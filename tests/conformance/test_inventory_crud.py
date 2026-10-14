"""Persisted stock arithmetic and optimistic concurrency, on each backend."""
import asyncio
import pytest


@pytest.mark.asyncio
async def test_receive_stock(scenario_api):
    api = scenario_api
    product = await api.product()
    await api.move('receive', product['sku'], 10)
    first = await api.stock(product['sku'])
    assert (first['quantity'], first['allocated'], first['available']) == (10, 0, 10)
    await api.move('receive', product['sku'], 5)
    second = await api.stock(product['sku'])
    assert second['quantity'] == 15 and second['version'] > first['version']


@pytest.mark.asyncio
async def test_dispatch_stock(scenario_api):
    api = scenario_api
    product = await api.product()
    await api.move('receive', product['sku'], 10, cost=125)
    await api.move('dispatch', product['sku'], 4)
    before = await api.stock(product['sku'])
    assert before['quantity'] == before['available'] == 6
    await api.move('dispatch', product['sku'], 7, reject=True)
    assert await api.stock(product['sku']) == before, 'Rejected overselling must not mutate stock/version'


@pytest.mark.asyncio
async def test_allocate_and_release(scenario_api):
    api = scenario_api
    product = await api.product()
    await api.move('receive', product['sku'], 10, cost=100)
    await api.move('allocate', product['sku'], 4)
    reserved = await api.stock(product['sku'])
    assert (reserved['quantity'], reserved['allocated'], reserved['available']) == (10, 4, 6)
    await api.move('allocate', product['sku'], 7, reject=True)
    assert await api.stock(product['sku']) == reserved
    await api.move('release-allocation', product['sku'], 3)
    released = await api.stock(product['sku'])
    assert (released['quantity'], released['allocated'], released['available']) == (10, 1, 9)


@pytest.mark.asyncio
async def test_fulfill_allocation(scenario_api):
    api = scenario_api
    product = await api.product()
    await api.move('receive', product['sku'], 10, cost=100)
    await api.move('allocate', product['sku'], 4)
    await api.move('fulfill-allocation', product['sku'], 3)
    balance = await api.stock(product['sku'])
    assert (balance['quantity'], balance['allocated'], balance['available']) == (7, 1, 6)
    await api.move('fulfill-allocation', product['sku'], 2, reject=True)
    assert await api.stock(product['sku']) == balance


@pytest.mark.asyncio
async def test_concurrent_version_conflict(scenario_api):
    api = scenario_api
    product = await api.product()
    await api.move('receive', product['sku'], 10, cost=100)
    before = await api.stock(product['sku'])
    results = await asyncio.gather(*(api.move('dispatch', product['sku'], 2, version=before['version']) for _ in range(2)), return_exceptions=True)
    assert sum(not isinstance(r, BaseException) for r in results) == 1, 'Exactly one writer with the same expected version must succeed'
    rejected = next(r for r in results if isinstance(r, BaseException))
    assert 'HTTP 409' in str(rejected), f'Expected explicit conflict, received {rejected}'
    after = await api.stock(product['sku'])
    assert after['quantity'] == 8 and after['version'] == before['version'] + 1
