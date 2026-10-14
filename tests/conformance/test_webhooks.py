import asyncio
import pytest
from api import key, rows, integer


def subscription():
    # Reserved .invalid domain: no messages can be delivered to an outside party.
    return {'targetUrl': 'https://conformance.invalid/' + key(), 'secret': 'conformance-only-' + key(),
        'eventTypes': ['StockChanged', 'StockReceived', 'stock.received']}


@pytest.mark.asyncio
async def test_webhook_subscription_crud(scenario_api):
    api = scenario_api
    data = subscription()
    created = await api.webhook('create', payload=data)
    identifier = created['id']
    listed = next(r for r in rows(await api.webhook('list')) if r['id'] == identifier)
    assert listed['targetUrl'] == data['targetUrl'] and listed['eventTypes'] == data['eventTypes']
    assert listed['isActive'] is True
    await api.webhook('update', identifier)
    assert next(r for r in rows(await api.webhook('list')) if r['id'] == identifier)['isActive'] is False
    await api.webhook('delete', identifier)
    assert not any(r['id'] == identifier for r in rows(await api.webhook('list')))


@pytest.mark.asyncio
async def test_webhook_delivery_logs(scenario_api):
    api = scenario_api
    created = await api.webhook('create', payload=subscription())
    try:
        product = await api.product()
        await api.move('receive', product['sku'], 2, cost=100)
        matching = []
        for attempt in range(10):
            matching = [r for r in rows(await api.webhook('deliveries')) if r['subscriptionId'] == created['id']]
            if matching:
                break
            await asyncio.sleep(1)
        assert matching, 'A stock event must persist a delivery record for its subscription'
        assert all(r['status'].upper() in ('PENDING', 'PROCESSING', 'FAILED', 'DEAD_LETTER', 'RETRY') for r in matching), 'The reserved destination cannot acknowledge successful delivery'
        assert all(integer(r['attempts']) >= 0 for r in matching)
        assert all(r.get('eventType', r.get('eventName')) in ('StockChanged', 'StockReceived', 'stock.received') for r in matching)
    finally:
        await api.webhook('delete', created['id'])
