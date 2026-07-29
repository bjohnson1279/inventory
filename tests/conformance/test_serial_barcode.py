import pytest
from conftest import BackendType
from comparator import assert_behavioral_match

@pytest.mark.asyncio
async def test_serial_registration_and_trace(backend, authenticated_client):
    pass

@pytest.mark.asyncio
async def test_barcode_assignment_and_scan(backend, authenticated_client):
    pass

@pytest.mark.asyncio
async def test_rma_return_flow(backend, authenticated_client):
    pass
