"""Check saved RTL evidence. This does not run a new hardware simulation or API call."""
from pathlib import Path
import collections, hashlib, json, zipfile

ROOT = Path(__file__).resolve().parent

def main():
    package = ROOT / 'docs/assets/rtl-repair-study.zip'
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        def read(name):
            return json.loads(archive.read('rtl/' + name).decode('utf-8'))
        def sha(name):
            return hashlib.sha256(archive.read('rtl/' + name)).hexdigest()
        protocol = read('protocol.json')
        summary = read('summary.json')
        assert summary['complete'] and read('delivery_audit.json')['passed']
        for name, digest in protocol['sha256'].items():
            assert sha(name) == digest, name
        assert sha('selection.json') == read('selection_manifest.json')['sha256']
        selected = read('selection.json')
        assert not selected['independent_feedback_used']
        results = read('final_results.json')
        assert len(results) == len({(r['case'], r['method']) for r in results}) == 216
        assert [(r['case'], r['method'], r['source_sha256']) for r in results] == [(r['case'], r['method'], r['source_sha256']) for r in selected['rows']]
        for row in results:
            assert row['calls'] <= 3 and sha(row['source']) == row['source_sha256']
            for stage in ('development', 'independent'):
                score = read('scores/' + row['task'] + '_' + row['source_sha256'][:16] + '_' + stage + '/score.json')
                assert score['source_sha256'] == row['source_sha256']
                assert score['pass_test'] == row[stage + '_pass']
                assert not score['seed_results'] or [s['seed'] for s in score['seed_results']] == protocol[stage + '_seeds']
        calls = []
        for name in archive.namelist():
            if name.startswith('rtl/cases/') and name.endswith('/api_attempts.jsonl'):
                rows = [json.loads(line) for line in archive.read(name).decode('utf-8').splitlines()]
                assert len(rows) == len({r['tag'] for r in rows})
                calls.extend(rows)
        assert all(r['attempt'] == 1 for r in calls)
        assert len(calls) == summary['actual_calls'] == 72 + sum(r['calls'] - 1 for r in results if r['method'] != 'direct_patch')
        assert dict(collections.Counter(r['status'] for r in calls)) == summary['api_statuses']
        for method, totals in summary['methods'].items():
            rows = [r for r in results if r['method'] == method]
            assert len(rows) == totals['n'] == 72
            assert sum(r['independent_pass'] for r in rows) == totals['independent_pass']
            assert sum(r['development_pass'] and r['independent_pass'] for r in rows) == totals['correct_adoption']
            assert sum(r['development_pass'] and not r['independent_pass'] for r in rows) == totals['false_adoption']
            assert sum(r['calls'] for r in rows) == totals['logical_calls']
        qualifications = read('qualification_summary.json')
        assert len(qualifications) == 21
        assert all(r['pass_test'] if r['reference'] else r['functional_rejection'] for r in qualifications)
    print(json.dumps(dict(saved_evidence_replay_passed=True, cases=72, route_rows=216, actual_calls=len(calls), fresh_RTL_simulation=False, model_calls=False)))

if __name__ == '__main__':
    main()
