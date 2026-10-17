"""Real PostgreSQL contract checks; all test DDL/data rolls back per test."""
import os
import uuid

import psycopg
from psycopg import sql
import pytest

from scripts.canonical_schema import MIGRATIONS, SchemaError, migrations, normalize_schema, run, select_schema, validate_schema


@pytest.fixture
def store():
    dsn = os.getenv('CANONICAL_SCHEMA_TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('Set CANONICAL_SCHEMA_TEST_DATABASE_URL for PostgreSQL schema tests')
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        schema = 'canonical_test_' + uuid.uuid4().hex
        try:
            yield conn, schema
        finally:
            conn.rollback()


def install(store):
    conn, schema = store
    run(conn, 'apply', schema)
    select_schema(conn, schema)
    conn.execute("SELECT set_config('inventory.tenant_id','tenant-a',true)")
    conn.execute("INSERT INTO tenants(id,name) VALUES ('tenant-a','Shop A'),('tenant-b','Shop B')")
    conn.execute("INSERT INTO products(tenant_id,id,name) VALUES ('tenant-a','parent','Shirt'),('tenant-b','parent','Shirt B')")
    conn.execute("INSERT INTO variants(tenant_id,id,product_id,sku,name,currency) VALUES ('tenant-a','variant','parent','SKU','Small','USD'),('tenant-b','variant','parent','SKU','Small B','USD')")
    conn.execute("INSERT INTO locations(tenant_id,id,name) VALUES ('tenant-a','shop','Front'),('tenant-b','other-shop','Front B')")
    return conn, schema


def test_clean_install_repeat_and_physical_check(store):
    conn, schema = install(store)
    assert run(conn, 'apply', schema)['applied'] == ['0001', '0002', '0003']
    assert run(conn, 'check', schema)['pending'] == []
    select_schema(conn, schema)
    assert conn.execute('SELECT count(*) FROM products').fetchone()[0] == 2
    assert conn.execute('SELECT count(*) FROM schema_migrations').fetchone()[0] == 3


def test_upgrade_preserves_rows(store, tmp_path):
    conn, schema = store
    first = MIGRATIONS / '0001_identity_catalog_stock.sql'
    (tmp_path / first.name).write_bytes(first.read_bytes())
    run(conn, 'apply', schema, tmp_path)
    select_schema(conn, schema)
    conn.execute("INSERT INTO tenants(id,name,created_at) VALUES ('legacy-tenant','Existing',now())")
    assert run(conn, 'status', schema)['pending'] == ['0002', '0003']
    run(conn, 'apply', schema)
    select_schema(conn, schema)
    assert conn.execute('SELECT name FROM tenants').fetchone()[0] == 'Existing'


def test_failed_install_rolls_back_schema_and_registry(store, tmp_path):
    conn, schema = store
    (tmp_path / '0001_broken.sql').write_text('CREATE TABLE IF NOT EXISTS surviving (id integer); SELECT 1/0;')
    with pytest.raises(psycopg.errors.DivisionByZero), conn.transaction():
        run(conn, 'apply', schema, tmp_path)
    assert conn.execute('SELECT to_regnamespace(%s)', (schema,)).fetchone()[0] is None


def test_existing_unversioned_schema_is_not_adopted(store):
    conn, schema = store
    conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    with pytest.raises(SchemaError, match='refusing to adopt'):
        run(conn, 'apply', schema)


def test_changed_history_is_rejected(store):
    conn, schema = install(store)
    conn.execute("UPDATE schema_migrations SET checksum = repeat('0',64) WHERE version='0001'")
    with pytest.raises(SchemaError, match='history differs'):
        run(conn, 'apply', schema)


@pytest.mark.parametrize('statement', [
    "DELETE FROM schema_migrations WHERE version='0001'",
    "INSERT INTO schema_migrations(version,name,checksum) VALUES ('0099','unknown',repeat('0',64))",
])
def test_missing_or_unknown_migration_is_rejected(store, statement):
    conn, schema = install(store)
    conn.execute(statement)
    with pytest.raises(SchemaError, match='history differs'):
        run(conn, 'apply', schema)


def test_legacy_namespace_and_rows_are_untouched(store):
    conn, schema = store
    legacy = 'legacy_test_' + uuid.uuid4().hex
    conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(legacy)))
    select_schema(conn, legacy)
    # Deliberately incompatible table with the same name as a canonical table.
    conn.execute('CREATE TABLE products (sku text PRIMARY KEY, price numeric(10,2))')
    conn.execute("INSERT INTO products VALUES ('legacy-sku',12.34)")
    run(conn, 'apply', schema)
    run(conn, 'check', schema)
    select_schema(conn, legacy)
    row = conn.execute('SELECT sku,price::text FROM products').fetchone()
    assert row == ('legacy-sku', '12.34')


