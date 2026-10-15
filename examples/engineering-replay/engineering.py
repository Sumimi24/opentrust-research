"""Finite engineering contracts with shared four-period operating decisions, CPU only."""
from pathlib import Path
from functools import lru_cache
import copy
import json
import os
import tempfile
import uuid
import warnings
os.environ['OMP_NUM_THREADS']='2'
os.environ['OPENBLAS_NUM_THREADS']='2'
import numpy as np
import pandapower as pp
import wntr

ROOT=Path(__file__).resolve().parent
WORK=Path(tempfile.gettempdir())/'opentrust_design_v04'
WORK.mkdir(exist_ok=True)


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def load_water(path):
    # The observed BWSN1 warning concerns preserved, unused curves; record it in source metadata.
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message='Not all curves were used in .*',category=UserWarning)
        return wntr.network.WaterNetworkModel(str(path))


@lru_cache(maxsize=4)
def grid(path):return pp.from_json(path)


def schema_errors(task,design):
    expected={'parallel_lines','transformer_parallel','tap_schedule'} if task['domain']=='power' else {'pipe_upgrades','pump_schedules','tank_control_shifts_m'}
    if not isinstance(design,dict) or set(design)!=expected:return ['Supply exactly these design fields: '+','.join(sorted(expected))]
    errors=[];field='parallel_lines' if task['domain']=='power' else 'pipe_upgrades';assets=design[field]
    if not isinstance(assets,list) or any(not isinstance(v,str) for v in assets):errors.append('Upgrade IDs must be an array of strings')
    elif len(set(assets))!=len(assets) or any(v not in task['eligible_assets'] for v in assets):errors.append('Unapproved or duplicate upgrade IDs')
    elif len(assets)>task['max_upgrades']:errors.append('Capital works limit exceeded')
    if task['domain']=='power':
        if type(design['transformer_parallel'])!=int or design['transformer_parallel'] not in task['transformer_choices']:errors.append('Transformer count outside catalogue')
        taps=design['tap_schedule']
        if not isinstance(taps,list) or len(taps)!=4 or any(type(v)!=int or v not in task['tap_choices'] for v in taps):errors.append('Supply four approved integer taps in period order')
        elif sum(abs(taps[(i+1)%4]-taps[i]) for i in range(4))>task['max_tap_movement']:errors.append('Daily cyclic tap movement limit exceeded')
    else:
        schedules=design['pump_schedules']
        if not isinstance(schedules,dict) or set(schedules)!=set(task['decision_pumps']):errors.append('Supply all declared pump schedules and no extra IDs')
        elif any(not isinstance(s,list) or len(s)!=4 or any(type(v) not in (int,float) or v not in task['speed_choices'] for v in s) for s in schedules.values()):errors.append('Each pump needs four approved relative speeds')
        shifts=design['tank_control_shifts_m']
        if not isinstance(shifts,dict) or set(shifts)!=set(task['control_shift_choices']):errors.append('Supply all declared tank shifts and no extra IDs')
        elif any(type(v) not in (int,float) or v not in task['control_shift_choices'][k] for k,v in shifts.items()):errors.append('Tank shift outside threshold-safe catalogue')
    return errors


def power_network(task,design,scenario):
    net=copy.deepcopy(grid(str(ROOT/'inputs'/task['input_file'])))
    net.load[['p_mw','q_mvar']]*=task['demand_growth']*scenario['load']
    net.sgen[['p_mw','q_mvar']]*=scenario['generation']
    rng=np.random.default_rng(scenario.get('spatial_seed',0));spread=scenario.get('spatial_spread',0.)
    net.load[['p_mw','q_mvar']]=net.load[['p_mw','q_mvar']].mul(rng.uniform(1-spread,1+spread,len(net.load)),axis=0)
    net.sgen[['p_mw','q_mvar']]=net.sgen[['p_mw','q_mvar']].mul(rng.uniform(1-spread,1+spread,len(net.sgen)),axis=0)
    for asset in design['parallel_lines']:net.line.loc[int(asset),'parallel']=task['line_circuits']
    net.trafo.loc[:,'parallel']=design['transformer_parallel'];net.trafo.loc[:,'tap_pos']=design['tap']
    if scenario.get('line_circuit_outage'):
        idx=int(scenario['line_circuit_outage'])
        if net.line.loc[idx,'parallel']<=1:net.line.loc[idx,'in_service']=False
        else:net.line.loc[idx,'parallel']-=1
    if scenario.get('transformer_outage'):
        idx=int(scenario['transformer_bank'])
        if net.trafo.loc[idx,'parallel']<=1:net.trafo.loc[idx,'in_service']=False
        else:net.trafo.loc[idx,'parallel']-=1
    return net


