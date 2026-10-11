"""Fixed calibration-only routing and cluster bootstrap; never a deployment certificate."""
from pathlib import Path
import collections,csv,hashlib,json,random,statistics
BASE=Path(__file__).resolve().parent
MODELS=['gpt-5.4','qwen3.8-max','deepseek-v4-pro','kimi-k2.5'];REVIEWERS=MODELS[:3]

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def metrics(rows):
    n=len(rows);bad=sum(not r['correct'] for r in rows);accepted=sum(r['accepted'] for r in rows);fa=sum(r['accepted'] and not r['correct'] for r in rows);good=n-bad
    return dict(n=n,bad=bad,accepted=accepted,false_accepted=fa,correct_accepted=accepted-fa,
        accuracy=(n-bad)/n if n else None,false_endorsement=fa/bad if bad else None,
        coverage=accepted/n if n else None,conditional_risk=fa/accepted if accepted else None,
        correct_acceptance=(accepted-fa)/good if good else None)

def choose(rows):
    scores={m:metrics([r for r in rows if r['reviewer']==m]) for m in REVIEWERS}
    key=lambda m:((scores[m]['false_endorsement'] if scores[m]['false_endorsement'] is not None else 1),-(scores[m]['correct_acceptance'] or 0),REVIEWERS.index(m))
    return min(REVIEWERS,key=key),scores

def cluster_interval(rows,repetitions=2000):
    groups={}
    for r in rows:groups.setdefault(r['family'],{}).setdefault(r['cluster'],[]).append(r)
    rng=random.Random(90210);values={k:[] for k in ('coverage','conditional_risk','false_endorsement')}
    for _ in range(repetitions):
        sample=[]
        for clusters in groups.values():
            keys=list(clusters)
            for key in rng.choices(keys,k=len(keys)):sample.extend(clusters[key])
        result=metrics(sample)
        for k in values:
            if result[k] is not None:values[k].append(result[k])
    return {k:[sorted(v)[int(.025*(len(v)-1))],sorted(v)[int(.975*(len(v)-1))]] if v else None for k,v in values.items()}

def difference(a,b,repetitions=2000):
    by={}
    for r in a:by.setdefault(r['family'],{}).setdefault(r['cluster'],[[],[]])[0].append(r)
    for r in b:by[r['family']][r['cluster']][1].append(r)
    rng=random.Random(80331);vals={k:[] for k in ('coverage','conditional_risk','false_endorsement')}
    for _ in range(repetitions):
        aa=[];bb=[]
        for clusters in by.values():
            keys=list(clusters)
            for key in rng.choices(keys,k=len(keys)):
                aa.extend(clusters[key][0]);bb.extend(clusters[key][1])
        x,y=metrics(aa),metrics(bb)
        for k in vals:
            if x[k] is not None and y[k] is not None:vals[k].append(x[k]-y[k])
    return {k:[sorted(v)[int(.025*(len(v)-1))],sorted(v)[int(.975*(len(v)-1))]] if v else None for k,v in vals.items()}

