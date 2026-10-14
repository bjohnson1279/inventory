"""Exact cents, costing after consumption, and persisted double-entry journals."""
from datetime import date
import pytest
from api import key, rows, integer


@pytest.mark.asyncio
async def test_journal_entry_creation(scenario_api):
    api = scenario_api
    description = 'Conformance journal ' + key()
    lines = [{'accountCode': '1000', 'amountCents': 1250, 'type': 'debit'},
        {'accountCode': '3000', 'amountCents': 1250, 'type': 'credit'}]
    data = {'tenantId': api.tenant, 'description': description, 'date': date.today().isoformat(),
        'method': 'accrual', 'referenceId': key(), 'lines': lines}
    if api.gql:
        data['id'] = key()
        await api.graphql('createJournalEntry', {'input': ('CreateJournalEntryInput!', data)}, mutation=True)
        ledger = rows(await api.graphql('journalEntries', {'tenantId': ('ID!', api.tenant)}, 'id description lines{account{code} amountCents type}'))
        data['id'], data['description'] = key(), description + ' unbalanced'
        data['lines'][1]['amountCents'] = 1249
        await api.graphql('createJournalEntry', {'input': ('CreateJournalEntryInput!', data)}, mutation=True, reject=True)
    else:
        path = '/journal/entries' if api.php else '/accounting/journals'
        if api.python:
            data.update(mutationId=key(), reason='Conformance manual posting')
            status = await api.rest('GET', '/accounting/financial/status')
            await api.rest('POST', '/accounting/financial/activate', {'expectedVersion': status['version'], 'mutationId': key(), 'reason': 'Activate empty conformance ledger'})
        if api.php:
            data['lines'] = [{'account': l['accountCode'], 'amount': l['amountCents'], 'type': l['type']} for l in lines]
        await api.rest('POST', path, data)
        ledger = rows(await api.rest('GET', path if api.php else '/accounting/ledger'), 'entries' if api.php else None)
        data['description'] += ' unbalanced'
        data['lines'][1]['amount' if api.php else 'amountCents'] = 1249
        if api.python:
            data['mutationId'] = key()
        await api.rest('POST', path, data, reject=True)
    matches = [j for j in ledger if j['description'] == description]
    assert len(matches) == 1
    posted = matches[0]['lines']
    amounts = {side: sum(integer(l['amountCents'] if 'amountCents' in l else l['amount']) for l in posted if l['type'].lower() == side) for side in ('debit', 'credit')}
    assert amounts == {'debit': 1250, 'credit': 1250}
    ledger = rows(await api.graphql('journalEntries', {'tenantId': ('ID!', api.tenant)}, 'id description') if api.gql else await api.rest('GET', path if api.php else '/accounting/ledger'), 'entries' if api.php else None)
    assert not any(j['description'] == description + ' unbalanced' for j in ledger)


async def carrying_value(api, method, expected):
    await api.config(method)
    product = await api.product()
    # 10 @ 100 + 10 @ 300; consume 5. Receipt-only valuation cannot distinguish methods.
    await api.move('receive', product['sku'], 10, cost=100)
    await api.move('receive', product['sku'], 10, cost=300)
    await api.move('dispatch', product['sku'], 5)
    matching = [r for r in await api.valuation(method) if r['sku'] == product['sku']]
    assert len(matching) == 1
    assert integer(matching[0]['totalQuantity']) == 15
    assert integer(matching[0]['totalValueCents']) == expected
    assert (await api.stock(product['sku']))['quantity'] == 15


@pytest.mark.asyncio
async def test_stock_valuation_fifo(scenario_api):
    await carrying_value(scenario_api, 'FIFO', 3500)


@pytest.mark.asyncio
async def test_stock_valuation_lifo(scenario_api):
    await carrying_value(scenario_api, 'LIFO', 2500)


@pytest.mark.asyncio
async def test_stock_valuation_wac(scenario_api):
    await carrying_value(scenario_api, 'WAC', 3000)


@pytest.mark.asyncio
async def test_tenant_accounting_config(scenario_api):
    api = scenario_api
    await api.config('LIFO')
    config = await api.config()
    assert config['tenantId'] == api.tenant
    assert config['costingMethod'].upper() == 'LIFO'
    assert config['accountingMethod'].upper() == 'ACCRUAL'
    await api.config('FIFO')
    assert (await api.config())['costingMethod'].upper() == 'FIFO'
