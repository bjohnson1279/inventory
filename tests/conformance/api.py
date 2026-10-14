"""Explicit wire contracts. No dummy data, ignored errors, or endpoint guessing."""
import json
import uuid
from urllib.parse import quote
from scripts.conformance_runtime import BackendType, HarnessError


def key():
    return uuid.uuid4().hex


def rows(value, envelope=None):
    if envelope and isinstance(value, dict):
        value = value[envelope]
    assert isinstance(value, list), f'Expected list{f" in {envelope}" if envelope else ""}'
    return value


def integer(value):
    # bool, decimal truncation and missing numbers must not pass monetary assertions.
    assert type(value) is int, f'Expected integer, received {type(value).__name__}'
    return value


class API:
    def __init__(self, backend, client, url, identity):
        self.backend, self.client, self.url, self.identity = backend, client, url, identity
        self.tenant = identity.tenant_id
        self.location = 'default'
        self.actor = None
        self.serial_ids = {}
        self.kit_ids = {}

    @property
    def gql(self):
        return self.backend == BackendType.GRAPHQL

    @property
    def python(self):
        return self.backend == BackendType.PYTHON_REST

    @property
    def php(self):
        return self.backend == BackendType.PHP_REST

    async def rest(self, method, path, payload=None, params=None, reject=False):
        response = await self.client.request(method, '/api' + path, json=payload, params=params)
        if reject:
            assert response.status_code in (400, 409, 422), f'{self.backend.value}: {path} must reject invalid/conflicting input, HTTP {response.status_code}'
            return response.status_code
        if response.status_code not in (200, 201, 204):
            raise HarnessError(f'{self.backend.value}: {method} /api{path} returned HTTP {response.status_code}; required capability failed')
        if response.status_code == 204:
            return None
        try:
            value = response.json()
        except ValueError as exc:
            raise HarnessError(f'{self.backend.value}: {path} returned invalid JSON') from exc
        assert not (isinstance(value, dict) and (value.get('error') or value.get('errors') or value.get('success') is False)), f'{self.backend.value}: {path} returned an error envelope'
        return value

    async def graphql(self, field, arguments=None, selection=None, mutation=False, reject=False):
        arguments = arguments or {}
        definitions = ','.join(f'${name}:{kind}' for name, (kind, _) in arguments.items())
        values = ','.join(f'{name}:${name}' for name in arguments)
        document = ('mutation' if mutation else 'query') + (f'({definitions})' if definitions else '')
        document += '{' + field + (f'({values})' if values else '') + (f'{{{selection}}}' if selection else '') + '}'
        response = await self.client.post(self.url, json={'query': document, 'variables': {name: value for name, (_, value) in arguments.items()}})
        assert response.status_code in (200, 400), f'gql: {field} returned HTTP {response.status_code}'
        value = response.json()
        if reject:
            # Validation errors prove an invalid harness query, not business rejection.
            errors = value.get('errors')
            assert errors, f'gql: {field} accepted invalid/conflicting input'
            assert all(e.get('extensions', {}).get('code') not in ('GRAPHQL_VALIDATION_FAILED', 'GRAPHQL_PARSE_FAILED') for e in errors), f'gql: {field} failed schema validation instead of exercising the domain'
            return errors
        if value.get('errors'):
            messages = [e.get('message', 'unknown error') for e in value['errors']]
            raise HarnessError(f'gql: {field} failed: {messages}')
        assert 'data' in value and field in value['data'], f'gql: {field} missing from response'
        result = value['data'][field]
        assert result is not None and result is not False, f'gql: {field} did not confirm success'
        return result

    async def users(self):
        if self.gql:
            return rows(await self.graphql('users', {'tenantId': ('ID!', self.tenant)}, 'id email role'))
        return rows(await self.rest('GET', '/users', params={'tenantId': self.tenant}), 'users' if self.python else None)

    async def actor_id(self):
        if self.actor is None:
            matches = [u for u in await self.users() if u['email'] == self.identity.email]
            assert len(matches) == 1
            self.actor = matches[0]['id']
        return self.actor

    async def product(self, tracking='quantity'):
        product_id, sku = str(uuid.uuid4()), 'CF-' + key()[:20].upper()
        name = 'Conformance ' + sku
        if self.gql:
            await self.graphql('createProduct', {'id': ('ID!', product_id), 'name': ('String!', name)}, mutation=True)
            await self.graphql('addProductVariant', {'productId': ('ID!', product_id), 'sku': ('String!', sku),
                'trackingMode': ('TrackingMode!', tracking), 'attributes': ('[AttributeInput!]!', [])}, mutation=True)
            products = rows(await self.graphql('products', selection='id name variants{id sku}'))
        else:
            path = '/inventory/products' if self.python else '/catalog/products'
            await self.rest('POST', path, {'id': product_id, 'name': name})
            # Python represents quantity-tracked lots in cost layers, not a lot enum.
            await self.rest('POST', f'{path}/{product_id}/variants', {'sku': sku, 'trackingMode': 'quantity' if self.python and tracking == 'lot' else tracking, 'attributes': []})
            products = rows(await self.rest('GET', path), 'products' if self.php else None)
        matching = [v for p in products for v in p['variants'] if v['sku'] == sku]
        assert len(matching) == 1, 'Created variant must be persisted and uniquely readable'
        return {'sku': sku, 'variantId': matching[0]['id'], 'productId': product_id, 'name': name}

    async def stock(self, sku, location=None):
        location = location or self.location
        if self.gql:
            value = await self.graphql('inventoryItemBySkuAndLocation', {'sku': ('String!', sku), 'locationId': ('String!', location)}, 'id sku locationId quantity allocated available version')
        elif self.python:
            matches = [r for r in rows(await self.rest('GET', '/inventory', params={'limit': 1000})) if r['sku'] == sku and r['locationId'] == location]
            assert len(matches) == 1, f'Expected one persisted stock record for {sku}/{location}'
            value = matches[0]
        else:
            value = await self.rest('GET', '/inventory/' + quote(sku, safe=''), params={('location_id' if self.php else 'locationId'): location})
        for name in ('quantity', 'allocated', 'available'):
            integer(value[name])
        assert value['available'] == value['quantity'] - value['allocated']
        return value

    async def move(self, operation, sku, amount, cost=None, lot=None, expiry=None, version=None, reject=False, location=None):
        location = location or self.location
        if self.gql:
            field = {'receive': 'receiveStock', 'dispatch': 'dispatchStock', 'allocate': 'allocateStock',
                'release-allocation': 'releaseAllocation', 'fulfill-allocation': 'fulfillAllocation'}[operation]
            args = {'sku': ('String!', sku), 'locationId': ('String!', location), 'amount': ('Int!', amount)}
            selection = 'id sku locationId quantity allocated available version'
            if operation == 'receive' and cost is not None:
                field, selection = 'receiveStockWithLot', None
                args = {'sku': ('String!', sku), 'locationId': ('String!', location), 'quantity': ('Int!', amount),
                    'unitCostCents': ('Int!', cost), 'lotNumber': ('String!', lot or 'CF-' + key()),
                    'expirationDate': ('String!', expiry or '2099-01-01T00:00:00Z')}
            if version is not None:
                # A missing public concurrency contract is a genuine conformance failure.
                args['expectedVersion'] = ('Int!', version)
            return await self.graphql(field, args, selection, mutation=True, reject=reject)
        payload = {'sku': sku, 'tenantId': self.tenant, 'locationId': location, 'amount': amount}
        if self.python:
            payload['mutationId'] = key()
        if self.php:
            payload = {'sku': sku, 'location_id': location, 'quantity' if operation in ('receive', 'dispatch') else 'amount': amount}
        if cost is not None:
            payload['unit_cost_cents' if self.php else 'unitCostCents'] = cost
        if lot:
            payload['lot_number' if self.php else 'lotNumber'] = lot
        if expiry:
            payload['expiration_date' if self.php else 'expirationDate'] = expiry
        if version is not None:
            payload['expectedVersion'] = version
        return await self.rest('POST', '/inventory/' + operation, payload, reject=reject)

    async def config(self, method=None):
        costing = {'FIFO': 'fifo', 'LIFO': 'lifo', 'WAC': 'weighted_average_cost'}
        if method is not None:
            payload = {'tenantId': self.tenant, 'accountingMethod': 'ACCRUAL' if self.python else 'accrual', 'costingMethod': method if self.python else costing[method]}
            if self.gql:
                await self.graphql('saveTenantAccountingConfig', {'input': ('SaveTenantAccountingConfigInput!', payload)}, mutation=True)
            else:
                await self.rest('POST', '/accounting/tenant-config', payload)
        if self.gql:
            return await self.graphql('tenantAccountingConfig', {'tenantId': ('ID!', self.tenant)}, 'tenantId accountingMethod costingMethod')
        return await self.rest('GET', '/accounting/tenant-config/' + quote(self.tenant, safe=''))

    async def valuation(self, method):
        if self.gql:
            value = await self.graphql('stockValuationReport', {'tenantId': ('ID!', self.tenant), 'locationId': ('String', self.location),
                'method': ('CostingMethod', {'FIFO': 'fifo', 'LIFO': 'lifo', 'WAC': 'weighted_average_cost'}[method])},
                'lineItems{sku quantityOnHand unitCostCents totalValueCents}')
            return [{**r, 'totalQuantity': r['quantityOnHand']} for r in rows(value, 'lineItems')]
        path = '/reports/valuation' if self.php else '/accounting/valuation-report'
        value = await self.rest('GET', path, params={'tenantId': self.tenant, 'locationId': self.location, 'method': method})
        return rows(value, 'items' if self.php and isinstance(value, dict) else None)

    async def fefo(self, sku, amount):
        if self.gql:
            return rows(await self.graphql('suggestFefoPicking', {'sku': ('String!', sku), 'quantity': ('Int!', amount)}, 'locationId lotNumber quantity expirationDate'))
        return rows(await self.rest('GET', '/inventory/fefo-pick', params={'sku': sku, 'quantity': amount}))

    async def recall(self, lot):
        if self.gql:
            return rows(await self.graphql('traceProductRecall', {'lotNumber': ('String!', lot)}, 'ledgerEntryId quantity locationId referenceId actorId occurredAt'))
        return rows(await self.rest('GET', '/inventory/reports/recall/' + quote(lot, safe='')))

    async def serial(self, product, number, action='register'):
        actor = await self.actor_id()
        payload = {'serialNumber': number, 'variantId': product['variantId'], 'tenantId': self.tenant,
            'locationId': self.location, 'actorId': actor, 'referenceId': 'CF-' + key(), 'purchaseOrderId': 'CF-' + key(),
            'saleId': 'CF-' + key(), 'unitCostCents': 100}
        if self.gql:
            if action in ('register', 'receive'):
                assert action == 'receive', 'GraphQL serial registration occurs during receive'
                data = {k: payload[k] for k in ('variantId', 'serialNumber', 'tenantId', 'locationId', 'actorId', 'purchaseOrderId', 'unitCostCents')}
                return await self.graphql('receiveSerializedItem', {'input': ('ReceiveSerializedInput!', data)}, mutation=True)
            fields = {'sell': ('sellSerializedItem', 'SellSerializedInput!', ('serialNumber', 'tenantId', 'saleId', 'actorId')),
                'return': ('returnSerializedItem', 'ReturnSerializedInput!', ('serialNumber', 'tenantId', 'referenceId', 'actorId')),
                'restock': ('restockSerializedItem', 'RestockSerializedInput!', ('serialNumber', 'tenantId', 'locationId', 'referenceId', 'actorId'))}
            field, kind, names = fields[action]
            return await self.graphql(field, {'input': (kind, {n: payload[n] for n in names})}, mutation=True)
        if self.python:
            data = {'mutationId': key(), 'reason': 'Conformance serial lifecycle'}
            if action == 'register':
                data.update(sku=product['sku'], serialNumber=number, locationId=self.location)
                return await self.rest('POST', '/serials', data)
            state = await self.trace_serial(number)
            data.update(expectedVersion=state['version'], referenceId=payload['referenceId'])
            if action == 'receive':
                data.update(unitCostCents=100, locationId=self.location)
            return await self.rest('POST', f'/serials/{quote(number, safe="")}/{action}', data)
        if self.php:
            if action == 'register':
                result = await self.rest('POST', '/serials', {'variant_id': product['variantId'], 'serial_number': number, 'tenant_id': self.tenant, 'location_id': self.location})
                self.serial_ids[number] = result['id']
                return result
            return await self.rest('POST', f'/serials/{self.serial_ids[number]}/{action}',
                {'location_id': self.location, 'purchase_order_id': payload['purchaseOrderId'], 'unit_cost_cents': 100,
                 'sale_id': payload['saleId'], 'reference_id': payload['referenceId'], 'actor_id': actor})
        return await self.rest('POST', '/serials/' + action, payload)

    async def trace_serial(self, number):
        if self.gql:
            return await self.graphql('serializedItemBySerial', {'serialNumber': ('String!', number), 'tenantId': ('ID!', self.tenant)},
                'id variantId serialNumber locationId status history{from to reason referenceId}')
        if self.php:
            return await self.rest('GET', '/serials/lookup', params={'serial_number': number, 'tenant_id': self.tenant})
        path = '/serials/trace/' + quote(number, safe='') if self.python else '/serials/' + quote(number, safe='') + '/history'
        return await self.rest('GET', path, params={'tenantId': self.tenant})

    async def define_kit(self, product, component):
        payload = {'sku': product['sku'], 'name': product['name']}
        if self.gql:
            identifier = str(uuid.uuid4())
            await self.graphql('createKit', {'id': ('ID!', identifier), 'sku': ('String!', product['sku']), 'name': ('String!', product['name']),
                'components': ('[KitComponentInput!]!', [{'variantId': component['variantId'], 'quantity': 2}])}, mutation=True)
            self.kit_ids[product['sku']] = identifier
        elif self.python:
            await self.rest('POST', '/kits', {**payload, 'components': [{'sku': component['sku'], 'quantity': 2}], 'expectedVersion': 0, 'mutationId': key(), 'reason': 'Conformance bill of materials'})
        elif self.php:
            identifier = (await self.rest('POST', '/kits', payload))['id']
            await self.rest('POST', f'/kits/{identifier}/components', {'variant_id': component['variantId'], 'quantity': 2})
            self.kit_ids[product['sku']] = identifier
        else:
            await self.rest('POST', '/kits/create', {**payload, 'components': [{'variantId': component['variantId'], 'quantity': 2}]})

    async def use_kit(self, operation, kit, component, quantity):
        payload = {'kitSku': kit['sku'], 'quantity': quantity, 'locationId': self.location,
            'tenantId': self.tenant, 'actorId': await self.actor_id(), 'referenceId': 'CF-' + key()}
        if self.gql:
            if operation == 'sale':
                payload.update(kitId=self.kit_ids[kit['sku']], sku=kit['sku'], name=kit['name'], components=[{'variantId': component['variantId'], 'quantity': 2}])
                payload.pop('kitSku')
                return await self.graphql('sellKit', {'input': ('SellKitInput!', payload)}, mutation=True)
            return await self.graphql('assembleKit' if operation == 'assemble' else 'disassembleKit',
                {'input': ('AssembleKitInput!' if operation == 'assemble' else 'DisassembleKitInput!', payload)}, mutation=True)
        if self.python:
            state = await self.rest('GET', '/kits/' + kit['sku'])
            affected = (kit, component) if operation == 'assemble' else (kit,) if operation == 'disassemble' else (component,)
            balances = [await self.stock(p['sku']) for p in affected]
            payload = {**payload, 'mutationId': key(), 'reason': 'Conformance kit ' + operation, 'expectedVersion': state['version'],
                'stockVersions': {r['sku']: r['version'] for r in balances}}
            payload.pop('actorId')
        elif self.php:
            payload = {'kit_sku': kit['sku'], 'quantity': quantity, 'location_id': self.location, 'reference_id': payload['referenceId']}
            if operation == 'sale':
                return await self.rest('POST', f'/kits/{self.kit_ids[kit["sku"]]}/sell', {**payload, 'sale_id': key(), 'actor_id': await self.actor_id()})
        elif operation == 'sale':
            payload['saleId'] = payload['referenceId']
            return await self.rest('POST', '/kits/dispatch', payload)
        return await self.rest('POST', '/kits/' + operation, payload)

    async def compliance(self, operation, timestamp=None):
        if self.gql:
            # These public operations are intentionally required, even where absent.
            field = {'ledger': 'complianceLedger', 'verify': 'verifyComplianceLedger', 'reconstruct': 'reconstructState', 'replay': 'replayAudit'}[operation]
            args = {'tenantId': ('String!', self.tenant)}
            if timestamp:
                args['upToTimestamp' if operation == 'replay' else 'timestamp'] = ('String', timestamp)
            selection = {'ledger': 'id sequenceNumber eventType timestamp hash previousHash payload',
                'verify': 'isValid failedSequenceNumber reason', 'reconstruct': 'tenantId eventsReplayedCount stockLevels{sku locationId quantity}',
                'replay': 'sequenceNumber eventType timestamp hash previousHash payload'}[operation]
            return await self.graphql(field, args, selection)
        params = {'tenantId': self.tenant}
        if timestamp:
            params['timestamp'] = timestamp
        return await self.rest('POST' if operation == 'verify' else 'GET', '/compliance/' + operation, params=params)

    async def warehouse(self, operation, payload=None):
        if self.gql:
            if operation == 'list':
                return await self.graphql('warehouseLocations', selection='id warehouseId zone maxWeightGrams maxVolumeCubicMeters')
            if operation == 'create':
                return await self.graphql('createWarehouseLocation', {'input': ('CreateWarehouseLocationInput!', payload)}, 'id', mutation=True)
            if operation == 'delete':
                return await self.graphql('deleteWarehouseLocation', {'id': ('ID!', payload['id'])}, mutation=True)
            if operation == 'putaway':
                return await self.graphql('suggestPutawayLocations', {'input': ('PutawayInput!', payload)}, 'locationId quantity remainingWeightGrams remainingVolumeCubicMeters')
            if operation == 'pick':
                return await self.graphql('optimizePickingRoute', {'tenantId': ('ID!', self.tenant), 'items': ('[PickItemInput!]!', payload['items'])}, 'warehouseId items{sku locationId quantity}')
            return await self.graphql('slottingSuggestions', selection='sku currentLocationId recommendedLocationId estimatedSavings')
        if operation == 'create':
            data = dict(payload)
            return await self.rest('POST', '/warehouse-locations', data)
        if operation == 'delete':
            return await self.rest('DELETE', '/warehouse-locations/' + quote(payload['id'], safe=''))
        paths = {'list': '', 'putaway': '/putaway-suggestions', 'pick': '/optimize-pick-route', 'slotting': '/slotting-suggestions'}
        return await self.rest('POST' if operation in ('putaway', 'pick') else 'GET', '/warehouse-locations' + paths[operation], payload,
            params={'tenantId': self.tenant})

    async def outbox(self, operation):
        if self.gql:
            return await self.graphql('outboxStats' if operation == 'stats' else 'deadLetterEvents',
                selection='pending processing processed failed total' if operation == 'stats' else 'id eventType status attempts')
        path = '/outbox/stats' if operation == 'stats' else '/outbox/dead-letter'
        return await self.rest('GET', path)

    async def cache(self, operation):
        if self.gql:
            return await self.graphql('cacheStats' if operation == 'stats' else 'clearCache',
                {'tenantId': ('String', self.tenant)} if operation == 'clear' else None,
                'hits misses hitRatio invalidations activeKeysCount' if operation == 'stats' else None,
                mutation=operation == 'clear')
        return await self.rest('GET' if operation == 'stats' else 'POST', '/admin/cache/' + operation, params={'tenantId': self.tenant})

    async def webhook(self, operation, identifier=None, payload=None):
        base = '/webhook-subscriptions' if self.php else '/webhooks/subscriptions'
        if self.gql:
            if operation == 'list':
                return await self.graphql('webhookSubscriptions', selection='id tenantId targetUrl eventTypes isActive')
            if operation == 'create':
                return await self.graphql('createWebhookSubscription', {k: (('[String!]!' if k == 'eventTypes' else 'String!'), v) for k,v in payload.items()}, 'id', mutation=True)
            if operation == 'delete':
                return await self.graphql('deleteWebhookSubscription', {'id': ('ID!', identifier)}, mutation=True)
            if operation == 'update':
                return await self.graphql('updateWebhookSubscription', {'id': ('ID!', identifier), 'isActive': ('Boolean', False)}, 'id isActive', mutation=True)
            return await self.graphql('webhookDeliveries', selection='id subscriptionId eventType status attempts')
        if operation == 'create':
            return await self.rest('POST', base, payload)
        if operation == 'update':
            return await self.rest('PUT', base + '/' + identifier, {'isActive': False})
        if operation == 'delete':
            return await self.rest('DELETE', base + '/' + identifier)
        return await self.rest('GET', base if operation == 'list' else '/webhooks/deliveries')
