import pytest
from api import key
from scenario_helpers import received_serial, customer_return


@pytest.mark.asyncio
async def test_serial_registration_and_trace(scenario_api):
    api = scenario_api
    product, number = await received_serial(api)
    before = await api.trace_serial(number)
    assert before['serialNumber'] == number and before['status'].lower() in ('in_stock', 'available')
    assert (await api.stock(product['sku']))['quantity'] == 1
    await api.serial(product, number, 'sell')
    sold = await api.trace_serial(number)
    assert sold['id'] == before['id'] and sold['serialNumber'] == number
    assert sold['status'].lower() == 'sold'
    assert (await api.stock(product['sku']))['quantity'] == 0
    await api.serial(product, number, 'return')
    await api.serial(product, number, 'restock')
    final = await api.trace_serial(number)
    assert final['id'] == before['id'] and final['status'] == before['status']
    transitions = [h['to'].lower() for h in final['history']]
    assert transitions.index('sold') < transitions.index('returned') < len(transitions) - 1
    assert transitions[-1] == before['status'].lower()
    assert (await api.stock(product['sku']))['quantity'] == 1


@pytest.mark.asyncio
async def test_barcode_assignment_and_scan(scenario_api):
    api = scenario_api
    product = await api.product()
    await api.move('receive', product['sku'], 5, cost=100)
    barcode = 'CF-' + key()
    if api.gql:
        await api.graphql('assignBarcode', {'input': ('AssignBarcodeInput!', {'sku': product['sku'], 'barcodeValue': barcode,
            'symbology': 'code_128', 'source': 'internal', 'makePrimary': True})}, mutation=True)
        resolved = await api.graphql('lookupBarcode', {'barcodeValue': ('String!', barcode)})
        assert resolved in (product['sku'], product['variantId'])
        await api.graphql('dispatchBarcodeScan', {'rawScan': ('String!', barcode), 'context': ('ScanContext!', 'pos'),
            'payload': ('ScanPayloadInput!', {'locationId': api.location, 'amount': 2})}, mutation=True)
    else:
        payload = {'sku': product['sku'], 'variantId': product['variantId'], 'barcodeValue': barcode,
            'symbology': 'Code128', 'source': 'manual', 'isPrimary': True, 'makePrimary': True}
        await api.rest('POST', '/barcodes/assign', payload)
        if api.python:
            assigned = await api.rest('GET', '/barcodes')
            assert any(r['barcodeValue'] == barcode and r['sku'] == product['sku'] for r in assigned)
            scan = {'barcodeValue': barcode, 'context': 'pos', 'scannedAmount': 2, 'locationId': api.location, 'mutationId': key()}
        else:
            scan = {'rawScan': barcode, 'context': 'pos', 'payload': {'locationId': api.location, 'amount': 2}}
        await api.rest('POST', '/barcodes/scan', scan)
    assert (await api.stock(product['sku']))['quantity'] == 3, 'Scan must execute the POS deduction'


@pytest.mark.asyncio
async def test_rma_return_flow(scenario_api):
    api = scenario_api
    product, rma = await customer_return(api)
    assert rma['status'].upper() in ('RECEIVED', 'COMPLETED')
    assert (await api.stock(product['sku']))['quantity'] == 9
