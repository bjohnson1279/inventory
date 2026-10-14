import pytest
from api import key, rows, integer
from scenario_helpers import warehouse_bin


@pytest.mark.asyncio
async def test_warehouse_location_crud(scenario_api):
    api = scenario_api
    location = await warehouse_bin(api)
    listed = next(r for r in rows(await api.warehouse('list')) if r['id'] == location['id'])
    assert listed['warehouseId'] == location['warehouseId']
    assert listed['maxWeightGrams'] == 100000
    assert listed['maxVolumeCubicMeters'] == 100.0
    await api.warehouse('delete', {'id': location['id']})
    assert not any(r['id'] == location['id'] for r in rows(await api.warehouse('list')))


@pytest.mark.asyncio
async def test_putaway_suggestions(scenario_api):
    api = scenario_api
    product = await api.product()
    location = await warehouse_bin(api)
    suggestions = rows(await api.warehouse('putaway', {'sku': product['sku'], 'quantity': 4}))
    assert suggestions, 'Capacity-compatible empty bins must produce a putaway suggestion'
    assert sum(integer(r['quantity'] if 'quantity' in r else r['suggestedQuantity']) for r in suggestions) == 4
    known = {r['id'] for r in rows(await api.warehouse('list'))}
    assert all(r['locationId'] in known for r in suggestions), 'Suggestions must reference persisted bins'
    assert any(r['locationId'] == location['id'] for r in suggestions)


@pytest.mark.asyncio
async def test_pick_route_optimization(scenario_api):
    api = scenario_api
    near = await warehouse_bin(api, aisle='01')
    far = await warehouse_bin(api, aisle='09', warehouse=near['warehouseId'])
    items = [{'sku': 'CF-FAR', 'quantity': 2, 'locationId': far['id']},
        {'sku': 'CF-NEAR', 'quantity': 1, 'locationId': near['id']}]
    routes = rows(await api.warehouse('pick', {'items': items}))
    assert len(routes) == 1 and routes[0]['warehouseId'] == near['warehouseId']
    picked = rows(routes[0], 'items')
    assert [(r['sku'], r['locationId'], r['quantity']) for r in picked] == [
        ('CF-NEAR', near['id'], 1), ('CF-FAR', far['id'], 2)], 'Route must preserve quantities and order bins by aisle'


@pytest.mark.asyncio
async def test_slotting_suggestions(scenario_api):
    api = scenario_api
    product = await api.product()
    near = await warehouse_bin(api, aisle='01')
    far = await warehouse_bin(api, aisle='99', warehouse=near['warehouseId'])
    await api.move('receive', product['sku'], 20, cost=100, location=far['id'])
    await api.move('dispatch', product['sku'], 10, location=far['id'])
    suggestions = rows(await api.warehouse('slotting'))
    matching = [r for r in suggestions if r['sku'] == product['sku']]
    assert matching, 'High-velocity stock in a distant bin should produce an actionable move'
    assert any(r['currentLocationId'] == far['id'] and r['recommendedLocationId'] == near['id'] and r['estimatedSavings'] > 0 for r in matching)
