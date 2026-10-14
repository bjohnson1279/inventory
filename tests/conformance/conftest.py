"""Real bootstrap, independent REST/GraphQL clients and attributable reports."""
import ast
import inspect
import os
import textwrap
import uuid
import ssl
import pytest
import pytest_asyncio
import httpx
from gql import Client
from gql.transport.httpx import HTTPXAsyncTransport
from scripts.conformance_runtime import BackendType, BACKENDS, backend_urls, bootstrap, HarnessError
from api import API

BACKEND_URLS = backend_urls()

@pytest.fixture(scope='session', params=BACKENDS, ids=lambda b: b.value)
def backend(request):
    return request.param

@pytest.fixture(scope='session')
def run_id():
    return os.getenv('CONFORMANCE_RUN_ID') or uuid.uuid4().hex

@pytest.fixture(scope='session')
def tls_context():
    # Loading the Windows trust store once avoids repeated SSL initialization
    # for hundreds of HTTP clients while retaining certificate verification.
    return ssl.create_default_context()

@pytest.fixture(scope='session')
def bootstrap_client(backend, tls_context):
    with httpx.Client(timeout=10, follow_redirects=False, verify=tls_context) as client:
        yield client

@pytest.fixture(scope='session')
def session_identity(backend, run_id, bootstrap_client):
    bootstrap_client.cookies.clear()
    return bootstrap(bootstrap_client, backend, BACKEND_URLS[backend], run_id, os.getenv('CONFORMANCE_SEED') == '1')

@pytest.fixture
def tenant_id(session_identity):
    return session_identity.tenant_id

@pytest.fixture
def auth_token(session_identity):
    return session_identity.token

@pytest_asyncio.fixture
async def rest_client(backend, auth_token):
    if backend == BackendType.GRAPHQL:
        yield None
    else:
        async with httpx.AsyncClient(base_url=BACKEND_URLS[backend], timeout=10, follow_redirects=False,
            headers={'Authorization': 'Bearer '+auth_token}) as client:
            yield client

@pytest_asyncio.fixture
async def graphql_client(backend, auth_token):
    if backend != BackendType.GRAPHQL:
        yield None
    else:
        transport = HTTPXAsyncTransport(url=BACKEND_URLS[backend], timeout=10,
            headers={'Authorization': 'Bearer '+auth_token})
        async with Client(transport=transport, fetch_schema_from_transport=False) as client:
            yield client

@pytest_asyncio.fixture
async def authenticated_client(backend, rest_client, graphql_client):
    # The other protocol fixture yields None without opening any connection.
    return graphql_client if backend == BackendType.GRAPHQL else rest_client

@pytest.fixture
def seed_data(session_identity):
    if not session_identity.seeded:
        raise HarnessError('seed_data requires --seed; no dummy seeding is permitted')
    return {'tenantId': session_identity.tenant_id, 'status': 'created-and-authenticated'}

@pytest_asyncio.fixture
async def scenario_api(backend, bootstrap_client, tls_context):
    """Each business scenario owns a fresh tenant; costing/config and AI cannot leak."""
    if os.getenv('CONFORMANCE_SEED') != '1':
        raise HarnessError('Business conformance scenarios require --seed on disposable backends')
    bootstrap_client.cookies.clear()
    identity = bootstrap(bootstrap_client, backend, BACKEND_URLS[backend], uuid.uuid4().hex, True)
    from scripts.conformance_runtime import origin
    async with httpx.AsyncClient(base_url=origin(BACKEND_URLS[backend]), timeout=10, follow_redirects=False, verify=tls_context,
        headers={'Authorization': 'Bearer ' + identity.token}) as client:
        yield API(backend, client, BACKEND_URLS[backend], identity)

def pytest_configure(config):
    config.addinivalue_line('markers', 'conformance_gap: scenario has no implementation')

def pytest_collection_modifyitems(items):
    for item in items:
        source = textwrap.dedent(inspect.getsource(item.obj))
        function = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
        body = [s for s in function.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
        if not body or all(isinstance(s, ast.Pass) or isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis for s in body):
            item.add_marker('conformance_gap')

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    if item.get_closest_marker('conformance_gap'):
        pytest.fail('Unimplemented conformance scenario: '+item.originalname, pytrace=False)

@pytest.hookimpl(optionalhook=True)
def pytest_json_runtest_metadata(item, call):
    backend = item.callspec.params.get('backend') if hasattr(item, 'callspec') else None
    return {'backend': backend.value if isinstance(backend, BackendType) else None,
        'scenario': item.originalname or item.name, 'coverage_gap': bool(item.get_closest_marker('conformance_gap'))}

def normalize_graphql_response(response):
    if isinstance(response, dict) and response.get('errors'):
        raise HarnessError('GraphQL operation returned errors')
    return response['data'] if isinstance(response, dict) and set(response) == {'data'} else response
