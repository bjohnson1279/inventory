import pytest
from enum import Enum
import httpx
from gql import Client, gql
from gql.transport.httpx import HTTPXAsyncTransport
from typing import Dict, Any, Optional

class BackendType(Enum):
    GRAPHQL = "GRAPHQL"
    EXPRESS_REST = "EXPRESS_REST"
    PHP_REST = "PHP_REST"

BACKEND_URLS = {
    BackendType.GRAPHQL: "http://localhost:4000",
    BackendType.EXPRESS_REST: "http://localhost:5000",
    BackendType.PHP_REST: "http://localhost:8000"
}

@pytest.fixture(params=[BackendType.GRAPHQL, BackendType.EXPRESS_REST, BackendType.PHP_REST])
def backend(request):
    return request.param

@pytest.fixture
def rest_client(backend):
    if backend == BackendType.GRAPHQL:
        pytest.skip("Not a REST backend")
    url = BACKEND_URLS[backend]
    return httpx.AsyncClient(base_url=url)

@pytest.fixture
def graphql_client():
    transport = HTTPXAsyncTransport(url=BACKEND_URLS[BackendType.GRAPHQL])
    return Client(transport=transport, fetch_schema_from_transport=False)

@pytest.fixture
async def auth_token(backend, rest_client, graphql_client):
    if backend in [BackendType.EXPRESS_REST, BackendType.PHP_REST]:
        response = await rest_client.post("/api/auth/login", json={"username": "admin", "password": "password"})
        return response.json().get("token", "dummy-token")
    else:
        query = gql('''
            mutation {
                login(username: "admin", password: "password") {
                    token
                }
            }
        ''')
        response = await graphql_client.execute_async(query)
        return response["login"]["token"]

@pytest.fixture
def authenticated_client(backend, auth_token):
    if backend in [BackendType.EXPRESS_REST, BackendType.PHP_REST]:
        return httpx.AsyncClient(
            base_url=BACKEND_URLS[backend],
            headers={"Authorization": f"Bearer {auth_token}"}
        )
    else:
        transport = HTTPXAsyncTransport(
            url=BACKEND_URLS[BackendType.GRAPHQL],
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        return Client(transport=transport, fetch_schema_from_transport=False)

@pytest.fixture
def seed_data(backend):
    # Dummy seed data fixture
    return {"status": "seeded"}

def normalize_graphql_response(response: Dict[str, Any]) -> Any:
    # Basic unwrap logic if wrapped in data
    if "data" in response and len(response.keys()) == 1:
        return response["data"]
    return response

def normalize_keys(obj: Any, target_case='camel') -> Any:
    import re
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if target_case == 'camel':
                new_key = re.sub(r'_([a-z])', lambda m: m.group(1).upper(), k)
            else:
                new_key = re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), k)
            result[new_key] = normalize_keys(v, target_case)
        return result
    elif isinstance(obj, list):
        return [normalize_keys(item, target_case) for item in obj]
    return obj

def strip_volatile_fields(obj: Any, keys=('id', 'createdAt', 'updatedAt', 'occurredAt', 'assignedAt')) -> Any:
    if isinstance(obj, dict):
        return {k: strip_volatile_fields(v, keys) for k, v in obj.items() if k not in keys}
    elif isinstance(obj, list):
        return [strip_volatile_fields(item, keys) for item in obj]
    return obj
