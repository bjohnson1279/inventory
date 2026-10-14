import pytest
from api import rows, integer
from db_faults import altered_ledger_payload
from scenario_helpers import movement_ledger, payload


@pytest.mark.asyncio
async def test_compliance_entries_on_stock_movement(scenario_api):
    product, entries = await movement_ledger(scenario_api)
    relevant = [e for e in entries if payload(e).get('sku') == product['sku']]
    assert len(relevant) >= 2
    assert len({e['id'] for e in relevant}) == len(relevant)
    assert any('receiv' in e['eventType'].lower() for e in relevant)
    assert any('dispatch' in e['eventType'].lower() or 'sold' in e['eventType'].lower() for e in relevant)


@pytest.mark.asyncio
async def test_hash_chain_verification(scenario_api):
    api = scenario_api
    _, entries = await movement_ledger(api)
    ordered = sorted(entries, key=lambda e: integer(e['sequenceNumber']))
    assert len({e['sequenceNumber'] for e in ordered}) == len(ordered)
    for previous, current in zip(ordered, ordered[1:]):
        assert current['previousHash'] == previous.get('hash', previous.get('currentHash'))
    assert (await api.compliance('verify'))['isValid'] is True


@pytest.mark.asyncio
async def test_tamper_detection(scenario_api):
    api = scenario_api
    _, entries = await movement_ledger(api)
    assert (await api.compliance('verify'))['isValid'] is True
    target = sorted(entries, key=lambda e: e['sequenceNumber'])[-1]
    with altered_ledger_payload(api, target['id']):
        verdict = await api.compliance('verify')
        assert verdict['isValid'] is False, 'Backend verifier must detect persisted payload corruption'
        assert verdict['failedSequenceNumber'] == target['sequenceNumber']
        assert verdict['reason']
    assert (await api.compliance('verify'))['isValid'] is True, 'Original payload must be restored'


@pytest.mark.asyncio
async def test_point_in_time_state_reconstruction(scenario_api):
    api = scenario_api
    product = await api.product()
    await api.move('receive', product['sku'], 10, cost=100)
    entries = rows(await api.compliance('ledger'))
    receipt = max(entries, key=lambda e: e['sequenceNumber'])
    timestamp = receipt.get('timestamp', receipt.get('createdAt'))
    assert timestamp
    await api.move('dispatch', product['sku'], 3)
    historical = await api.compliance('reconstruct', timestamp)
    current = await api.compliance('reconstruct')
    def balance(state):
        return next(r['quantity'] for r in state['stockLevels'] if r['sku'] == product['sku'] and r['locationId'] == api.location)
    assert balance(historical) == 10
    assert balance(current) == 7
    assert current['eventsReplayedCount'] > historical['eventsReplayedCount']


@pytest.mark.asyncio
async def test_audit_replay(scenario_api):
    api = scenario_api
    _, entries = await movement_ledger(api)
    replay = rows(await api.compliance('replay'))
    sequences = [integer(e['sequenceNumber']) for e in replay]
    assert sequences == sorted(sequences) and len(set(sequences)) == len(sequences)
    assert set(sequences) == {e['sequenceNumber'] for e in entries}
    cutoff = replay[0].get('timestamp', replay[0].get('createdAt'))
    limited = rows(await api.compliance('replay', cutoff))
    assert limited and len(limited) < len(replay)
    assert all(e['sequenceNumber'] <= replay[0]['sequenceNumber'] for e in limited)
