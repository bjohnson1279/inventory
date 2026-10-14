import pytest
from api import key, rows, integer


@pytest.mark.asyncio
async def test_user_management(scenario_api):
    api = scenario_api
    email = 'cf-' + key() + '@conformance.example'
    role = 'warehouse_operator'
    if api.gql:
        created = await api.graphql('inviteUser', {'tenantId': ('ID!', api.tenant), 'email': ('String!', email), 'role': ('String!', role)}, 'userId', mutation=True)
    else:
        created = await api.rest('POST', '/users', {'tenantId': api.tenant, 'email': email, 'role': role})
    users = await api.users()
    matching = [u for u in users if u['email'] == email]
    assert len(matching) == 1
    identifier = created.get('userId', created.get('id'))
    assert matching[0]['id'] == identifier and matching[0]['role'].upper() == role.upper()
    if api.gql:
        await api.graphql('updateUserRole', {'tenantId': ('ID!', api.tenant), 'userId': ('ID!', identifier), 'role': ('String!', 'viewer')}, mutation=True)
    else:
        await api.rest('PATCH', f'/users/{identifier}/role', {'tenantId': api.tenant, 'role': 'USER' if api.python else 'viewer'})
    updated = next(u for u in await api.users() if u['id'] == identifier)
    assert updated['role'].upper() == ('USER' if api.python else 'VIEWER')
    assert any(u['email'] == api.identity.email and u['role'].upper() == 'ADMIN' for u in await api.users())


@pytest.mark.asyncio
async def test_audit_cycle_count(scenario_api):
    api = scenario_api
    product = await api.product()
    await api.move('receive', product['sku'], 10, cost=100)
    if api.python:
        count = await api.rest('POST', '/cycle-counts/start', {'name': 'Conformance count', 'location_id': api.location,
            'skus': [product['sku']], 'is_blind_count': False, 'mutation_id': key()})
        identifier = count['record_id']
        await api.rest('POST', '/cycle-counts/submit', {'record_id': identifier, 'revision': count['revision'], 'mutation_id': key(),
            'items': [{'sku': product['sku'], 'counted_quantity': 8}]})
        persisted = next(c for c in rows(await api.rest('GET', '/cycle-counts')) if c['record_id'] == identifier)
        assert persisted['status'].upper() == 'SUBMITTED'
        assert persisted['items'][0]['counted_quantity'] == 8
        await api.rest('POST', f'/cycle-counts/{identifier}/approve', {'revision': persisted['revision'], 'mutation_id': key(), 'reason': 'Review confirmed shrinkage'})
    elif api.gql:
        count = await api.graphql('startCycleCount', {'tenantId': ('ID!', api.tenant), 'name': ('String!', 'Conformance count'), 'isBlindCount': ('Boolean', False)}, 'id status', mutation=True)
        await api.graphql('submitCycleCount', {'id': ('ID!', count['id']), 'countedLines': ('JSON!', [{'sku': product['sku'], 'countedQuantity': 8}])}, mutation=True)
        persisted = rows(await api.graphql('getCycleCounts', {'tenantId': ('ID!', api.tenant)}, 'id status'))
        assert any(c['id'] == count['id'] for c in persisted), 'Acknowledged counts must survive a subsequent read'
    else:
        base = '/cycle-count' if api.php else '/cycle-counts'
        count = await api.rest('POST', base + '/start', {'tenantId': api.tenant, 'name': 'Conformance count', 'isBlindCount': False})
        await api.rest('POST', base + '/submit', {'id': count['id'], 'countedLines': [{'sku': product['sku'], 'countedQuantity': 8}]})
        assert any(c['id'] == count['id'] for c in rows(await api.rest('GET', base)))
    assert (await api.stock(product['sku']))['quantity'] == 8, 'Reviewed counts must reconcile persisted stock'


@pytest.mark.asyncio
async def test_outbox_stats_and_dead_letters(scenario_api):
    api = scenario_api
    before = await api.outbox('stats')
    product = await api.product()
    await api.move('receive', product['sku'], 3, cost=100)
    after = await api.outbox('stats')
    names = ('pending', 'published', 'failed') if api.python else ('pending', 'processing', 'processed', 'failed') if api.gql else ('totalPending', 'totalProcessed', 'totalDeadLettered')
    assert all(integer(after[name]) >= 0 for name in names)
    assert sum(after[name] for name in names) > sum(before[name] for name in names), 'Mutation must durably enqueue an event'
    dead = rows(await api.outbox('dead'))
    assert len(dead) <= 100
    assert len({e['id'] for e in dead}) == len(dead)
    assert all(integer(e['attempts']) >= 1 for e in dead)
    assert all(e.get('status', 'DEAD_LETTER').upper() in ('DEAD_LETTER', 'FAILED') for e in dead)


@pytest.mark.asyncio
async def test_rfid_tag_operations(scenario_api):
    api = scenario_api
    epc, sku, serial = key()[:24].upper(), 'CF-' + key()[:16].upper(), 'SN-' + key()
    if api.gql:
        await api.graphql('assignRfidTag', {'epc': ('String!', epc), 'sku': ('String!', sku), 'serialNumber': ('String!', serial)}, mutation=True)
        tags = rows(await api.graphql('rfidTags', {'tenantId': ('ID!', api.tenant)}, 'epc sku serialNumber status'))
    else:
        await api.rest('POST', '/rfid/assign', {'epc': epc, 'sku': sku, 'serialNumber': serial})
        tags = rows(await api.rest('GET', '/rfid/tags', params={'tenantId': api.tenant}), 'tags')
    matching = [t for t in tags if t['epc'] == epc]
    assert len(matching) == 1
    assert (matching[0]['sku'], matching[0]['serialNumber'], matching[0]['status'].upper()) == (sku, serial, 'ACTIVE')


@pytest.mark.asyncio
async def test_tier2_redis_cache_and_outbox_invalidation(scenario_api):
    api = scenario_api
    await api.cache('clear')
    product = await api.product()
    await api.move('receive', product['sku'], 5, cost=100)
    await api.stock(product['sku'])
    baseline = await api.cache('stats')
    await api.stock(product['sku'])
    warmed = await api.cache('stats')
    assert integer(warmed['hits']) > integer(baseline['hits']), 'Repeated stock reads must exercise the real cache'
    await api.move('dispatch', product['sku'], 2)
    assert (await api.stock(product['sku']))['quantity'] == 3, 'Mutation must not return the cached pre-dispatch balance'
    after = await api.cache('stats')
    assert integer(after['invalidations']) > integer(warmed['invalidations']), 'Outbox/mutation invalidation must be observable'
