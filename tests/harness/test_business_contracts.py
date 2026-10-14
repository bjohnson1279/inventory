"""Exercise scenario assertions, wire contracts and deliberate regressions offline.

The stateful transport here is a test double, never evidence of backend parity.
"""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest
from scripts.conformance_runtime import BackendType, Identity, HarnessError

ROOT = Path(__file__).resolve().parents[2]
CONFORMANCE = ROOT / 'tests/conformance'


def module(name):
    spec = importlib.util.spec_from_file_location('contract_' + name, CONFORMANCE / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture
def contract(monkeypatch):
    monkeypatch.syspath_prepend(str(CONFORMANCE))
    return module('api')


class InventoryTransport:
    def __init__(self, corrupt_balance=False, corrupt_cost=False):
        self.products = []
        self.stocks = {}
        self.method = 'FIFO'
        self.corrupt_balance, self.corrupt_cost = corrupt_balance, corrupt_cost

    def __call__(self, request):
        path, method = request.url.path, request.method
        data = json.loads(request.content) if request.content else {}
        if path == '/api/inventory/products':
            if method == 'POST':
                self.products.append({**data, 'variants': []})
                return httpx.Response(201, json=data)
            return httpx.Response(200, json=self.products)
        if path.endswith('/variants'):
            self.products[-1]['variants'].append({**data, 'id': 'variant-' + data['sku']})
            return httpx.Response(201, json=data)
        if path == '/api/accounting/tenant-config' and method == 'POST':
            self.method = data['costingMethod']
            return httpx.Response(200, json=data)
        if path.startswith('/api/accounting/tenant-config/'):
            return httpx.Response(200, json={'tenantId': 'conformance-unit', 'accountingMethod': 'ACCRUAL', 'costingMethod': self.method})
        if path == '/api/inventory' and method == 'GET':
            values = [dict(v) for v in self.stocks.values()]
            if self.corrupt_balance:
                for v in values:
                    v['quantity'] += 1
                    v['available'] += 1
            return httpx.Response(200, json=values)
        if path == '/api/accounting/valuation-report':
            expected = {'FIFO': 3500, 'LIFO': 2500, 'WAC': 3000}[self.method]
            return httpx.Response(200, json=[{'sku': sku, 'totalQuantity': v['quantity'],
                'totalValueCents': expected + int(self.corrupt_cost)} for sku, v in self.stocks.items()])
        if path.startswith('/api/inventory/') and method == 'POST':
            operation = path.rsplit('/', 1)[-1]
            sku, amount = data['sku'], data['amount']
            state = self.stocks.setdefault(sku, {'id': 'stock-' + sku, 'sku': sku, 'locationId': data['locationId'],
                'quantity': 0, 'allocated': 0, 'available': 0, 'version': 0})
            if 'expectedVersion' in data and data['expectedVersion'] != state['version']:
                return httpx.Response(409, json={'error': 'Stock version conflict'})
            if operation in ('dispatch', 'allocate') and amount > state['available'] or operation in ('release-allocation', 'fulfill-allocation') and amount > state['allocated']:
                return httpx.Response(400, json={'error': 'Insufficient stock'})
            if operation == 'receive':
                state['quantity'] += amount
            elif operation in ('dispatch', 'fulfill-allocation'):
                state['quantity'] -= amount
            if operation == 'allocate':
                state['allocated'] += amount
            elif operation in ('release-allocation', 'fulfill-allocation'):
                state['allocated'] -= amount
            state['available'] = state['quantity'] - state['allocated']
            state['version'] += 1
            return httpx.Response(200, json=state)
        return httpx.Response(404, json={'error': 'Unknown endpoint'})


@pytest.mark.asyncio
@pytest.mark.parametrize('name', ['test_receive_stock', 'test_dispatch_stock', 'test_allocate_and_release',
    'test_fulfill_allocation', 'test_concurrent_version_conflict'])
async def test_stock_scenarios_exercise_state_transitions(contract, name):
    async with httpx.AsyncClient(base_url='http://unit', transport=httpx.MockTransport(InventoryTransport())) as client:
        api = contract.API(BackendType.PYTHON_REST, client, 'http://unit', Identity('conformance-unit', 'admin@unit', 'test-token', True))
        await getattr(module('test_inventory_crud'), name)(api)


@pytest.mark.asyncio
async def test_receive_assertion_detects_a_wrong_persisted_balance(contract):
    async with httpx.AsyncClient(base_url='http://unit', transport=httpx.MockTransport(InventoryTransport(corrupt_balance=True))) as client:
        api = contract.API(BackendType.PYTHON_REST, client, 'http://unit', Identity('conformance-unit', 'admin@unit', 'test-token', True))
        with pytest.raises(AssertionError):
            await module('test_inventory_crud').test_receive_stock(api)


@pytest.mark.asyncio
@pytest.mark.parametrize('method,expected', [('FIFO', 3500), ('LIFO', 2500), ('WAC', 3000)])
@pytest.mark.parametrize('corrupt', [False, True])
async def test_costing_assertions_detect_single_cent_regressions(contract, method, expected, corrupt):
    async with httpx.AsyncClient(base_url='http://unit', transport=httpx.MockTransport(InventoryTransport(corrupt_cost=corrupt))) as client:
        api = contract.API(BackendType.PYTHON_REST, client, 'http://unit', Identity('conformance-unit', 'admin@unit', 'test-token', True))
        scenario = module('test_accounting_ledger').carrying_value
        if corrupt:
            with pytest.raises(AssertionError):
                await scenario(api, method, expected)
        else:
            await scenario(api, method, expected)


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [302, 404, 500])
async def test_missing_or_broken_capabilities_never_pass(contract, status):
    async with httpx.AsyncClient(base_url='http://unit', transport=httpx.MockTransport(lambda r: httpx.Response(status, json={}))) as client:
        api = contract.API(BackendType.PYTHON_REST, client, 'http://unit', Identity('conformance-unit', 'admin@unit', 'test-token', True))
        with pytest.raises(HarnessError):
            await api.rest('POST', '/inventory/dispatch', {})
        with pytest.raises(AssertionError):
            await api.rest('POST', '/inventory/dispatch', {}, reject=True)


