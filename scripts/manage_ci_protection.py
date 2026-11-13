"""Audit/apply additive default-branch gates without weakening existing rulesets.

Requires an authenticated GitHub CLI with repository administration permission.
Dry-run by default. Approval counts are inherited from active default-branch rules.
"""
import argparse
import json
import subprocess
from pathlib import Path

RULESET_NAME = 'Inventory CI enforcement'
CHECKS = {
    'inventory': ['Conformance Tests', 'Lint Schemas', 'Conformance harness self-tests', 'Database contracts']
        + [f'{kind} ({backend})' for kind in ('Syntax Check', 'Unit Tests')
           for backend in ('gql-ddd-inventory', 'js-ddd-inventory', 'php-ddd-inventory', 'python-ddd-inventory')],
    'gql-ddd-inventory': ['build-and-test'],
    'js-ddd-inventory': ['test'],
    'php-ddd-inventory': ['Unit tests', 'Integration tests (with Postgres)'],
    'python-ddd-inventory': ['Run Pytest', 'PostgreSQL costing and tenant security contracts', 'Acknowledged Kafka outbox delivery'],
    'react-ddd-inventory-client': ['build-and-test'],
    'inventory-python-sidecar': ['Run Tests'],
}
for required in CHECKS.values():
    required.append('Audit Bot PR Diff & Guardrails')


def github(endpoint, method='GET', payload=None):
    command = ['gh', 'api', '--method', method, endpoint]
    if payload is not None:
        command += ['--input', '-']
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def default_branch_rule(rule, branch):
    refs = rule.get('conditions', {}).get('ref_name', {})
    include, exclude = refs.get('include', []), refs.get('exclude', [])
    return (any(ref in include for ref in ('~DEFAULT_BRANCH', '~ALL', 'refs/heads/' + branch))
            and 'refs/heads/' + branch not in exclude)


def policy(repo, existing, branch):
    approvals = max((item.get('parameters', {}).get('required_approving_review_count', 0)
                     for ruleset in existing if ruleset.get('enforcement') == 'active' and default_branch_rule(ruleset, branch)
                     for item in ruleset['rules'] if item['type'] == 'pull_request'), default=0)
    return {
        'name': RULESET_NAME, 'target': 'branch', 'enforcement': 'active',
        'bypass_actors': [],
        'conditions': {'ref_name': {'include': ['~DEFAULT_BRANCH'], 'exclude': []}},
        'rules': [
            {'type': 'deletion'}, {'type': 'non_fast_forward'},
            {'type': 'pull_request', 'parameters': {
                'required_approving_review_count': approvals,
                'dismiss_stale_reviews_on_push': True,
                'require_code_owner_review': False,
                'require_last_push_approval': False,
                'required_review_thread_resolution': True,
            }},
            {'type': 'required_status_checks', 'parameters': {
                'strict_required_status_checks_policy': True,
                'do_not_enforce_on_create': False,
                'required_status_checks': [{'context': name, 'integration_id': 15368} for name in CHECKS[repo]],
            }},
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', default='bjohnson1279')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--repo', choices=CHECKS, action='append')
    parser.add_argument('--report', type=Path, default=Path('.pytest_cache/ci-protection-application.json'))
    args = parser.parse_args()
    report = []
    args.report.parent.mkdir(parents=True, exist_ok=True)
    for repo in args.repo or CHECKS:
        endpoint = f'repos/{args.owner}/{repo}'
        metadata = github(endpoint)
        before = [github(endpoint + f'/rulesets/{item["id"]}') for item in github(endpoint + '/rulesets')]
        proposed = policy(repo, before, metadata['default_branch'])
        record = {'repo': repo, 'default_branch': metadata['default_branch'], 'before': before, 'proposed': proposed}
        report.append(record)
        # Save rollback evidence before any remote mutation, including partial runs.
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
        if args.apply:
            current = next((rule for rule in before if rule['name'] == RULESET_NAME), None)
            destination = endpoint + '/rulesets' + (f'/{current["id"]}' if current else '')
            saved = github(destination, 'PUT' if current else 'POST', proposed)
            actual = github(endpoint + f'/rulesets/{saved["id"]}')
            assert actual['enforcement'] == 'active' and actual['bypass_actors'] == []
            actual_checks = next(rule['parameters'] for rule in actual['rules'] if rule['type'] == 'required_status_checks')
            assert actual_checks['strict_required_status_checks_policy']
            assert {(check['context'], check.get('integration_id')) for check in actual_checks['required_status_checks']} == {
                (check['context'], check['integration_id']) for check in proposed['rules'][-1]['parameters']['required_status_checks']}
            record['verified'] = actual
            args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f'{repo}: {"verified" if args.apply else "proposed"} {len(CHECKS[repo])} required checks, no bypass actors', flush=True)


if __name__ == '__main__':
    main()
