"""Mandatory real health, bootstrap/login and protected identity probes."""
import httpx
import pytest
from conftest import BackendType, BACKEND_URLS
from scripts.conformance_runtime import check_health, origin, USERS_QUERY

def test_backend_health(backend):
    with httpx.Client(timeout=5, follow_redirects=False) as client:
        check_health(client, backend, BACKEND_URLS[backend])

@pytest.mark.asyncio
async def test_authenticated_identity(backend, authenticated_client, session_identity):
    if backend == BackendType.GRAPHQL:
        from gql import gql
        data = await authenticated_client.execute(gql(USERS_QUERY), variable_values={'tenantId': session_identity.tenant_id})
        users = data['users']
    else:
        response = await authenticated_client.get('/api/users', params={'tenantId': session_identity.tenant_id})
        assert response.status_code == 200
        value = response.json()
        users = value['users'] if isinstance(value, dict) else value
    assert isinstance(users, list)
    assert any(user.get('email') == session_identity.email for user in users)

@pytest.mark.asyncio
async def test_unauthenticated_identity_is_rejected(backend, session_identity):
    async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
        if backend == BackendType.GRAPHQL:
            response = await client.post(BACKEND_URLS[backend], json={'query': USERS_QUERY, 'variables': {'tenantId': session_identity.tenant_id}})
            assert response.status_code in (200, 401, 403)
            if response.status_code == 200:
                value = response.json()
                assert value.get('errors') and not (value.get('data') or {}).get('users')
        else:
            response = await client.get(origin(BACKEND_URLS[backend])+'/api/users', params={'tenantId': session_identity.tenant_id})
            assert response.status_code in (401, 403)
