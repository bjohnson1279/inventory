"""Keep required check names, coverage commands, and protected merge paths aligned."""
from pathlib import Path
import yaml
from scripts.manage_ci_protection import CHECKS, policy

ROOT = Path(__file__).resolve().parents[2]


def workflow(path):
    return yaml.load((ROOT / path).read_text(encoding='utf-8'), Loader=yaml.BaseLoader)


def job_names(data):
    names = set()
    for identifier, job in data['jobs'].items():
        name = job.get('name', identifier)
        matrix = job.get('strategy', {}).get('matrix', {})
        if 'backend' in matrix:
            names.update(f'{name} ({backend})' for backend in matrix['backend'])
        else:
            names.add(name)
    return names


def test_required_checks_exist_in_unfiltered_pull_request_workflows():
    for repo, required in CHECKS.items():
        directory = ROOT if repo == 'inventory' else ROOT / repo
        available = set()
        for path in (directory / '.github/workflows').glob('*.yml'):
            data = yaml.load(path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
            pull_request = data['on'].get('pull_request')
            if isinstance(pull_request, dict) and not any(key in pull_request for key in ('paths', 'paths-ignore')):
                available.update(job_names(data))
        assert set(required) <= available, (repo, set(required) - available)


def test_policy_preserves_existing_approvals_and_does_not_allow_admin_bypass():
    existing = [{'enforcement': 'active', 'conditions': {'ref_name': {'include': ['~DEFAULT_BRANCH']}},
                 'rules': [{'type': 'pull_request', 'parameters': {'required_approving_review_count': 2}}]}]
    proposed = policy('python-ddd-inventory', existing, 'master')
    assert proposed['bypass_actors'] == []
    assert next(rule for rule in proposed['rules'] if rule['type'] == 'pull_request')['parameters']['required_approving_review_count'] == 2
    assert proposed['rules'][-1]['parameters']['strict_required_status_checks_policy']
    assert all(check['integration_id'] == 15368 for check in proposed['rules'][-1]['parameters']['required_status_checks'])


def test_database_contracts_run_with_real_service_urls_and_block_conformance():
    jobs = workflow('.github/workflows/conformance.yml')['jobs']
    database = jobs['database-contracts']
    assert database['services']['postgres']
    assert database['env']['CANONICAL_SCHEMA_TEST_DATABASE_URL']
    assert database['env']['CONFORMANCE_LEDGER_DATABASE_URL']
    commands = '\n'.join(step.get('run', '') for step in database['steps'])
    assert 'test_shared_ledger_compat.py' in commands
    assert 'test_canonical_schema.py' in commands and 'test_canonical_import.py' in commands
    assert 'database-contracts' in jobs['conformance-tests']['needs']


def test_bot_workflows_queue_merges_and_do_not_swallow_security_failures():
    for repo in CHECKS:
        path = ROOT if repo == 'inventory' else ROOT / repo
        text = (path / '.github/workflows/bot-guard.yml').read_text(encoding='utf-8')
        merge = next(line for line in text.splitlines() if line.strip().startswith('gh pr merge'))
        assert '--auto' in merge and '||' not in merge
        for line in text.splitlines():
            if any(command in line for command in ('npm audit --audit-level', 'composer audit', 'bundle-audit check --update')):
                assert '|| true' not in line


def test_submodule_updates_use_pull_requests_and_explicitly_start_ci():
    text = (ROOT / '.github/workflows/submodule-sync.yml').read_text(encoding='utf-8')
    assert 'create-pull-request@' in text and 'git push origin main' not in text
    assert 'gh workflow run conformance.yml' in text
    assert 'workflow_dispatch' in workflow('.github/workflows/conformance.yml')['on']
