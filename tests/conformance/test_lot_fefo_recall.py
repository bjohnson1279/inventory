import pytest
from conftest import BackendType
from comparator import assert_behavioral_match

@pytest.mark.asyncio
async def test_fefo_pick_order(backend, authenticated_client):
    pass

@pytest.mark.asyncio
async def test_lot_quarantine_lifecycle(backend, authenticated_client):
    pass

@pytest.mark.asyncio
async def test_recall_traceability(backend, authenticated_client):
    pass

@pytest.mark.asyncio
async def test_quarantined_items_list(backend, authenticated_client):
    pass
