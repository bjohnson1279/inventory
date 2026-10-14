"""Scenario setup with observable persisted facts."""
import json
from datetime import datetime, timezone
from api import key, rows


async def received_serial(api):
    product = await api.product('serial')
    number = 'SN-' + key()
    if not api.gql:
        await api.serial(product, number)
    await api.serial(product, number, 'receive')
    return product, number


async def kit_stock(api):
    component, kit = await api.product(), await api.product()
    await api.move('receive', component['sku'], 20, cost=125)
    await api.move('receive', kit['sku'], 1, cost=250)
    await api.move('dispatch', kit['sku'], 1)
    await api.define_kit(kit, component)
    return kit, component


async def movement_ledger(api):
    product = await api.product()
    await api.move('receive', product['sku'], 10, cost=100)
    await api.move('dispatch', product['sku'], 3)
    entries = rows(await api.compliance('ledger'))
    assert len(entries) >= 2, 'Real stock movements must generate ledger entries'
    assert all(e.get('tenantId', e.get('tenant_id', api.tenant)) == api.tenant for e in entries)
    return product, entries


async def customer_return(api, disposition='RESTOCK'):
    product = await api.product()
    await api.move('receive', product['sku'], 10, cost=125)
    await api.move('dispatch', product['sku'], 3)
    if api.python:
        movements = rows(await api.rest('GET', '/inventory/movements'))
        dispatch = next(m for m in movements if m['sku'] == product['sku'] and m['operation'] == 'dispatch')
        layer = dispatch['result']['consumedLayers'][0]['layerId']
        result = await api.rest('POST', '/returns/rmas', {'sourceMovementId': dispatch['id'],
            'items': [{'layerId': layer, 'quantity': 2, 'disposition': disposition}], 'reason': 'Conformance return', 'mutationId': key()})
        identifier = result['id']
        result = await api.rest('POST', f'/returns/rmas/{identifier}/authorize', {'expectedVersion': result['version'], 'mutationId': key(), 'reason': 'Approve return'})
        await api.rest('POST', f'/returns/rmas/{identifier}/receive', {'expectedVersion': result['version'], 'receiptId': key(), 'items': [{'layerId': layer, 'quantity': 2}]})
        persisted = await api.rest('GET', '/returns/rmas/' + identifier)
    else:
        payload = {'rmaNumber': 'RMA-' + key(), 'tenantId': api.tenant, 'customerId': 'CF-CUSTOMER', 'locationId': api.location,
            'items': [{'variantId': product['variantId'], 'quantity': 2, 'unitCostCents': 125}]}
        if api.gql:
            result = await api.graphql('createRma', {'input': ('CreateRmaInput!', payload)}, 'id status', mutation=True)
            identifier = result['id']
            await api.graphql('authorizeRma', {'id': ('ID!', identifier)}, mutation=True)
            await api.graphql('receiveRma', {'input': ('ReceiveRmaInput!', {'rmaId': identifier, 'items': [{'variantId': product['variantId'], 'quantityReceived': 2, 'disposition': disposition}]})}, mutation=True)
            persisted = await api.graphql('rma', {'id': ('ID!', identifier)}, 'id status items{quantity receivedQuantity disposition}')
        else:
            result = await api.rest('POST', '/returns/rma', payload)
            identifier = result['id']
            await api.rest('POST', f'/returns/rma/{identifier}/authorize', {})
            await api.rest('POST', f'/returns/rma/{identifier}/receive', {'items': [{'variantId': product['variantId'], 'quantityReceived': 2, 'disposition': disposition}]})
            persisted = await api.rest('GET', '/returns/rma/' + identifier)
    assert persisted['id'] == identifier
    return product, persisted


async def quarantine_rows(api):
    if api.gql:
        return rows(await api.graphql('quarantineItems', {'tenantId': ('ID!', api.tenant)}, 'id variantId locationId quantity reason status'))
    return rows(await api.rest('GET', '/returns/quarantine'))


async def warehouse_bin(api, bin_code='01', aisle='01', warehouse=None):
    warehouse = warehouse or 'CF' + key()[:8].upper()
    identifier = '-'.join((warehouse, 'A', aisle, '01', '01', bin_code))
    data = {'id': identifier, 'warehouseId': warehouse, 'zone': 'A', 'aisle': aisle, 'rack': '01', 'shelf': '01', 'bin': bin_code,
        'maxWeightGrams': 100000, 'maxVolumeCubicMeters': 100.0}
    await api.warehouse('create', data)
    matches = [r for r in rows(await api.warehouse('list')) if r['id'] == identifier]
    assert len(matches) == 1, 'Created bin must be persisted under its exact ID'
    return data


def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def payload(entry):
    value = entry['payload']
    return json.loads(value) if isinstance(value, str) else value
