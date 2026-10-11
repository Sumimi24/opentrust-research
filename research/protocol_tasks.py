"""Synthetic engineering protocols. Truth comes from two independent CPU interpreters."""
import itertools,json,random

RULES={
'transaction': '''Events have monotone integer time t. BEGIN creates a never-reused transaction id; at most capacity transactions may be active. WRITE(id,p) requires an active transaction, a listed participant p, and that p has not prepared. PREPARE(id,p) requires active id, listed p, and no prior prepare by p. COMMIT requires active id and every listed participant prepared; ABORT requires active id. COMMIT/ABORT close id. At end every transaction must be closed. Check TIME first, then operation rules. Rule labels: TIME, BEGIN, WRITE, PREPARE, COMMIT, ABORT, END.''',
'lease': '''Events have monotone integer time t. Leases expire automatically at t >= expiry, where expiry=acquisition/renewal time + ttl; expiry itself is excluded. ACQUIRE(id,n,ttl) requires id not currently active, 1<=n<=capacity, 1<=ttl<=max_ttl, and total units of all unexpired leases plus n <=capacity. USE(id), RELEASE(id), RENEW(id,ttl) require active id. RENEW additionally requires ttl in 1..max_ttl and sets expiry=t+ttl, preserving units. RELEASE closes id. Expired/released ids may be acquired again. TICK only advances time. At end no unexpired lease may remain. Check TIME first, then operation rules. Rule labels: TIME, ACQUIRE, USE, RELEASE, RENEW, END.''',
'request': '''Events have monotone integer time t. SUBMIT(id,n) creates a never-reused request with 1<=n<=max_bytes, with at most capacity active requests. ACCEPT(id) requires submitted, not already accepted id; set deadline=t+timeout. DATA(id,seq,n) requires accepted id, seq starting at 0 and increasing by exactly 1 per DATA, 1<=n<=chunk_bytes, and cumulative bytes <=submitted n. COMPLETE requires accepted id and cumulative bytes exactly submitted n, then closes id. CANCEL closes any active id. TICK only advances time. Before each event, any active accepted request with current t >deadline violates DEADLINE, even if that event would cancel it. Equality at deadline is allowed. At end every request must be closed. Check TIME, then DEADLINE, then operation rule. Rule labels: TIME, DEADLINE, SUBMIT, ACCEPT, DATA, COMPLETE, CANCEL, END.'''}

def verdict(index=None,rule=None):
    return dict(valid=index is None,first_bad_event=index,rule=rule)

def oracle(spec,events):
    """Online state transition implementation; 1-based events, END is N+1."""
    family=spec['family'];state={};seen=set();last=None
    for i,e in enumerate(events,1):
        t=e['t'];op=e['op'];ident=e.get('id');p=e.get('p')
        if last is not None and t<last:return verdict(i,'TIME')
        last=t
        if family=='lease':state={k:v for k,v in state.items() if v['expiry']>t}
        if family=='request' and any('deadline' in v and t>v['deadline'] for v in state.values()):return verdict(i,'DEADLINE')
        if family=='transaction':
            if op=='BEGIN':
                if ident in seen or len(state)>=spec['capacity']:return verdict(i,op)
                state[ident]=set();seen.add(ident)
            elif op in ('WRITE','PREPARE'):
                if ident not in state or p not in spec['participants'] or p in state[ident]:return verdict(i,op)
                if op=='PREPARE':state[ident].add(p)
            elif op in ('COMMIT','ABORT'):
                if ident not in state or (op=='COMMIT' and state[ident]!=set(spec['participants'])):return verdict(i,op)
                del state[ident]
            else:raise ValueError(op)
        elif family=='lease':
            if op=='ACQUIRE':
                if ident in state or not 1<=e['n']<=spec['capacity'] or not 1<=e['ttl']<=spec['max_ttl'] or sum(v['n'] for v in state.values())+e['n']>spec['capacity']:return verdict(i,op)
                state[ident]=dict(n=e['n'],expiry=t+e['ttl'])
            elif op in ('USE','RELEASE','RENEW'):
                if ident not in state or (op=='RENEW' and not 1<=e['ttl']<=spec['max_ttl']):return verdict(i,op)
                if op=='RELEASE':del state[ident]
                if op=='RENEW':state[ident]['expiry']=t+e['ttl']
            elif op!='TICK':raise ValueError(op)
        else:
            if op=='SUBMIT':
                if ident in seen or len(state)>=spec['capacity'] or not 1<=e['n']<=spec['max_bytes']:return verdict(i,op)
                state[ident]=dict(n=e['n'],sent=0,seq=0);seen.add(ident)
            elif op=='ACCEPT':
                if ident not in state or 'deadline' in state[ident]:return verdict(i,op)
                state[ident]['deadline']=t+spec['timeout']
            elif op=='DATA':
                if ident not in state or 'deadline' not in state[ident] or e['seq']!=state[ident]['seq'] or not 1<=e['n']<=spec['chunk_bytes'] or state[ident]['sent']+e['n']>state[ident]['n']:return verdict(i,op)
                state[ident]['sent']+=e['n'];state[ident]['seq']+=1
            elif op in ('COMPLETE','CANCEL'):
                if ident not in state or (op=='COMPLETE' and ('deadline' not in state[ident] or state[ident]['sent']!=state[ident]['n'])):return verdict(i,op)
                del state[ident]
            elif op!='TICK':raise ValueError(op)
    return verdict(len(events)+1,'END') if state else verdict()