@pytest.mark.asyncio
async def test_graphql_schema_errors_cannot_prove_domain_rejection(contract):
    reply = {'errors': [{'message': 'Unknown argument', 'extensions': {'code': 'GRAPHQL_VALIDATION_FAILED'}}]}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(400, json=reply))) as client:
        api = contract.API(BackendType.GRAPHQL, client, 'http://unit/graphql', Identity('conformance-unit', 'admin@unit', 'test-token', True))
        with pytest.raises(AssertionError, match='schema validation'):
            await api.graphql('dispatchStock', reject=True)


@pytest.mark.parametrize('value', [True, 1.1, '100', None])
def test_amounts_cannot_be_coerced_into_integer_cents(contract, value):
    with pytest.raises(AssertionError):
        contract.integer(value)


def test_tamper_guard_rejects_non_disposable_runs(contract, monkeypatch):
    faults = module('db_faults')
    monkeypatch.delenv('CONFORMANCE_DB_FAULTS', raising=False)
    with pytest.raises(HarnessError, match='Tamper scenario requires'):
        with faults.altered_ledger_payload(SimpleNamespace(tenant='store', backend=BackendType.PYTHON_REST), 'entry'):
            pytest.fail('Guard must run before opening a database connection')


def test_no_business_scenario_remains_pass_only():
    import ast
    functions = []
    for path in CONFORMANCE.glob('test_*.py'):
        for function in ast.parse(path.read_text(encoding='utf-8-sig')).body:
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)) and function.name.startswith('test_'):
                functions.append(function)
                body = [s for s in function.body if not isinstance(s, ast.Expr) or not isinstance(s.value, ast.Constant) or not isinstance(s.value.value, str)]
                assert body and not all(isinstance(s, ast.Pass) for s in body), function.name
    assert len(functions) == 47


def _empty_scenario(backend):
    pass


def test_placeholder_guard_still_rejects_new_empty_scenarios(contract):
    fixture_module = module('conftest')
    markers = []
    item = SimpleNamespace(obj=_empty_scenario, originalname='empty', add_marker=markers.append,
        get_closest_marker=lambda name: name in markers)
    fixture_module.pytest_collection_modifyitems([item])
    assert markers == ['conformance_gap']
    with pytest.raises(pytest.fail.Exception, match='Unimplemented conformance scenario'):
        fixture_module.pytest_runtest_setup(item)


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['receive', 'dispatch', 'allocate', 'release-allocation', 'fulfill-allocation',
    'cost-receive', 'stock', 'fefo', 'recall', 'config', 'valuation', 'warehouse-list', 'warehouse-create',
    'warehouse-delete', 'warehouse-putaway', 'warehouse-pick', 'webhook-list', 'webhook-create', 'webhook-update',
    'webhook-delete', 'serial-receive', 'serial-sell', 'serial-return', 'serial-restock', 'kit-assemble', 'kit-disassemble', 'kit-sale'])