@pytest.mark.parametrize('change', [
    'ALTER TABLE stock DROP CONSTRAINT stock_check',
    'ALTER TABLE stock ALTER COLUMN quantity DROP NOT NULL',
    'ALTER TABLE stock ALTER COLUMN version SET DEFAULT 7',
    'ALTER TABLE stock DISABLE ROW LEVEL SECURITY',
    'DROP INDEX barcodes_one_primary',
    'ALTER TABLE journal_lines DISABLE TRIGGER journal_lines_balance',
    'CREATE TABLE rogue (id integer)',
])
def test_drift_blocks_checks_and_upgrades(store, change):
    conn, schema = install(store)
    conn.execute(change)
    for command in ('check', 'apply'):
        with pytest.raises(SchemaError, match='Physical schema drift'):
            run(conn, command, schema)


def test_pending_schema_check_fails(store):
    with pytest.raises(SchemaError, match='pending migrations'):
        run(store[0], 'check', store[1])


def test_competing_runner_fails_without_waiting(store):
    conn, schema = store
    run(conn, 'status', schema)
    with psycopg.connect(os.environ['CANONICAL_SCHEMA_TEST_DATABASE_URL'], connect_timeout=5) as other:
        with pytest.raises(SchemaError, match='Another canonical'):
            run(other, 'apply', schema)


@pytest.mark.parametrize('statement', [
    "INSERT INTO stock(tenant_id,variant_id,location_id,quantity,allocated,in_transit,version) VALUES ('tenant-a','variant','other-shop',1,0,0,0)",
    "INSERT INTO stock(tenant_id,variant_id,location_id,quantity,allocated,in_transit,version) VALUES ('tenant-a','variant','shop',1,2,0,0)",
    "INSERT INTO stock(tenant_id,variant_id,location_id,quantity,allocated,in_transit,version) VALUES ('tenant-a','variant','shop',-1,0,0,0)",
    "INSERT INTO variants(tenant_id,id,product_id,sku,name,currency) VALUES ('tenant-a','duplicate','parent','SKU','Duplicate','USD')",
    "INSERT INTO variants(tenant_id,id,product_id,sku,name,currency,price_cents) VALUES ('tenant-a','bad','parent','BAD','Bad','USD',9007199254740992)",
])
def test_catalog_stock_invariants(store, statement):
    conn, _ = install(store)
    with pytest.raises(psycopg.IntegrityError), conn.transaction():
        conn.execute(statement)