def main():
    root=BASE/'protocol_formal';assert read(root/'completion.json')['complete']
    candidates=read(root/'production.json');reviews=read(root/'reviews.json');blind=read(root/'blind.json');cases=read(root/'cases.json')
    cal=[r for r in reviews if r['split']=='calibration'];test=[r for r in reviews if r['split']=='test']
    global_model,global_scores=choose(cal)
    per_model={m:choose([r for r in cal if r['producer']==m])[0] for m in MODELS}
    # Rules below are fixed in this script before any formal result has been read.
    routes={}
    for m in REVIEWERS:routes['fixed_'+m]=[r for r in test if r['reviewer']==m]
    routes['global_calibration']=[r for r in test if r['reviewer']==global_model]
    routes['producer_calibration']=[r for r in test if r['reviewer']==per_model[r['producer']]]
    def random_reviewer(r):return REVIEWERS[int(hashlib.sha256((r['case']+'|'+r['producer']).encode()).hexdigest()[:8],16)%len(REVIEWERS)]
    routes['random_hash']=[r for r in test if r['reviewer']==random_reviewer(r)]
    blind_lookup={(r['case'],r['reviewer']):r for r in blind}
    candidate_lookup={(r['case'],r['producer']):r for r in candidates}
    routes['blind_global_agreement']=[dict(r,accepted=blind_lookup[(r['case'],global_model)]['answer'] is not None and candidate_lookup[(r['case'],r['producer'])]['answer']==blind_lookup[(r['case'],global_model)]['answer']) for r in routes['global_calibration']]
    routes['all_three_agree']=[dict(r,accepted=all(x['accepted'] for x in test if x['case']==r['case'] and x['producer']==r['producer'])) for r in routes['global_calibration']]
    routes['shuffled_producer_route']=[r for r in test if r['reviewer']==per_model[MODELS[(MODELS.index(r['producer'])+1)%len(MODELS)]]]
    route_summary={name:dict(metrics(rows),interval95_cluster_bootstrap=cluster_interval(rows),reviews_per_candidate=3 if name=='all_three_agree' else 1) for name,rows in routes.items()}
    matrix=[]
    for producer in MODELS:
        for reviewer in REVIEWERS:
            rows=[r for r in test if r['producer']==producer and r['reviewer']==reviewer]
            matrix.append(dict(producer=producer,reviewer=reviewer,**metrics(rows),interval95_cluster_bootstrap=cluster_interval(rows)))
    output=dict(version='formal_protocol_analysis_v1',completion=read(root/'completion.json'),
        independent_calibration_specs=30,independent_test_specs=90,
        calibration_selection=dict(global_reviewer=global_model,producer_reviewers=per_model,global_scores=global_scores),
        producers={m:dict(n=sum(r['producer']==m and r['split']=='test' for r in candidates),correct=sum(r['producer']==m and r['split']=='test' and r['correct'] for r in candidates)) for m in MODELS},
        matrix=matrix,routes=route_summary,
        paired_difference_producer_minus_global=difference(routes['producer_calibration'],routes['global_calibration']),
        paired_difference_visible_minus_blind=difference(routes['global_calibration'],routes['blind_global_agreement']),
        families={f:{name:metrics([r for r in rows if r['family']==f]) for name,rows in routes.items()} for f in ('transaction','lease','request')},
        limitations=['Three synthetic protocol families; exact index/rule analysis is distinct from RTL correctness.',
          'Benchmark traces balanced valid/invalid; production distribution prevalence is unknown.',
          'Clusters are specification seeds; model samples and valid/invalid pairs are correlated.',
          'Bootstrap intervals are descriptive; zero observed errors do not certify zero deployment risk.',
          'API-reported model names are not independently authenticated vendor identities.',
          'All-cross dataset collection costs more than hypothetical single-review deployment; report both.'])
    attempts=[json.loads(x) for x in (root/'api_attempts_metadata.jsonl').read_text(encoding='utf-8').splitlines()]
    output['calls']=dict(actual=len(attempts),statuses=dict(collections.Counter(r['status'] for r in attempts)),reported_models=dict(collections.Counter(r.get('reported_model','unknown') for r in attempts)),usage=dict(sum_tokens(attempts)))
    save(root/'analysis.json',output)
    for name,rows in [('candidate_results',candidates),('review_results',reviews)]:
        with (root/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
            fields=[k for k in rows[0] if k!='answer'];writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(producers=output['producers'],routes=route_summary,route_difference=output['paired_difference_producer_minus_global']),ensure_ascii=False),flush=True)

def sum_tokens(attempts):
    total=collections.Counter()
    for r in attempts:
        for k in ('prompt_tokens','completion_tokens','total_tokens'):
            v=(r.get('usage') or {}).get(k)
            if isinstance(v,int):total[k]+=v
    return total

if __name__=='__main__':main()