def reference(spec,events):
    """Reconstruct each id from its complete prior history, rather than update online state."""
    family=spec['family']
    def active_history(prefix,t):
        ids={e.get('id') for e in prefix if 'id' in e};active={}
        for ident in ids:
            h=[x for x in prefix if x.get('id')==ident]
            if family=='lease':
                starts=[j for j,x in enumerate(h) if x['op']=='ACQUIRE']
                if not starts:continue
                h=h[starts[-1]:]
                if any(x['op']=='RELEASE' for x in h):continue
                expiry_event=[x for x in h if x['op'] in ('ACQUIRE','RENEW')][-1]
                if expiry_event['t']+expiry_event['ttl']>t:active[ident]=h
            else:
                if h and h[-1]['op'] not in ('COMMIT','ABORT','COMPLETE','CANCEL'):active[ident]=h
        return active
    for j,e in enumerate(events):
        t=e['t'];op=e['op'];ident=e.get('id');prefix=events[:j]
        if j and t<events[j-1]['t']:return verdict(j+1,'TIME')
        active=active_history(prefix,t);h=active.get(ident,[])
        if family=='request':
            if any(t>[x['t'] for x in history if x['op']=='ACCEPT'][0]+spec['timeout'] for history in active.values() if any(x['op']=='ACCEPT' for x in history)):return verdict(j+1,'DEADLINE')
        good=True
        if family=='transaction':
            prepared={x['p'] for x in h if x['op']=='PREPARE'}
            if op=='BEGIN':good=not any(x.get('id')==ident for x in prefix) and len(active)<spec['capacity']
            elif op in ('WRITE','PREPARE'):good=bool(h) and e['p'] in spec['participants'] and e['p'] not in prepared
            elif op=='COMMIT':good=bool(h) and prepared==set(spec['participants'])
            elif op=='ABORT':good=bool(h)
            else:raise ValueError(op)
        elif family=='lease':
            if op=='ACQUIRE':good=not h and 1<=e['n']<=spec['capacity'] and 1<=e['ttl']<=spec['max_ttl'] and sum(v[0]['n'] for v in active.values())+e['n']<=spec['capacity']
            elif op in ('USE','RELEASE'):good=bool(h)
            elif op=='RENEW':good=bool(h) and 1<=e['ttl']<=spec['max_ttl']
            elif op!='TICK':raise ValueError(op)
        else:
            accepted=any(x['op']=='ACCEPT' for x in h);data=[x for x in h if x['op']=='DATA']
            if op=='SUBMIT':good=not any(x.get('id')==ident for x in prefix) and len(active)<spec['capacity'] and 1<=e['n']<=spec['max_bytes']
            elif op=='ACCEPT':good=bool(h) and not accepted
            elif op=='DATA':good=bool(h) and accepted and e['seq']==len(data) and 1<=e['n']<=spec['chunk_bytes'] and sum(x['n'] for x in data)+e['n']<=h[0]['n']
            elif op=='COMPLETE':good=bool(h) and accepted and sum(x['n'] for x in data)==h[0]['n']
            elif op=='CANCEL':good=bool(h)
            elif op!='TICK':raise ValueError(op)
        if not good:return verdict(j+1,op)
    if active_history(events,events[-1]['t'] if events else 0):return verdict(len(events)+1,'END')
    return verdict()

