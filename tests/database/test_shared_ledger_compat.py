"""PostgreSQL migration checks, isolated by a schema rolled back after each test.

Set CONFORMANCE_LEDGER_DATABASE_URL to a local disposable PostgreSQL connection.
"""
import json
import os
import uuid
from pathlib import Path
import psycopg
from psycopg import sql
import pytest

MIGRATION = Path(__file__).resolve().parents[2]/'php-ddd-inventory/docker/postgres/init/21_shared_ledger_compat.sql'


@pytest.fixture
def database():
    url = os.environ.get('CONFORMANCE_LEDGER_DATABASE_URL')
    if not url:
        pytest.fail('Set CONFORMANCE_LEDGER_DATABASE_URL for PostgreSQL migration validation')
    with psycopg.connect(url, connect_timeout=5) as connection:
        try:
            name = 'cf_ledger_' + uuid.uuid4().hex
            connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(name)))
            connection.execute(sql.SQL('SET LOCAL search_path TO {}').format(sql.Identifier(name)))
            connection.execute('''CREATE TABLE journal_entries (
                id varchar(100) PRIMARY KEY, tenant_id varchar(100) NOT NULL,
                entry_date date NOT NULL, description text, reference_id text,
                method varchar(50), lines jsonb NOT NULL);
                CREATE TABLE journal_lines (id varchar(100) PRIMARY KEY,
                entry_id varchar(100) NOT NULL, account_code varchar(100) NOT NULL,
                amount_cents integer NOT NULL, type varchar(50) NOT NULL, memo text);''')
            yield connection
        finally:
            connection.rollback()


def migrate(db):
    db.execute(MIGRATION.read_text(encoding='utf-8'))


def legacy_entry(db, identifier='php-entry', method='cash', amount=1250):
    lines = [{'account': '1000', 'amount': amount, 'type': 'debit', 'memo': 'Cash'},
        {'account': '3000', 'amount': amount, 'type': 'credit', 'memo': 'Equity'}]
    db.execute('INSERT INTO journal_entries(id,tenant_id,entry_date,description,method,lines) VALUES (%s,%s,CURRENT_DATE,%s,%s,%s)',
        (identifier, 'tenant-1', 'Legacy journal', method, json.dumps(lines)))


def test_migration_exposes_the_columns_used_by_prisma(database):
    migrate(database)
    assert database.execute('SELECT accounting_method FROM journal_entries').fetchall() == []
    assert database.execute('SELECT journal_entry_id,account_name,account_category,debit_or_credit FROM journal_lines').fetchall() == []


def test_historical_cash_journals_and_amounts_are_preserved(database):
    legacy_entry(database)
    migrate(database)
    assert database.execute('SELECT method,accounting_method FROM journal_entries').fetchone() == ('cash', 'cash')
    assert database.execute('SELECT account_code,amount_cents,debit_or_credit FROM journal_lines ORDER BY account_code').fetchall() == [('1000', 1250, 'debit'), ('3000', 1250, 'credit')]
    assert database.execute('SELECT lines FROM journal_entries').fetchone()[0][0]['amount'] == 1250


def test_new_php_writes_are_readable_by_express(database):
    migrate(database)
    legacy_entry(database)
    assert database.execute('SELECT accounting_method FROM journal_entries').fetchone()[0] == 'cash'
    assert database.execute('SELECT count(*) FROM journal_lines WHERE journal_entry_id=%s', ('php-entry',)).fetchone()[0] == 2


def test_new_express_writes_are_readable_by_php(database):
    migrate(database)
    database.execute("INSERT INTO journal_entries(id,tenant_id,entry_date,description,accounting_method) VALUES ('express-entry','tenant-2',CURRENT_DATE,'Express journal','accrual')")
    database.execute("INSERT INTO journal_lines(id,journal_entry_id,account_code,account_name,account_category,debit_or_credit,amount_cents) VALUES ('debit','express-entry','1000','Cash','asset','debit',2400),('credit','express-entry','3000','Equity','equity','credit',2400)")
    method, lines = database.execute('SELECT method,lines FROM journal_entries WHERE id=%s', ('express-entry',)).fetchone()
    assert method == 'accrual'
    assert sorted((l['account'],l['amount'],l['type']) for l in lines) == [('1000',2400,'debit'),('3000',2400,'credit')]


def test_php_updates_replace_normalized_lines_without_duplicates(database):
    migrate(database)
    legacy_entry(database)
    changed = [{'account': '1000', 'amount': 500, 'type': 'debit'}, {'account': '3000', 'amount': 500, 'type': 'credit'}]
    database.execute('UPDATE journal_entries SET lines=%s,method=%s WHERE id=%s', (json.dumps(changed), 'accrual', 'php-entry'))
    assert database.execute('SELECT accounting_method FROM journal_entries').fetchone()[0] == 'accrual'
    assert database.execute('SELECT sum(amount_cents),count(*) FROM journal_lines').fetchone() == (1000, 2)


def test_migration_is_repeatable_and_preserves_line_identifiers(database):
    legacy_entry(database)
    migrate(database)
    before = database.execute('SELECT id,account_code,amount_cents FROM journal_lines ORDER BY id').fetchall()
    migrate(database)
    assert database.execute('SELECT id,account_code,amount_cents FROM journal_lines ORDER BY id').fetchall() == before
    assert database.execute('SELECT count(*) FROM journal_entries').fetchone()[0] == 1
