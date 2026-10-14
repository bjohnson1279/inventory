import json
import pytest
from api import key, rows


@pytest.mark.asyncio
async def test_cross_dock_evaluation(scenario_api):
    api = scenario_api
    variant = 'CF-' + key()
    po = 'PO-' + key()
    inbound = [{'variantId': variant, 'quantity': 6}]
    orders = [{'orderId': 'LOW', 'variantId': variant, 'quantity': 5, 'priority': 1},
        {'orderId': 'HIGH', 'variantId': variant, 'quantity': 4, 'priority': 10},
        {'orderId': 'OTHER', 'variantId': 'OTHER', 'quantity': 99, 'priority': 99}]
    if api.gql:
        result = await api.graphql('evaluateCrossDocking', {'purchaseOrderId': ('String!', po),
            'inboundItemsJson': ('String!', json.dumps(inbound)), 'backordersJson': ('String!', json.dumps(orders))},
            'purchaseOrderId variantId inboundQuantity recommendedCrossDockQuantity matchingBackorders{orderId requiredQuantity priority}', mutation=True)
        result = [result]
    else:
        result = rows(await api.rest('POST', '/cross-dock/evaluate', {'purchaseOrderId': po, 'inboundItems': inbound, 'backorders': orders}))
    assert len(result) == 1
    match = result[0]
    assert (match['purchaseOrderId'], match['variantId'], match['inboundQuantity'], match['recommendedCrossDockQuantity']) == (po, variant, 6, 6)
    assert [(r['orderId'], r['requiredQuantity']) for r in match['matchingBackorders']] == [('HIGH', 4), ('LOW', 2)]


@pytest.mark.asyncio
async def test_drop_ship_fulfillment(scenario_api):
    api = scenario_api
    product = await api.product()
    order = 'ORDER-' + key()
    supplier = 'SUPPLIER-' + key()
    data = {'orderId': order, 'variantId': product['variantId'], 'quantity': 3, 'supplierId': supplier}
    if api.gql:
        result = await api.graphql('createDropShipOrder', {k: ('Int!' if k == 'quantity' else 'String!', v) for k,v in data.items()}, mutation=True)
        orders = rows(await api.graphql('purchaseOrders', {'tenantId': ('ID!', api.tenant)}, 'id supplierId items{variantId quantity}'))
    else:
        result = await api.rest('POST', '/fulfillment/drop-ship', data)
        orders = rows(await api.rest('GET', '/purchase-orders', params={'tenantId': api.tenant}))
    assert result['orderId'] == order and result['quantity'] == 3
    identifier = result['dropShipPoId']
    matching = [po for po in orders if po['id'] == identifier]
    assert len(matching) == 1, 'An invented PO ID is not a completed drop-ship workflow'
    assert matching[0].get('supplierId', matching[0].get('vendorId')) == supplier
    assert matching[0]['items'][0]['quantity'] == 3