async def test_graphql_adapter_matches_checked_in_schema(contract, operation):
    from graphql import build_ast_schema, parse, validate, print_ast, DocumentNode
    from copy import copy
    source = (ROOT/'gql-ddd-inventory/src/infrastructure/graphql/typeDefs.ts').read_text(encoding='utf-8-sig').split('`')[1]
    # graphql-tools merges duplicate named SDL blocks before building Apollo's
    # schema. Mirror that merge, while rejecting conflicting field types.
    definitions, named = [], {}
    for definition in parse(source).definitions:
        name = definition.name.value if hasattr(definition, 'name') else None
        identity = (definition.kind, name)
        if identity in named and hasattr(definition, 'fields'):
            previous = definitions[named[identity]]
            fields = {f.name.value: f for f in previous.fields}
            for field in definition.fields:
                if field.name.value in fields:
                    assert print_ast(fields[field.name.value].type) == print_ast(field.type)
                fields[field.name.value] = field
            merged = copy(previous)
            merged.fields = tuple(fields.values())
            definitions[named[identity]] = merged
        else:
            named[identity] = len(definitions)
            definitions.append(definition)
    schema = build_ast_schema(DocumentNode(definitions=tuple(definitions)))
    requests = []
    def respond(request):
        document = json.loads(request.content)
        parsed = parse(document['query'])
        errors = validate(schema, parsed)
        assert not errors, '\n'.join(e.message for e in errors)
        # Validate variables too; enum/input validation isn't covered by validate().
        from graphql.execution.values import get_variable_values
        variables = get_variable_values(schema, parsed.definitions[0].variable_definitions, document['variables'])
        assert not isinstance(variables, list), str(variables)
        field = parsed.definitions[0].selection_set.selections[0].name.value
        requests.append(field)
        value = True
        if field == 'users':
            value = [{'id': 'actor', 'email': 'admin@unit', 'role': 'admin'}]
        elif field in ('warehouseLocations','suggestPutawayLocations','optimizePickingRoute','webhookSubscriptions','suggestFefoPicking','traceProductRecall'):
            value = []
        elif field == 'stockValuationReport':
            value = {'lineItems': []}
        elif field == 'inventoryItemBySkuAndLocation':
            value = {'quantity': 0, 'allocated': 0, 'available': 0}
        return httpx.Response(200, json={'data': {field: value}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        api = contract.API(BackendType.GRAPHQL, client, 'http://unit/graphql', Identity('conformance-unit', 'admin@unit', 'test-token', True))
        product = {'sku': 'CF-SKU', 'variantId': 'variant', 'productId': 'kit', 'name': 'Kit'}
        api.kit_ids[product['sku']] = 'kit'
        if operation in ('receive', 'dispatch', 'allocate', 'release-allocation', 'fulfill-allocation'):
            await api.move(operation, 'CF-SKU', 1)
        elif operation == 'cost-receive':
            await api.move('receive', 'CF-SKU', 1, cost=100)
        elif operation == 'stock':
            await api.stock('CF-SKU')
        elif operation == 'fefo':
            await api.fefo('CF-SKU', 1)
        elif operation == 'recall':
            await api.recall('LOT')
        elif operation == 'config':
            await api.config('WAC')
        elif operation == 'valuation':
            await api.valuation('WAC')
        elif operation.startswith('warehouse-'):
            data = {'id': 'bin', 'warehouseId': 'W', 'zone': 'A', 'aisle': '01', 'rack': '01', 'shelf': '01', 'bin': '01', 'maxWeightGrams': 1000, 'maxVolumeCubicMeters': 10.0}
            payload = {'create': data, 'delete': {'id': 'bin'}, 'putaway': {'sku': 'CF-SKU', 'quantity': 1},
                'pick': {'items': [{'sku': 'CF-SKU', 'quantity': 1, 'locationId': 'bin'}]}, 'list': None}
            action = operation.split('-')[1]
            await api.warehouse(action, payload[action])
        elif operation.startswith('webhook-'):
            await api.webhook(operation.split('-')[1], 'identifier', {'targetUrl': 'https://conformance.invalid', 'secret': 'secret', 'eventTypes': ['StockReceived']})
        elif operation.startswith('serial-'):
            await api.serial(product, 'SERIAL', operation.split('-')[1])
        else:
            await api.use_kit(operation.split('-')[1], product, {'sku':'COMPONENT', 'variantId':'component'}, 1)
    assert requests
