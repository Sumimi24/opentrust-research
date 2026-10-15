"""Replay two frozen engineering cases on CPU, without a model/API connection."""
import argparse
import hashlib
import json
import math
import platform
import time
from pathlib import Path

import engineering

ROOT = Path(__file__).resolve().parent
ABS_TOL = 1e-6
REL_TOL = 1e-8


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def compare(actual, expected, path='score'):
    """Numerical replay tolerance does not modify the physical pass thresholds."""
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        return [] if actual == expected else [path]
    if isinstance(expected, (int, float)):
        return [] if math.isclose(actual, expected, rel_tol=REL_TOL, abs_tol=ABS_TOL) else [path]
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [path]
        return [p for i, (a, e) in enumerate(zip(actual, expected))
                for p in compare(a, e, f'{path}[{i}]')]
    if not isinstance(actual, dict) or actual.keys() != expected.keys():
        return [path]
    return [p for k in expected for p in compare(actual[k], expected[k], f'{path}.{k}')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['kerber_overhead', 'Net1'])
    parser.add_argument('--design', type=Path, help='Custom design JSON; requires --case. Does not compare against frozen output.')
    parser.add_argument('--output', type=Path, default=ROOT / 'results.json')
    args = parser.parse_args()
    if args.design and not args.case:
        parser.error('--design requires --case')
    for item in read(ROOT / 'source_manifest.json')['files']:
        path = ROOT / item['bundle_path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Frozen asset hash mismatch: {item["bundle_path"]}')
    cases = [c for c in read(ROOT / 'cases.json') if not args.case or c['task'] == args.case]
    results = []
    started = time.perf_counter()
    for case in cases:
        task = read(ROOT / 'tasks' / (case['task'] + '.json'))
        scenarios = task['dev'] + task['held']
        assert len(task['dev']) == len(task['held']) == 8
        assert len({s['id'] for s in scenarios}) == 16
        designs = {'custom': read(args.design)} if args.design else {s: case[s] for s in ['initial', 'final']}
        for stage, design in designs.items():
            before = time.perf_counter()
            score = engineering.grade(task, design, scenarios)
            mismatches = None if args.design else compare(score, case['expected'][stage])
            results.append({'case':case['task'], 'stage':stage, 'design':design, 'score':score,
                            'expected_match': None if mismatches is None else not mismatches,
                            'mismatched_paths':mismatches, 'seconds':time.perf_counter()-before})
            print(f'{case["task"]} {stage}: pass={score["passed"]}; '
                  f'scenarios={len(score["tests"])}; '
                  f'expected_match={results[-1]["expected_match"]}', flush=True)
    report = {'mode':'custom_design' if args.design else 'frozen_replay',
              'model_calls':0, 'simulation_scenarios':sum(len(r['score']['tests']) for r in results),
              'all_expected_match':None if args.design else all(r['expected_match'] for r in results),
              'metric_comparison_tolerance':{'absolute':ABS_TOL,'relative':REL_TOL},
              'seconds':time.perf_counter()-started, 'platform':platform.platform(),
              'python':platform.python_version(), 'results':results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if report['all_expected_match'] is False:
        raise SystemExit('Frozen replay mismatch; inspect results.json. The expected data were not changed.')
    print(f'Report: {args.output}',flush=True)


if __name__ == '__main__':
    main()