def generate(family,seed):
    rng=random.Random(seed);events=[];t=0
    spec=dict(family=family,capacity=rng.randint(2,4))
    groups=2+(seed%3)*2
    def add(op,**kw):events.append(dict(t=t,op=op,**kw))
    if family=='transaction':
        spec['participants']=['p'+str(i) for i in range(rng.randint(2,4))]
        for group in range(groups):
            ids=['x'+str(group)+'_'+str(k) for k in range(spec['capacity'])]
            for ident in ids:add('BEGIN',id=ident)
            actions={ident:[dict(op=op,id=ident,p=p) for p in rng.sample(spec['participants'],len(spec['participants'])) for op in ('WRITE','PREPARE')]+[dict(op='ABORT' if rng.random()<.2 else 'COMMIT',id=ident)] for ident in ids}
            while actions:
                ident=rng.choice(list(actions));action=actions[ident].pop(0);t+=rng.randint(0,1);add(**action)
                if not actions[ident]:del actions[ident]
    elif family=='lease':
        spec['max_ttl']=rng.randint(4,10)
        for group in range(groups):
            ids=['l'+str(k) for k in range(spec['capacity'])]
            for ident in ids:add('ACQUIRE',id=ident,n=1,ttl=spec['max_ttl'])
            for _ in range(spec['max_ttl']//2):
                t+=1
                for ident in rng.sample(ids,len(ids)):add('USE',id=ident)
                if rng.random()<.4:
                    ident=rng.choice(ids);add('RENEW',id=ident,ttl=spec['max_ttl'])
            for ident in rng.sample(ids,len(ids)):add('RELEASE',id=ident)
            t+=rng.randint(1,3);add('TICK')
        # Explicit valid exclusive-expiry boundary, then reuse the id.
        add('ACQUIRE',id='edge',n=spec['capacity'],ttl=1);t+=1;add('TICK')
        add('ACQUIRE',id='edge',n=1,ttl=1);add('RELEASE',id='edge')
    else:
        spec.update(chunk_bytes=rng.choice([2,4,8]),max_bytes=rng.choice([9,17,25]),timeout=100)
        for group in range(groups):
            ids=['r'+str(group)+'_'+str(k) for k in range(spec['capacity'])];actions={}
            for ident in ids:
                n=rng.randint(1,spec['max_bytes']);add('SUBMIT',id=ident,n=n)
                a=[dict(op='ACCEPT',id=ident)];seq=0
                while n:
                    size=min(n,rng.randint(1,spec['chunk_bytes']));a.append(dict(op='DATA',id=ident,seq=seq,n=size));n-=size;seq+=1
                a.append(dict(op='COMPLETE',id=ident));actions[ident]=a
            while actions:
                ident=rng.choice(list(actions));add(**actions[ident].pop(0))
                if not actions[ident]:del actions[ident]
            t+=1
    assert oracle(spec,events)==reference(spec,events)==verdict()
    return spec,events

def corrupt(spec,events,seed):
    rng=random.Random(seed);bad=json.loads(json.dumps(events));family=spec['family'];kind=seed%4
    if kind==0:
        j=rng.randrange(1,len(bad));bad[j]['t']=bad[j-1]['t']-1;mutation='time_reversal'
    elif kind==1:
        choices=[j for j,e in enumerate(bad) if e['op'] in {'transaction':'PREPARE','lease':'USE','request':'DATA'}.values()]
        j=rng.choice(choices);bad[j]['id']='missing';mutation='unknown_id'
    elif kind==2:
        op={'transaction':'COMMIT','lease':'RELEASE','request':'COMPLETE'}[family]
        choices=[j for j,e in enumerate(bad) if e['op']==op]
        if not choices:choices=[j for j,e in enumerate(bad) if e['op']=='ABORT']
        j=rng.choice(choices);bad.insert(j+1,dict(bad[j]));mutation='duplicate_terminal'
    else:
        if family=='transaction':
            j=rng.choice([j for j,e in enumerate(bad) if e['op']=='PREPARE']);bad[j]['p']='absent'
        elif family=='lease':
            j=rng.choice([j for j,e in enumerate(bad) if e['op']=='ACQUIRE']);bad[j]['n']=spec['capacity']+1
        else:
            j=rng.choice([j for j,e in enumerate(bad) if e['op']=='DATA']);bad[j]['seq']+=1
        mutation='field_constraint'
    a=oracle(spec,bad);assert not a['valid'] and a==reference(spec,bad)
    return bad,mutation

def audit():
    counts={};lengths={}
    for family in RULES:
        counts[family]=0;lengths[family]=[]
        for seed in range(90,150):
            spec,events=generate(family,seed);lengths[family].append(len(events))
            for k in range(8):
                bad,_=corrupt(spec,events,seed*8+k);assert oracle(spec,bad)==reference(spec,bad);counts[family]+=1
        # Exhaustive short traces over a concrete small event alphabet.
        spec,unused=generate(family,91);spec['capacity']=2
        alphabet={'transaction':[dict(t=0,op='BEGIN',id='a'),dict(t=0,op='WRITE',id='a',p='p0'),dict(t=0,op='PREPARE',id='a',p='p0'),dict(t=0,op='COMMIT',id='a'),dict(t=0,op='ABORT',id='a')],
                  'lease':[dict(t=0,op='ACQUIRE',id='a',n=1,ttl=1),dict(t=1,op='USE',id='a'),dict(t=0,op='RELEASE',id='a'),dict(t=1,op='RENEW',id='a',ttl=2),dict(t=1,op='TICK')],
                  'request':[dict(t=0,op='SUBMIT',id='a',n=1),dict(t=0,op='ACCEPT',id='a'),dict(t=0,op='DATA',id='a',seq=0,n=1),dict(t=0,op='COMPLETE',id='a'),dict(t=101,op='TICK')]}[family]
        for n in range(5):
            for sequence in itertools.product(alphabet,repeat=n):
                assert oracle(spec,list(sequence))==reference(spec,list(sequence));counts[family]+=1
    return dict(passed=True,dual_oracle_comparisons=counts,trace_lengths={f:dict(min=min(v),max=max(v)) for f,v in lengths.items()},scope='finite short-trace alphabet enumeration plus 60 generated specifications per family; not formal proof')

def make_cases(stage):
    pilot=stage.startswith('pilot')
    rows=[];count=2 if pilot else 40;offset=(11000 if stage=='pilot_v2' else 10000) if pilot else 20000
    for family in RULES:
        for k in range(count):
            seed=offset+k;spec,events=generate(family,seed)
            for damaged in (False,True):
                trace,mutation=corrupt(spec,events,seed) if damaged else (events,'none')
                rows.append(dict(id=f'{family}_{seed}_{int(damaged)}',cluster=f'{family}_{seed}',family=family,split='pilot' if pilot else ('calibration' if k<10 else 'test'),spec=spec,events=trace,truth=oracle(spec,trace),mutation=mutation))
    return rows

def public_problem(case):
    numbered='\n'.join(str(i)+': '+json.dumps(e,separators=(',',':')) for i,e in enumerate(case['events'],1))
    return 'Protocol definition:\n'+RULES[case['family']]+'\nParameters:\n'+json.dumps(case['spec'])+'\nEvents (explicit 1-based labels; END violation uses N+1):\n'+numbered

if __name__=='__main__':print(json.dumps(audit(),indent=2))
