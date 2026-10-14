import pytest
from api import key, rows, integer


@pytest.mark.asyncio
async def test_purchase_order_lifecycle(scenario_api):
    api = scenario_api
    product = await api.product()
    if api.gql:
        created = await api.graphql('createPurchaseOrder', {'input': ('CreatePurchaseOrderInput!', {'tenantId': api.tenant,
            'supplierId': 'SUP-' + key(), 'destinationLocationId': api.location, 'items': [{'variantId': product['variantId'], 'quantity': 6}]})}, 'id status', mutation=True)
        identifier = created['id']
        assert created['status'].upper() == 'DRAFT'
        ordered = await api.graphql('placePurchaseOrder', {'id': ('ID!', identifier)}, 'id status', mutation=True)
        assert ordered['status'].upper() == 'ORDERED'
        await api.graphql('receivePurchaseOrder', {'id': ('ID!', identifier), 'actorId': ('ID!', await api.actor_id()), 'tenantId': ('ID!', api.tenant)}, 'id status', mutation=True)
        persisted = await api.graphql('purchaseOrder', {'id': ('ID!', identifier)}, 'id status items{variantId quantity}')
    else:
        if api.python:
            supplier = await api.rest('POST', '/suppliers', {'name': 'Conformance supplier', 'mutationId': key()})
            data = {'supplierId': supplier['id'], 'locationId': api.location, 'mutationId': key(), 'items': [{'sku': product['sku'], 'quantity': 6, 'unitCostCents': 125}]}
        else:
            data = {'purchaseOrderNumber': 'PO-' + key(), 'tenantId': api.tenant, 'vendorId': 'SUP-' + key(),
                'locationId': api.location, 'items': [{'variantId': product['variantId'], 'quantity': 6, 'unitCostCents': 125}]}
        created = await api.rest('POST', '/purchase-orders', data)
        identifier = created['id']
        assert created['status'].upper() == 'DRAFT'
        for action, expected in [('approve', 'APPROVED'), ('send', 'SENT')]:
            data = {'mutationId': key(), 'expectedVersion': created['version']} if api.python else {}
            await api.rest('POST', f'/purchase-orders/{identifier}/{action}', data)
            created = await api.rest('GET', '/purchase-orders/' + identifier)
            assert created['status'].upper() == expected
        receipt = {'items': [{'sku': product['sku'], 'quantity': 6}], 'receiptId': key(), 'expectedVersion': created.get('version')}
        if not api.python:
            receipt = {'items': [{'variantId': product['variantId'], 'quantity': 6}]}
        await api.rest('POST', f'/purchase-orders/{identifier}/receive', receipt)
        persisted = await api.rest('GET', '/purchase-orders/' + identifier)
    assert persisted['id'] == identifier and persisted['status'].upper() == 'RECEIVED'
    assert (await api.stock(product['sku']))['quantity'] == 6
    assert persisted['items'][0]['quantity'] == 6


@pytest.mark.asyncio
async def test_forecasting_report(scenario_api):
    api = scenario_api
    product = await api.product()
    await api.move('receive', product['sku'], 20, cost=100)
    await api.move('dispatch', product['sku'], 7)
    if api.gql:
        report = rows(await api.graphql('demandPlanningReport', {'locationId': ('String!', api.location)}, 'sku currentStock salesVelocity7d salesVelocity30d salesVelocity90d forecastedDemand30d'))
    else:
        report = rows(await api.rest('GET', '/forecasting/report', params={'locationId': api.location}))
    matching = [r for r in report if r['sku'] == product['sku']]
    assert len(matching) == 1
    row = matching[0]
    assert integer(row['currentStock']) == 13
    assert row['salesVelocity7d'] > 0 and row['salesVelocity30d'] > 0, 'Forecast must use the actual dispatch history'
    assert row.get('forecastedDemand30d', row.get('forecastedDemand')) >= 0
