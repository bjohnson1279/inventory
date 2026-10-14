import pytest
from scenario_helpers import kit_stock


@pytest.mark.asyncio
async def test_kit_assembly(scenario_api):
    api = scenario_api
    kit, component = await kit_stock(api)
    await api.use_kit('assemble', kit, component, 3)
    assert (await api.stock(kit['sku']))['quantity'] == 3
    assert (await api.stock(component['sku']))['quantity'] == 14


@pytest.mark.asyncio
async def test_kit_disassembly(scenario_api):
    api = scenario_api
    kit, component = await kit_stock(api)
    await api.use_kit('assemble', kit, component, 3)
    await api.use_kit('disassemble', kit, component, 2)
    assert (await api.stock(kit['sku']))['quantity'] == 1
    assert (await api.stock(component['sku']))['quantity'] == 18


@pytest.mark.asyncio
async def test_kit_dispatch(scenario_api):
    api = scenario_api
    kit, component = await kit_stock(api)
    await api.use_kit('sale', kit, component, 2)
    assert (await api.stock(component['sku']))['quantity'] == 16
    assert (await api.stock(kit['sku']))['quantity'] == 0, 'Virtual kit sale consumes components exactly once'