def test_tenant_rls_is_fail_closed_and_forced_for_owner(store):
    conn, schema = install(store)
    role = 'canonical_role_' + uuid.uuid4().hex
    # Requires a test administrator. The role and grants roll back with the fixture.
    conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)))
    conn.execute(sql.SQL('GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(schema), sql.Identifier(role)))
    conn.execute(sql.SQL('ALTER TABLE {}.products OWNER TO {}').format(sql.Identifier(schema), sql.Identifier(role)))
    conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
    assert conn.execute('SELECT tenant_id FROM products').fetchall() == [('tenant-a',)]
    conn.execute("SELECT set_config('inventory.tenant_id','',true)")
    assert conn.execute('SELECT count(*) FROM products').fetchone()[0] == 0
    with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
        conn.execute("INSERT INTO products(tenant_id,id,name) VALUES ('tenant-a','hidden','No')")
    conn.execute('RESET ROLE')


def journal(conn, identifier='journal'):
    conn.execute("INSERT INTO journals(tenant_id,id,number,entry_date,description,accounting_method,currency,actor_id,kind) VALUES ('tenant-a',%s,1,current_date,'Sale','ACCRUAL','USD','operator','MANUAL')", (identifier,))
    conn.execute("INSERT INTO journal_lines(tenant_id,id,journal_id,account_code,account_name,account_category,side,amount_cents) VALUES ('tenant-a','d',%s,'cash','Cash','ASSET','DEBIT',1234),('tenant-a','c',%s,'sales','Sales','REVENUE','CREDIT',1234)", (identifier, identifier))


def test_journal_deferred_balance_rejects_post_and_later_tamper(store):
    conn, _ = install(store)
    journal(conn)
    conn.execute("UPDATE journals SET status='POSTED'")
    conn.execute('SET CONSTRAINTS ALL IMMEDIATE')
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute("UPDATE journal_lines SET amount_cents=1235 WHERE id='c'")
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute("UPDATE journals SET status='DRAFT'")
    assert conn.execute('SELECT sum(amount_cents) FROM journal_lines').fetchone()[0] == 2468


def test_unbalanced_and_empty_posted_journals_rejected(store):
    conn, _ = install(store)
    journal(conn)
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute("DELETE FROM journal_lines WHERE id='c'")
        conn.execute("UPDATE journals SET status='POSTED'")
        conn.execute('SET CONSTRAINTS ALL IMMEDIATE')
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute('DELETE FROM journal_lines')
        conn.execute("UPDATE journals SET status='POSTED'")
        conn.execute('SET CONSTRAINTS ALL IMMEDIATE')


def test_failed_upgrade_preserves_existing_rows_and_history(store, tmp_path):
    conn, schema = install(store)
    for path in MIGRATIONS.glob('*.sql'):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    (tmp_path / '0004_broken.sql').write_text('ALTER TABLE products ADD COLUMN bad integer; SELECT 1/0;')
    with pytest.raises(psycopg.errors.DivisionByZero), conn.transaction():
        run(conn, 'apply', schema, tmp_path)
    assert run(conn, 'check', schema)['applied'] == ['0001', '0002', '0003']
    select_schema(conn, schema)
    assert conn.execute('SELECT count(*) FROM products').fetchone()[0] == 2


def test_stock_fractional_units_and_movement_idempotency(store):
    conn, _ = install(store)
    conn.execute("INSERT INTO stock(tenant_id,variant_id,location_id,quantity,allocated,in_transit,version) VALUES ('tenant-a','variant','shop',1.25,0.25,0,0)")
    conn.execute("INSERT INTO stock_movements(tenant_id,id,mutation_id,variant_id,location_id,quantity_delta,reason) VALUES ('tenant-a','m1','request-1','variant','shop',1.25,'Receipt')")
    with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
        conn.execute("INSERT INTO stock_movements(tenant_id,id,mutation_id,variant_id,location_id,quantity_delta,reason) VALUES ('tenant-a','m2','request-1','variant','shop',1.25,'Receipt retry')")


def test_tenant_cannot_reference_another_tenants_parent(store):
    conn, _ = install(store)
    conn.execute("INSERT INTO products(tenant_id,id,name) VALUES ('tenant-b','b-only','Private')")
    with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
        conn.execute("INSERT INTO variants(tenant_id,id,product_id,sku,name,currency) VALUES ('tenant-a','bad','b-only','BAD','Bad','USD')")


def test_outbox_json_streams_leases_and_uniqueness(store):
    conn, _ = install(store)
    conn.execute("INSERT INTO outbox_streams(tenant_id,id) VALUES ('tenant-a','stream')")
    conn.execute("INSERT INTO outbox_events(tenant_id,id,stream_id,sequence,aggregate_type,aggregate_id,event_type,payload) VALUES ('tenant-a','event','stream',1,'stock','variant','StockReceived','{\"quantity\":1}')")
    for statement in (
        "UPDATE outbox_events SET status='INFLIGHT'",
        "UPDATE outbox_events SET status='PUBLISHED'",
        "UPDATE outbox_events SET payload='\"double-encoded\"'::jsonb",
        "UPDATE outbox_events SET cycle_attempts=1",
        "INSERT INTO outbox_events SELECT tenant_id,'duplicate',stream_id,sequence,aggregate_type,aggregate_id,event_type,payload,occurred_at,status,attempts,cycle_attempts,version,next_attempt_at,last_attempt_at,last_error,lease_token,lease_expires_at,published_at FROM outbox_events",
    ):
        with pytest.raises(psycopg.IntegrityError), conn.transaction():
            conn.execute(statement)
    conn.execute("UPDATE outbox_events SET status='INFLIGHT',lease_token='claim',lease_expires_at=now()+interval '1 minute',attempts=1,cycle_attempts=1")
    conn.execute("UPDATE outbox_events SET status='PUBLISHED',lease_token=NULL,lease_expires_at=NULL,published_at=now()")


@pytest.mark.parametrize('schema', ['public','information_schema','pg_test','Bad','a;DROP SCHEMA public',''])
def test_reject_unsafe_namespace(schema):
    with pytest.raises(SchemaError):
        validate_schema(schema)


def test_migration_order_and_cross_platform_checksum(tmp_path):
    path = tmp_path / '0001_example.sql'
    path.write_bytes(b'SELECT 1;\r\n')
    windows = migrations(tmp_path)[0].checksum
    path.write_bytes(b'SELECT 1;\n')
    assert migrations(tmp_path)[0].checksum == windows
    (tmp_path / '0003_gap.sql').write_text('SELECT 3;')
    with pytest.raises(SchemaError, match='contiguous'):
        migrations(tmp_path)


def test_schema_normalization_preserves_sql_literals_and_identifier_boundaries():
    definition = '''SELECT inventory.products, "inventory".stock, other_inventory.stock, current_setting('inventory.tenant_id'), 'it''s inventory.literal' '''
    expected = '''SELECT @schema.products, @schema.stock, other_inventory.stock, current_setting('inventory.tenant_id'), 'it''s inventory.literal' '''
    assert normalize_schema(definition, 'inventory') == expected
