"""Offline CPU recheck. No API key, networking or RTL tool installation required."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent/'research'
sys.path.insert(0,str(ROOT))
from protocol_tasks import oracle,reference

def main():
    data=ROOT/'protocol_formal'
    cases=json.loads((data/'cases.json').read_text(encoding='utf-8'));lookup={c['id']:c for c in cases}
    for c in cases:assert oracle(c['spec'],c['events'])==reference(c['spec'],c['events'])==c['truth']
    candidates=json.loads((data/'production.json').read_text(encoding='utf-8'))
    for r in candidates:assert r['correct']==(r['answer']==lookup[r['case']]['truth'])
    import analyze_protocol
    before=json.loads((data/'analysis.json').read_text(encoding='utf-8'))
    analyze_protocol.main()
    after=json.loads((data/'analysis.json').read_text(encoding='utf-8'));assert before==after
    print(json.dumps(dict(passed=True,truth_rechecked=len(cases),candidate_labels_rechecked=len(candidates),analysis_replay_identical=True,scope='saved-data and CPU truth replay; no new API requests or RTL simulation')))

if __name__=='__main__':main()