def power_point(task,design,scenario):
    net=power_network(task,design,scenario);pp.runpp(net,numba=False,tolerance_mva=1e-9,max_iteration=50)
    if not net.converged or net.res_bus.vm_pu.isna().any():raise ValueError('Nonconverged or unserved bus')
    r=net.res_bus.vm_pu;line=net.res_line.loading_percent;limits=task['limits']
    metrics=dict(voltage_min=float(r.min()),voltage_max=float(r.max()),line_loading_max=float(line.max()),
        transformer_loading_max=float(net.res_trafo.loading_percent.max()),loss_mw=float(net.res_line.pl_mw.sum()),
        worst_low_bus=str(r.idxmin()),worst_high_bus=str(r.idxmax()),worst_line=str(line.idxmax()))
    checks=dict(voltage_min=metrics['voltage_min']>=limits['voltage_min']-1e-6,voltage_max=metrics['voltage_max']<=limits['voltage_max']+1e-6,
        line_loading=metrics['line_loading_max']<=100+1e-4,transformer_loading=metrics['transformer_loading_max']<=100+1e-4)
    return metrics,checks


def power(task,design,scenario):
    periods=[]
    for i,(load,generation) in enumerate(task['profile']):
        s=dict(load=load*scenario.get('load_scale',1.),generation=generation*scenario.get('generation_scale',1.),
            spatial_spread=scenario.get('spatial_spread',0.),spatial_seed=scenario.get('spatial_seed',0)+i)
        if i in scenario.get('outage_periods',[0,1,2,3]):
            for key in ['line_circuit_outage','transformer_outage','transformer_bank']:
                if scenario.get(key):s[key]=scenario[key]
        d=dict(demand_growth=task['demand_growth'],parallel_lines=design['parallel_lines'],transformer_parallel=design['transformer_parallel'],tap=design['tap_schedule'][i])
        metrics,checks=power_point(task,d,s);periods.append(dict(period=i,metrics=metrics,checks=checks))
    combined={key:all(p['checks'][key] for p in periods) for key in periods[0]['checks']}
    metrics=dict(voltage_min=min(p['metrics']['voltage_min'] for p in periods),voltage_max=max(p['metrics']['voltage_max'] for p in periods),
        line_loading_max=max(p['metrics']['line_loading_max'] for p in periods),transformer_loading_max=max(p['metrics']['transformer_loading_max'] for p in periods),
        estimated_24h_line_loss_mwh=6*sum(p['metrics']['loss_mw'] for p in periods),periods=periods)
    return metrics,combined


def compile_speed(wn,pump,schedule):
    from wntr.network.controls import Rule,Control,ControlAction,ValueCondition,SimTimeCondition,AndCondition
    assert pump.speed_pattern_name is None,'Decision catalogue excludes source speed-pattern pumps'
    base_speed=pump.base_speed
    if schedule==[1.]*4:return
    openings=[]
    for name,control in list(wn.controls()):
        actions=list(control.actions())
        for action in actions:
            obj,attribute=action.target()
            if obj is pump and attribute=='status' and action._value==wntr.network.LinkStatus.Open:
                assert isinstance(control,Control) and len(actions)==1,'Decision pump requires simple source enable controls'
                openings.append((name,control))
    pump.base_speed=base_speed*schedule[0] if pump.initial_status!=wntr.network.LinkStatus.Closed else 0.
    if len(set(schedule))==1:
        for name,control in openings:
            wn.remove_control(name);wn.add_control(name,Control(control.condition,ControlAction(pump,'setting',base_speed*schedule[0]),priority=control._priority,name=name))
        return
    # Native OPEN commands reset an EPANET pump's speed to 1. Translate their
    # unchanged availability conditions into "open at the scheduled speed".
    for name,_ in openings:wn.remove_control(name)
    wn.options.time.rule_timestep=900
    for day in range(3):
        for period,value in enumerate(schedule):
            start=day*86400+period*21600
            if start>48*3600:continue
            active=AndCondition(SimTimeCondition(wn,'>=',start),SimTimeCondition(wn,'<',start+21600))
            targets=[(ValueCondition(pump,'status','=',wntr.network.LinkStatus.Open),1)]+[(c.condition,c._priority) for _,c in openings]
            for index,(availability,priority) in enumerate(targets):
                name=f'OTS_{pump.name}_{index}_{day}_{period}'
                condition=AndCondition(availability,active)
                wn.add_control(name,Rule(condition,ControlAction(pump,'setting',base_speed*value),priority=priority,name=name))


