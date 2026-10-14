import pytest
from api import key, rows
from scenario_helpers import customer_return, quarantine_rows


@pytest.mark.asyncio
async def test_fefo_pick_order(scenario_api):
    api = scenario_api
    product = await api.product('lot')
    early, late = 'EARLY-' + key(), 'LATE-' + key()
    # Receive the later lot first to distinguish FEFO from FIFO.
    await api.move('receive', product['sku'], 5, cost=100, lot=late, expiry='2099-12-01T00:00:00Z')
    await api.move('receive', product['sku'], 5, cost=100, lot=early, expiry='2099-01-01T00:00:00Z')
    picks = await api.fefo(product['sku'], 7)
    assert [(r['lotNumber'], r['quantity']) for r in picks] == [(early, 5), (late, 2)]
    assert (await api.stock(product['sku']))['quantity'] == 10, 'Suggestions must not consume stock'


@pytest.mark.asyncio
async def test_lot_quarantine_lifecycle(scenario_api):
    api = scenario_api
    product = await api.product('lot')
    lot = 'LOT-' + key()
    await api.move('receive', product['sku'], 5, cost=100, lot=lot, expiry='2099-01-01T00:00:00Z')
    if api.gql:
        result = await api.graphql('quarantineLotBatch', {'lotNumber': ('String!', lot), 'variantId': ('String!', product['variantId']), 'reason': ('String!', 'Conformance hold')}, 'lotNumber status', mutation=True)
        assert result['status'].upper() == 'QUARANTINED'
    else:
        await api.rest('POST', '/lots/quarantine', {'lotNumber': lot, 'variantId': product['variantId'], 'reason': 'Conformance hold'})
    await api.move('dispatch', product['sku'], 1, lot=lot, reject=True)
    assert (await api.stock(product['sku']))['quantity'] == 5
    if api.gql:
        await api.graphql('releaseLotBatch', {'lotNumber': ('String!', lot), 'variantId': ('String!', product['variantId'])}, 'lotNumber status', mutation=True)
    else:
        await api.rest('POST', '/lots/release', {'lotNumber': lot, 'variantId': product['variantId']})
    await api.move('dispatch', product['sku'], 1, lot=lot)
    assert (await api.stock(product['sku']))['quantity'] == 4


@pytest.mark.asyncio
async def test_recall_traceability(scenario_api):
    api = scenario_api
    product = await api.product('lot')
    lot = 'RECALL-' + key()
    await api.move('receive', product['sku'], 10, cost=100, lot=lot, expiry='2099-01-01T00:00:00Z')
    await api.move('dispatch', product['sku'], 3, lot=lot)
    dispatches = await api.recall(lot)
    assert dispatches, 'A dispatched lot must have a traceable outbound reference'
    assert sum(r['quantity'] for r in dispatches) == 3
    assert all(r.get('locationId', r.get('location_id')) == api.location for r in dispatches)
    assert await api.recall('UNKNOWN-' + key()) == []


@pytest.mark.asyncio
async def test_quarantined_items_list(scenario_api):
    api = scenario_api
    product, rma = await customer_return(api, 'QUARANTINE')
    items = await quarantine_rows(api)
    matches = [q for q in items if q.get('sku') == product['sku'] or q.get('variantId') == product['variantId']]
    assert len(matches) == 1
    held = matches[0]
    assert held['quantity'] == 2 and held['status'].upper() == 'QUARANTINED'
    held_balance = await api.stock(product['sku'])
    # Python includes held physical units in on-hand; the other APIs exclude
    # them until resolution. All must reject consuming the held two units.
    assert held_balance['quantity'] == (9 if api.python else 7)
    await api.move('dispatch', product['sku'], 8, reject=True)
    assert await api.stock(product['sku']) == held_balance
    if api.gql:
        await api.graphql('resolveQuarantineItem', {'id': ('ID!', held['id']), 'resolution': ('String!', 'RESTOCK')}, mutation=True)
    else:
        data = {'resolution': 'RESTOCK'}
        if api.python:
            data.update(expectedVersion=held['version'], mutationId=key(), reason='Conformance inspection cleared')
        await api.rest('POST', '/returns/quarantine/' + held['id'] + '/resolve', data)
    assert not any(q['id'] == held['id'] and q['status'].upper() == 'QUARANTINED' for q in await quarantine_rows(api))
    assert (await api.stock(product['sku']))['quantity'] == 9
