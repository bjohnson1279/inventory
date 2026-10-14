"""Explicit four-backend protocols and fail-closed harness bootstrap."""
import os
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlsplit
import httpx

class BackendType(str, Enum):
    GRAPHQL = 'gql'
    EXPRESS_REST = 'express'
    PHP_REST = 'php'
    PYTHON_REST = 'python'

BACKENDS = tuple(BackendType)
CONFORMANCE_URLS = {BackendType.GRAPHQL: 'http://127.0.0.1:5040/graphql',
    BackendType.EXPRESS_REST: 'http://127.0.0.1:5050', BackendType.PHP_REST: 'http://127.0.0.1:5080',
    BackendType.PYTHON_REST: 'http://127.0.0.1:5081'}
ENV_URLS = {BackendType.GRAPHQL: ('GRAPHQL_URL', 'http://localhost:4000'),
    BackendType.EXPRESS_REST: ('EXPRESS_REST_URL', 'http://localhost:5000'),
    BackendType.PHP_REST: ('PHP_REST_URL', 'http://localhost:8000'),
    BackendType.PYTHON_REST: ('PYTHON_REST_URL', 'http://localhost:8001')}
SETUP_QUERY = '''mutation($orgName:String!,$tenantId:ID!,$adminName:String!,$adminEmail:String!,$adminPassword:String!){
setup(orgName:$orgName,tenantId:$tenantId,adminName:$adminName,adminEmail:$adminEmail,adminPassword:$adminPassword)}'''
LOGIN_QUERY = '''mutation($tenantId:ID!,$email:String!,$password:String!){login(tenantId:$tenantId,email:$email,password:$password)}'''
USERS_QUERY = 'query($tenantId:ID!){users(tenantId:$tenantId){id email}}'

class HarnessError(RuntimeError):
    pass

def graphql_endpoint(url):
    return url.rstrip('/') + '/graphql' if urlsplit(url).path in ('', '/') else url.rstrip('/')

def backend_urls(environment=None):
    env = os.environ if environment is None else environment
    result = {}
    for backend, (name, default) in ENV_URLS.items():
        value = env.get(name, default).rstrip('/')
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HarnessError(f'{name} requires an HTTP(S) URL without credentials/query/fragment')
        result[backend] = graphql_endpoint(value) if backend == BackendType.GRAPHQL else value
    return result

def origin(url):
    parsed = urlsplit(url)
    return f'{parsed.scheme}://{parsed.netloc}'

def json_response(response, backend, operation, statuses=(200,)):
    if response.status_code not in statuses:
        raise HarnessError(f'{backend.value}: {operation} returned HTTP {response.status_code}')
    try:
        value = response.json()
    except ValueError as exc:
        raise HarnessError(f'{backend.value}: {operation} returned invalid JSON') from exc
    if not isinstance(value, dict) or value.get('errors') or value.get('error') or value.get('success') is False:
        raise HarnessError(f'{backend.value}: {operation} returned an error or invalid envelope')
    return value

def check_health(client, backend, url):
    try:
        response = client.get(origin(url) + '/health')
        value = json_response(response, backend, 'health')
        if value.get('status') not in ('ok', 'healthy'):
            raise HarnessError(f'{backend.value}: health status is not healthy')
        service = value.get('service')
        expected = {BackendType.GRAPHQL: 'gql-ddd-inventory', BackendType.EXPRESS_REST: 'js-ddd-inventory',
            BackendType.PHP_REST: 'php-ddd-inventory', BackendType.PYTHON_REST: 'python-ddd-inventory'}
        if service and service not in (expected[backend], backend.value):
            raise HarnessError(f'{backend.value}: health belongs to a different service; check the configured backend URL')
    except httpx.RequestError as exc:
        raise HarnessError(f'{backend.value}: health connection failed ({type(exc).__name__})') from exc
    return value

@dataclass(frozen=True)
class Identity:
    tenant_id: str
    email: str
    token: str = field(repr=False)
    seeded: bool = False

def validate_credentials(seed=False, environment=None):
    env = os.environ if environment is None else environment
    password = env.get('CONFORMANCE_ADMIN_PASSWORD')
    if not password or len(password) < 8:
        raise HarnessError('Set CONFORMANCE_ADMIN_PASSWORD to a test-account password of at least 8 characters; --seed still requires a password')
    if not seed and not env.get('CONFORMANCE_TENANT_ID', '').strip():
        raise HarnessError('Set CONFORMANCE_TENANT_ID for an existing-tenant run, or use --seed to create unique test tenants')

def bootstrap(client, backend, url, run_id, seed=False):
    validate_credentials(seed)
    if backend == BackendType.GRAPHQL:
        url = graphql_endpoint(url)
    check_health(client, backend, url)
    tenant = f'conformance-{run_id}-{backend.value}' if seed else os.getenv('CONFORMANCE_TENANT_ID')
    email = os.getenv('CONFORMANCE_ADMIN_EMAIL', 'admin@conformance.example')
    password = os.getenv('CONFORMANCE_ADMIN_PASSWORD')
    try:
        if seed:
            payload = {'orgName': 'Conformance Test', 'tenantId': tenant, 'adminName': 'Conformance Admin',
                'adminEmail': email, 'adminPassword': password}
            if backend == BackendType.GRAPHQL:
                result = json_response(client.post(url, json={'query': SETUP_QUERY, 'variables': payload}), backend, 'setup')
                if result.get('data', {}).get('setup') is not True:
                    raise HarnessError('gql: setup did not confirm success')
            else:
                path = '/api/setup' if backend == BackendType.PHP_REST else '/api/auth/setup'
                json_response(client.post(origin(url)+path, json=payload), backend, 'setup', (200, 201))
        payload = {'tenantId': tenant, 'email': email, 'password': password}
        if backend == BackendType.GRAPHQL:
            value = json_response(client.post(url, json={'query': LOGIN_QUERY, 'variables': payload}), backend, 'login')
            token = value.get('data', {}).get('login')
        else:
            if backend == BackendType.PHP_REST:
                payload['tenant_id'] = payload.pop('tenantId')
            value = json_response(client.post(origin(url)+'/api/auth/login', json=payload), backend, 'login')
            token = value.get('token')
        if not isinstance(token, str) or not token.strip() or token == 'dummy-token':
            raise HarnessError(f'{backend.value}: login returned no usable token')
        return Identity(tenant, email, token, seed)
    except httpx.RequestError as exc:
        raise HarnessError(f'{backend.value}: bootstrap connection failed ({type(exc).__name__})') from exc
