"""Harness self-tests. Protocol servers below are test doubles, not parity evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import httpx
import pytest
from scripts.conformance_runtime import BackendType, BACKENDS, HarnessError, bootstrap, check_health
from scripts import run_conformance as runner

@pytest.mark.parametrize('status,payload', [(404, {'status':'ok'}), (401, {'status':'ok'}), (500, {'status':'ok'}), (200, {'status':'degraded'}), (200, {}), (302, {'status':'ok'})])
def test_health_rejects_false_success(status, payload):
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, json=payload))) as client:
        with pytest.raises(HarnessError):
            check_health(client, BackendType.PYTHON_REST, 'http://service')

@pytest.mark.parametrize('backend', BACKENDS)
def test_bootstrap_requires_real_setup_and_login(monkeypatch, backend):
    monkeypatch.setenv('CONFORMANCE_ADMIN_PASSWORD', 'unit-test-password')
    requests = []
    def handle(request):
        requests.append(request)
        if request.method == 'GET':
            return httpx.Response(200, json={'status':'ok'})
        payload = json.loads(request.content)
        if backend == BackendType.GRAPHQL:
            return httpx.Response(200, json={'data': {'setup': True}} if 'setup(' in payload['query'] else {'data': {'login':'verified-token'}})
        if request.url.path.endswith('login'):
            assert ('tenant_id' if backend == BackendType.PHP_REST else 'tenantId') in payload
            return httpx.Response(200, json={'token':'verified-token'})
        assert request.url.path == ('/api/setup' if backend == BackendType.PHP_REST else '/api/auth/setup')
        return httpx.Response(201, json={'success':True})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        identity = bootstrap(client, backend, 'http://service', 'unique', True)
    assert identity.seeded and identity.tenant_id.endswith(backend.value)
    assert len(requests) == 3
    assert 'verified-token' not in repr(identity)

@pytest.mark.parametrize('bad', [{'token':''}, {}, {'token':'dummy-token'}, {'errors':[{'message':'secret'}]}, {'success':False}])
def test_bad_authentication_cannot_fall_back(monkeypatch, bad):
    monkeypatch.setenv('CONFORMANCE_ADMIN_PASSWORD', 'unit-test-password')
    monkeypatch.setenv('CONFORMANCE_TENANT_ID', 'test-store')
    def handle(request):
        return httpx.Response(200, json={'status':'ok'} if request.method == 'GET' else bad)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(HarnessError):
            bootstrap(client, BackendType.PYTHON_REST, 'http://service', 'run')

def report():
    scenarios = ['test_backend_health','test_authenticated_identity','test_unauthenticated_identity_is_rejected']
    return {'exitcode':0, 'tests':[{'nodeid': f'test_smoke.py::{s}[{b.value}]', 'outcome':'passed',
        'metadata':{'backend':b.value,'scenario':s,'coverage_gap':False}} for b in BACKENDS for s in scenarios]}

@pytest.mark.parametrize('fault', ['missing','invalid','empty','exit','skip','xfail','gap','unattributed','missing_python','collection','duplicate','missing_scenario'])
def test_report_validation_fails_closed(tmp_path, fault):
    path = tmp_path/'report.json'
    value = report()
    if fault == 'missing':
        pass
    elif fault == 'invalid':
        path.write_text('not-json')
    else:
        if fault == 'empty': value['tests'] = []
        elif fault == 'exit': value['exitcode'] = 2
        elif fault in ('skip','xfail'): value['tests'][0]['outcome'] = 'skipped' if fault == 'skip' else 'xfailed'
        elif fault == 'gap': value['tests'][0]['metadata']['coverage_gap'] = True
        elif fault == 'unattributed': value['tests'][0]['metadata'] = {}
        elif fault == 'missing_python': value['tests'] = value['tests'][:-3]
        elif fault == 'collection': value['collectors'] = [{'outcome':'failed'}]
        elif fault == 'duplicate': value['tests'].append(value['tests'][0])
        elif fault == 'missing_scenario': value['tests'] = value['tests'][1:]
        path.write_text(json.dumps(value))
    with pytest.raises(HarnessError): runner.parse_and_print_report(path)

def test_report_accepts_complete_attributed_results(tmp_path):
    path = tmp_path/'report.json'
    path.write_text(json.dumps(report()))
    assert set(runner.parse_and_print_report(path)) == {'gql','express','php','python'}

def test_runner_rejects_subprocess_failure_and_removes_stale_report(tmp_path, monkeypatch):
    path = tmp_path/'conformance-report.json'
    path.write_text(json.dumps(report()))
    def failed(command, **kwargs):
        assert command[:3] == [sys.executable, '-m', 'pytest']
        assert kwargs['cwd'] == runner.ROOT and not path.exists()
        return subprocess.CompletedProcess(command, 3)
    monkeypatch.setattr(runner.subprocess, 'run', failed)
    assert runner.main(['--skip-health-check','--report-dir',str(tmp_path)]) == 1

@pytest.fixture
def protocol_servers(monkeypatch):
    servers = []
    for backend in BACKENDS:
        class Handler(BaseHTTPRequestHandler):
            protocol = backend
            identities = {}
            def log_message(self, *args): pass
            def reply(self, payload, status=200):
                raw = json.dumps(payload).encode()
                self.send_response(status); self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
            def do_GET(self):
                if self.path == '/health': return self.reply({'status':'healthy'})
                if self.path.startswith('/api/users'):
                    email = self.identities.get(self.headers.get('Authorization'))
                    return self.reply({'users':[{'id':'fixture-admin','email':email}]} if email else {'error':'Unauthorized'}, 200 if email else 401)
                if 'anomaly' in self.path: return self.reply({'alerts':[], 'overallRiskScore':0})
                if 'rebalance' in self.path: return self.reply({'recommendations':[], 'matrix':{}, 'summary':{}})
                self.reply({'error':'Unknown endpoint'},404)
            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
                if self.protocol == BackendType.GRAPHQL:
                    values, query = data['variables'], data['query']
                    if 'setup(' in query: return self.reply({'data':{'setup':True}})
                    if 'login(' in query:
                        token = 'fixture-token-'+values['tenantId']; self.identities['Bearer '+token] = values['email']
                        return self.reply({'data':{'login':token}})
                    email = self.identities.get(self.headers.get('Authorization'))
                    if not email: return self.reply({'errors':[{'message':'Unauthorized'}],'data':None})
                    if 'users(' in query: return self.reply({'data':{'users':[{'id':'fixture-admin','email':email}]}})
                    if 'analyzeInventoryAnomalies' in query: return self.reply({'data':{'analyzeInventoryAnomalies':{'alerts':[], 'overallRiskScore':0}}})
                    if 'rebalanceMatrix' in query: return self.reply({'data':{'rebalanceMatrix':{'recommendations':[], 'matrix':{}, 'summary':{}}}})
                if self.path in ('/api/setup','/api/auth/setup'): return self.reply({'success':True},201)
                if self.path == '/api/auth/login':
                    tenant = data['tenant_id' if self.protocol == BackendType.PHP_REST else 'tenantId']
                    token = 'fixture-token-'+tenant; self.identities['Bearer '+token] = data['email']
                    return self.reply({'token':token})
                self.reply({'error':'Unknown endpoint'},404)
        server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        servers.append((server,thread))
        from scripts.conformance_runtime import ENV_URLS
        monkeypatch.setenv(ENV_URLS[backend][0], f'http://127.0.0.1:{server.server_port}')
    monkeypatch.setenv('CONFORMANCE_ADMIN_PASSWORD','unit-test-password')
    yield
    for server, thread in servers:
        server.shutdown(); server.server_close(); thread.join(timeout=5)

def invoke_runner(tmp_path, suite):
    return subprocess.run([sys.executable, str(runner.ROOT/'scripts/run_conformance.py'), '--seed','--suite',suite,
        '--report-dir',str(tmp_path)], cwd=runner.ROOT, capture_output=True, text=True, timeout=300)

def test_actual_fixtures_and_runner_pass_all_four_smoke_protocols(protocol_servers, tmp_path):
    result = invoke_runner(tmp_path, 'smoke')
    assert result.returncode == 0, result.stdout+result.stderr
    value = json.loads((tmp_path/'conformance-report.json').read_text())
    assert len(value['tests']) == 12 and all(t['outcome']=='passed' for t in value['tests'])
    assert {t['metadata']['backend'] for t in value['tests']} == {'gql','express','php','python'}

def test_pass_only_scenarios_are_real_failures(protocol_servers, tmp_path):
    result = invoke_runner(tmp_path, 'full')
    assert result.returncode != 0
    value = json.loads((tmp_path/'conformance-report.json').read_text())
    gaps = [t for t in value['tests'] if t['metadata']['coverage_gap']]
    assert len(gaps) == 160 and all(t['outcome']=='error' for t in gaps)
    assert not any(t['outcome']=='skipped' for t in value['tests'])