def configure_water(task,design,scenario):
    wn=load_water(ROOT/'inputs'/task['input_file'])
    wn.options.time.duration=48*3600;wn.options.time.hydraulic_timestep=900;wn.options.time.report_timestep=900
    wn.options.hydraulic.demand_model='PDD';wn.options.hydraulic.minimum_pressure=0;wn.options.hydraulic.required_pressure=task['limits']['pressure_min']
    rng=np.random.default_rng(scenario.get('spatial_seed',0));spread=scenario.get('spatial_spread',0.)
    for _,j in wn.junctions():
        factor=task['demand_growth']*scenario.get('demand',1.)*float(rng.uniform(1-spread,1+spread))
        for demand in j.demand_timeseries_list:demand.base_value*=factor
    for _,pipe in wn.pipes():pipe.roughness*=scenario.get('roughness_factor',1.)
    for name in design['pipe_upgrades']:wn.get_link(name).diameter*=1.5
    for _,control in wn.controls():
        condition=control.condition
        if isinstance(condition,wntr.network.controls.ValueCondition) and isinstance(condition._source_obj,wntr.network.Tank) and condition._source_attr=='level':
            condition._threshold+=design['tank_control_shifts_m'].get(condition._source_obj.name,0.)
    for name,schedule in design['pump_schedules'].items():
        compile_speed(wn,wn.get_link(name),schedule)
    if scenario.get('fire_flow'):
        wn.get_node(task['fire_node']).add_fire_fighting_demand(wn,scenario['fire_flow'],scenario['fire_start']*3600,scenario['fire_end']*3600)
    return wn


def water(task,design,scenario):
    wn=configure_water(task,design,scenario);expected=wntr.metrics.expected_demand(wn,start_time=0,end_time=48*3600,timestep=900)
    stem=WORK/(task['id']+'_'+uuid.uuid4().hex)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');results=wntr.sim.EpanetSimulator(wn).run_sim(file_prefix=str(stem),convergence_error=True)
        if results.error_code:raise ValueError('EPANET numerical error '+str(results.error_code))
        times=list(range(0,48*3600+1,900))
        if list(results.node['pressure'].index)!=times:raise ValueError('Incomplete 48h trajectory')
        demanded=[n for n,j in wn.junctions() if any(d.base_value>0 for d in j.demand_timeseries_list)]
        pressure=results.node['pressure'][demanded];target=expected[wn.junction_name_list]
        ratio=(results.node['demand'][wn.junction_name_list]/target.where(target>1e-8)).min().min()
        changes={n:float(results.node['pressure'][n].iloc[-1]-t.init_level) for n,t in wn.tanks()}
        lower=min(float((results.node['pressure'][n]-t.min_level).min()) for n,t in wn.tanks())
        upper=min(float((t.max_level-results.node['pressure'][n]).min()) for n,t in wn.tanks())
        if not np.isfinite(pressure.to_numpy()).all() or not np.isfinite(ratio):raise ValueError('Nonfinite hydraulic results')
        energies={}
        for name,pump in wn.pumps():
            head=(results.node['head'][pump.end_node_name]-results.node['head'][pump.start_node_name]).clip(lower=0)
            hydraulic_watts=9810*head*results.link['flowrate'][name].clip(lower=0)
            energies[name]=float(np.trapezoid(hydraulic_watts.to_numpy(),x=np.array(times))/3.6e6)
        metrics=dict(pressure_min=float(pressure.min().min()),pressure_max=float(pressure.max().max()),supply_fraction_min=float(ratio),
            tank_end_change_m=changes,tank_lower_margin_m=lower,tank_upper_margin_m=upper,hydraulic_energy_kwh=sum(energies.values()),
            worst_low_node=str(pressure.min().idxmin()),worst_high_node=str(pressure.max().idxmax()),warnings=[str(w.message)[:160] for w in caught])
        metrics['worst_low_hour']=float(pressure[metrics['worst_low_node']].idxmin()/3600)
        metrics['worst_high_hour']=float(pressure[metrics['worst_high_node']].idxmax()/3600)
        metrics['periods']=[dict(period=i,pressure_min=float(pressure.loc[((pressure.index%86400)//21600)==i].min().min()),
            pressure_max=float(pressure.loc[((pressure.index%86400)//21600)==i].max().max())) for i in range(4)]
        limits=task['limits'];checks=dict(pressure_min=metrics['pressure_min']>=limits['pressure_min']-.01,
            pressure_max=metrics['pressure_max']<=limits['pressure_max']+.01,supply=metrics['supply_fraction_min']>=.999,
            tank_reserve=lower>=-.01 and upper>=-.01,terminal_storage=min(changes.values())>=-limits['tank_drawdown_max']-.01)
        return metrics,checks
    finally:
        for suffix in ['.inp','.rpt','.bin']:
            p=Path(str(stem)+suffix)
            if p.exists():p.unlink()


def grade(task,design,scenarios):
    errors=schema_errors(task,design)
    if errors:return dict(passed=False,contract_errors=errors,tests=[])
    rows=[]
    for scenario in scenarios:
        try:
            metrics,checks=(power if task['domain']=='power' else water)(task,design,scenario)
            rows.append(dict(scenario=scenario['id'],metrics=metrics,checks=checks,passed=all(checks.values())))
        except Exception as exc:rows.append(dict(scenario=scenario['id'],passed=False,error=type(exc).__name__+': '+str(exc)[:220]))
    return dict(passed=all(r['passed'] for r in rows),contract_errors=[],tests=rows)
