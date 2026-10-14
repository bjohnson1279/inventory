"""Fail-closed conformance runner: smoke proves wiring, full exposes coverage gaps."""
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from collections import Counter
import httpx
try:
    from scripts.conformance_runtime import BACKENDS, backend_urls, check_health, HarnessError
except ModuleNotFoundError:
    from conformance_runtime import BACKENDS, backend_urls, check_health, HarnessError

ROOT = Path(__file__).resolve().parents[1]

def wait_for_backends(max_retries=30, initial_delay=2):
    urls = backend_urls()
    last = {}
    with httpx.Client(timeout=2, follow_redirects=False) as client:
        for attempt in range(max_retries):
            for backend in BACKENDS:
                try:
                    check_health(client, backend, urls[backend])
                    last.pop(backend, None)
                except HarnessError as exc:
                    last[backend] = str(exc)
            if not last:
                return
            if attempt+1 < max_retries:
                time.sleep(initial_delay)
    raise HarnessError('Required backend health checks failed: '+ '; '.join(last.values()))

def required_scenarios(suite):
    paths = [ROOT/'tests/conformance/test_harness_smoke.py'] if suite == 'smoke' else sorted((ROOT/'tests/conformance').glob('test_*.py'))
    names = []
    for path in paths:
        for node in ast.parse(path.read_text(encoding='utf-8-sig')).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                names.append(node.name)
    if not names or len(names) != len(set(names)):
        raise HarnessError('Scenario manifest is empty or contains ambiguous duplicate names')
    return set(names)

def parse_and_print_report(report_file, suite='full'):
    try:
        data = json.loads(Path(report_file).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise HarnessError('Missing or invalid pytest JSON report') from exc
    if isinstance(data, dict) and isinstance(data.get('tests'), list):
        print('Backend result counts (smoke or incomplete scenarios do not establish parity):')
        for backend in BACKENDS:
            results = [t for t in data['tests'] if isinstance(t, dict) and isinstance(t.get('metadata'), dict) and t['metadata'].get('backend') == backend.value]
            counts = Counter(t.get('outcome', 'unknown') for t in results)
            gaps = sum(bool(t['metadata'].get('coverage_gap')) for t in results)
            print(f'{backend.value}: '+', '.join(f'{name}={count}' for name, count in sorted(counts.items()))+f', coverage_gaps={gaps}')
    if not isinstance(data, dict) or data.get('exitcode') != 0:
        raise HarnessError('Pytest report contains a nonzero/missing exit code')
    if any(c.get('outcome') == 'failed' for c in data.get('collectors', [])):
        raise HarnessError('Conformance test collection failed')
    tests = data.get('tests')
    if not isinstance(tests, list) or not tests:
        raise HarnessError('Conformance report has no tests')
    matrix = {b.value: {} for b in BACKENDS}
    for test in tests:
        metadata = test.get('metadata', {})
        backend, scenario = metadata.get('backend'), metadata.get('scenario')
        if backend not in matrix or not isinstance(scenario, str) or not scenario:
            raise HarnessError('Test result has no valid backend/scenario attribution')
        if scenario in matrix[backend]:
            raise HarnessError('Duplicate backend/scenario result')
        matrix[backend][scenario] = test.get('outcome')
        if test.get('outcome') != 'passed' or metadata.get('coverage_gap'):
            raise HarnessError(f'{backend}: {scenario} did not pass (skips/xfails/gaps are failures)')
    expected = required_scenarios(suite)
    if any(set(values) != expected for values in matrix.values()):
        raise HarnessError(f'Report lacks the complete {suite} scenario manifest on all four backends; filters cannot hide coverage gaps')
    for backend, scenarios in matrix.items():
        print(f'{backend}: {len(scenarios)} passed')
    return matrix

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', action='store_true', help='Create unique test tenants and verify their login; disposable environments only')
    parser.add_argument('--suite', choices=['full', 'smoke'], default='full')
    parser.add_argument('--skip-health-check', action='store_true', help='Skip readiness polling; mandatory health tests still run')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--report-dir', default='conformance-report')
    args = parser.parse_args(argv)
    report_dir = Path(args.report_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir/'conformance-report.json'
    report_file.unlink(missing_ok=True)  # Never accept a stale prior success.
    env = dict(os.environ, CONFORMANCE_RUN_ID=uuid.uuid4().hex, CONFORMANCE_SEED='1' if args.seed else '0')
    env['PYTHONPATH'] = str(ROOT)+os.pathsep+env.get('PYTHONPATH', '')
    failure_code = 1
    try:
        if not args.skip_health_check:
            wait_for_backends()
        target = 'tests/conformance/test_harness_smoke.py' if args.suite == 'smoke' else 'tests/conformance'
        command = [sys.executable, '-m', 'pytest', target, '--tb=short', '--json-report', '--json-report-omit=log',
            f'--json-report-file={report_file}', '-v' if args.verbose else '-q']
        result = subprocess.run(command, cwd=ROOT, env=env, check=False)
        if result.returncode > 0:
            failure_code = result.returncode
        if result.returncode != 0:
            print(f'Pytest exited {result.returncode}; report: {report_file}', file=sys.stderr)
        parse_and_print_report(report_file, args.suite)
        if result.returncode != 0:
            raise HarnessError(f'Pytest failed with exit code {result.returncode}')
        return 0
    except (HarnessError, OSError) as exc:
        print(f'Conformance FAILED: {exc}', file=sys.stderr)
        return failure_code

if __name__ == '__main__':
    sys.exit(main())
