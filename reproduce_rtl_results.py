"""Check saved RTL evidence. This does not run a new hardware simulation or API call."""
from pathlib import Path
import collections, hashlib, json, re, zipfile

ROOT = Path(__file__).resolve().parent

def main():
    package = ROOT / 'docs/assets/rtl-repair-study.zip'
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        def read(name, prefix='rtl/'):
            return json.loads(archive.read(prefix + name).decode('utf-8'))
        def sha(name, prefix='rtl/'):
            return hashlib.sha256(archive.read(prefix + name)).hexdigest()
        def source_valid(row, prefix='rtl/'):
            text = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/', '', archive.read(prefix + row['source']).decode('utf-8'))
            core = {'dma_write': 'axi_dma_wr', 'udp_rx_guard': 'udp_ip_rx', 'icache_ctrl': 'ibex_icache'}[row['task']]
            return re.findall(r'\bmodule\s+(\w+)', text) == [row['task']] and bool(re.search(r'\b' + core + r'\s*(?:#\s*\(|[A-Za-z_]\w*\s*\()', text))
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

        # Reassessment preserves the original source selection and acceptance decisions.
        gate = read('source_contract_audit.json')['rows']
        assert [(r['case'], r['method']) for r in gate] == [(r['case'], r['method']) for r in results]
        assert all(r['source_contract_valid'] == source_valid(r) for r in gate)
        plan = read('precision_revision/plan.json')
        assert sha('cpu_grade.py') == plan['original_grader_sha256']
        assert sha('cpu_grade_timescale_revision.py') == plan['revised_grader_sha256']
        original = archive.read('rtl/cpu_grade.py').decode('utf-8')
        start = original.index("        if not trusted and build==directory/'build':")
        end = original.index('        os.environ.update', start)
        expected = (original[:start] + original[end:]).replace('waves=False)', "waves=False,timescale='1ns/1ps')")
        assert archive.read('rtl/cpu_grade_timescale_revision.py').decode('utf-8') == expected
        assert sha('regrade_timescale.py', 'scripts/') == plan['driver_sha256']
        assert read('precision_revision/selection_binding.json')['selection_sha256'] == sha('selection.json')
        revised = read('precision_revision/results.json')
        assert [{k: r[k] for k in selected['rows'][0]} for r in revised] == selected['rows']
        for row in revised:
            assert row['source_contract_valid'] == source_valid(row)
            for stage in ('development', 'independent'):
                directory = 'precision_revision/scores/' + row['task'] + '_' + row['source_sha256'][:16] + '_' + stage + '/'
                score = read(directory + 'score.json')
                assert score['source_sha256'] == row['source_sha256'] and score['grader_sha256'] == plan['revised_grader_sha256']
                assert score['pass_test'] == row['regraded_' + stage + '_pass']
                assert not score['seed_results'] or [s['seed'] for s in score['seed_results']] == protocol[stage + '_seeds']
                log = archive.read('rtl/' + directory + 'simulation.log').decode('utf-8')
                assert not any(x in log for x in ('OSError: [Errno 22] Invalid argument', 'file truncated', 'No space left on device', 'Bus error'))
                assert not any('simulator precision' in s.get('error', '') for s in score['seed_results'])
        corrected = read('precision_revision/summary.json')
        assert corrected['complete'] and corrected['model_calls'] == 0 and read('precision_revision/audit.json')['passed']
        for method, totals in corrected['methods'].items():
            group = [r for r in revised if r['method'] == method]
            assert totals['n'] == len(group) == 72
            assert totals['regraded_independent_pass'] == sum(r['regraded_independent_pass'] for r in group)
            assert totals['frozen_correct_adoption'] == sum(r['development_pass'] and r['regraded_independent_pass'] and r['source_contract_valid'] for r in group)
            assert totals['frozen_false_adoption'] == sum(r['development_pass'] and not (r['regraded_independent_pass'] and r['source_contract_valid']) for r in group)
        assert len(read('precision_revision/qualification.json')) == 21
        assert all(r['qualified'] for r in read('precision_revision/qualification.json'))

        # The new source-gated smoke is a separate pipeline check, not a method gain.
        smoke = read('protocol.json', 'smoke/')
        for name, digest in smoke['sha256'].items():
            assert sha(name, 'smoke/') == digest, name
        assert sha('selection.json', 'smoke/') == read('selection_manifest.json', 'smoke/')['sha256']
        smoke_selection = read('selection.json', 'smoke/')
        assert not smoke_selection['independent_feedback_used']
        smoke_rows = read('final_results.json', 'smoke/')
        assert len(smoke_rows) == len({r['case'] for r in smoke_rows}) == 12
        assert [{k: r[k] for k in smoke_selection['rows'][0]} for r in smoke_rows] == smoke_selection['rows']
        for row in smoke_rows:
            assert row['calls'] <= 3 and sha(row['source'], 'smoke/') == row['source_sha256']
            if row['development_pass']:
                assert source_valid(row, 'smoke/')
            for stage in ('development', 'independent'):
                score = read('scores/' + row['task'] + '_' + row['source_sha256'][:16] + '_' + stage + '/score.json', 'smoke/')
                assert score['source_sha256'] == row['source_sha256'] and score['stage'] == stage
                assert score['pass_test'] == row[stage + '_pass']
                assert not score['seed_results'] or [s['seed'] for s in score['seed_results']] == smoke[stage + '_seeds']
        smoke_calls = [json.loads(line) for name in archive.namelist() if name.startswith('smoke/cases/') and name.endswith('/api_attempts.jsonl') for line in archive.read(name).decode('utf-8').splitlines()]
        smoke_summary = read('summary.json', 'smoke/')
        assert smoke_summary['complete'] and read('delivery_audit.json', 'smoke/')['passed']
        assert all(r['attempt'] == 1 for r in smoke_calls)
        assert len(smoke_calls) == smoke_summary['actual_calls'] == sum(r['calls'] for r in smoke_rows) <= 36
        assert dict(collections.Counter(r['status'] for r in smoke_calls)) == smoke_summary['api_statuses']
        totals = smoke_summary['methods']['cross_family_trace']
        assert totals['correct_adoption'] == sum(r['development_pass'] and r['independent_pass'] for r in smoke_rows)
        assert totals['false_adoption'] == sum(r['development_pass'] and not r['independent_pass'] for r in smoke_rows)
        smoke_qualifications = read('qualification_summary.json', 'smoke/')
        assert len(smoke_qualifications) == 6 and all(r['pass_test'] if r['reference'] else r['functional_rejection'] for r in smoke_qualifications)
        controls = read('source_gate_controls.json', 'smoke/')
        assert len(controls) == 3 and all(r['status'] == 'missing_upstream_core' for r in controls)
    print(json.dumps(dict(saved_evidence_replay_passed=True, cases=72, route_rows=216, actual_calls=len(calls), corrected_execution_rows=len(revised), smoke_cases=len(smoke_rows), smoke_calls=len(smoke_calls), fresh_RTL_simulation=False, model_calls=False)))

if __name__ == '__main__':
    main()
