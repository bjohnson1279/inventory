"""Import real legacy fixtures into canonical PostgreSQL; rollback all changes."""
from decimal import Decimal
import os
import uuid

import psycopg
from psycopg import sql
import pytest

from scripts.canonical_schema import SchemaError, run, select_schema
from scripts.import_canonical_data import convert, execute, load_tables


@pytest.fixture
def legacy():
    dsn = os.getenv('CANONICAL_SCHEMA_TEST_DATABASE_URL')
    if not dsn: pytest.skip('Set CANONICAL_SCHEMA_TEST_DATABASE_URL')
    with psycopg.connect(dsn,connect_timeout=5) as conn:
        try:
            source, target = 'legacy_' + uuid.uuid4().hex, 'target_' + uuid.uuid4().hex
            conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(source)))
            select_schema(conn,source)
            conn.execute('''
                CREATE TABLE tenants(id text PRIMARY KEY,name text,created_at timestamptz);
                CREATE TABLE roles(id text PRIMARY KEY,name text);
                CREATE TABLE role_permissions(role_id text,permission text);
                CREATE TABLE users(id text PRIMARY KEY,tenant_id text,email text,password_hash text,name text,active boolean);
                CREATE TABLE user_roles(user_id text,role_id text);
                CREATE TABLE locations(id text PRIMARY KEY,name text,type text);
                CREATE TABLE products(id text PRIMARY KEY,tenant_id text,sku text,name text,price numeric,department text);
                CREATE TABLE product_variants(id text PRIMARY KEY,product_id text,sku text,tracking_mode text);
                CREATE TABLE barcodes(id text PRIMARY KEY,value text,variant_id text,is_primary boolean,symbology text);
                CREATE TABLE inventory_items(id text PRIMARY KEY,sku text,location_id text,quantity numeric,allocated numeric,in_transit numeric,version integer);
                INSERT INTO tenants VALUES ('a','A',NULL),('b','B',NULL);
                INSERT INTO roles VALUES ('admin','Administrator'),('viewer','Viewer');
                INSERT INTO role_permissions VALUES ('admin','inventory:receive'),('viewer','inventory:read');
                INSERT INTO users VALUES ('u1','a',' SHOP@EXAMPLE.INVALID ','encoded-hash','Operator',false);
                INSERT INTO user_roles VALUES ('u1','admin'),('u1','viewer');
                INSERT INTO locations VALUES ('shop','Shop','STOREFRONT');
                INSERT INTO products VALUES ('p1','a','SKU','A Shirt',12.34,'Apparel');
                INSERT INTO product_variants VALUES ('v1','p1','SKU','serial');
                INSERT INTO barcodes VALUES ('barcode','123','v1',true,'EAN13');
                INSERT INTO inventory_items VALUES ('stock','SKU','shop',3.25,1.25,2,7);
            ''')
            run(conn,'apply',target)
            manifest = {'source_id':'fixture','source_schema':source,'target_schema':target,'currency':'USD','location_owners':{'shop':['a']}}
            yield conn,manifest
        finally:
            conn.rollback()


def apply(conn,manifest):
    plan = execute(conn,manifest)
    assert plan['issues'] == []
    return execute(conn,manifest,True,plan['plan_digest'])


def test_import_preserves_identity_catalog_stock_and_sources(legacy):
    conn, manifest = legacy
    before = load_tables(conn,manifest['source_schema'])
    plan = execute(conn,manifest)
    assert plan['issues'] == []
    select_schema(conn,manifest['target_schema'])
    assert conn.execute('SELECT count(*) FROM tenants').fetchone()[0] == 0
    report = execute(conn,manifest,True,plan['plan_digest'])
    assert report['applied'] and report['reconciled_rows'] == 22
    select_schema(conn,manifest['target_schema'])
    assert conn.execute('SELECT email,password_hash,display_name,active,role FROM users').fetchone() == ('shop@example.invalid','encoded-hash','Operator',False,'MULTIPLE')
    assert conn.execute('SELECT count(*) FROM user_roles').fetchone()[0] == 2
    assert conn.execute('SELECT count(*) FROM roles').fetchone()[0] == 4
    assert conn.execute('SELECT price_cents,currency,source_metadata->>\'tracking_mode\' FROM variants').fetchone() == (1234,'USD','serial')
    assert conn.execute('SELECT quantity,allocated,in_transit,version FROM stock').fetchone() == (Decimal('3.25'),Decimal('1.25'),Decimal('2'),7)
    assert conn.execute("SELECT source_metadata ? 'password_hash' FROM users").fetchone()[0] is False
    assert conn.execute('SELECT count(*) FROM import_rows').fetchone()[0] == report['reconciled_rows']
    assert load_tables(conn,manifest['source_schema']) == before


def test_repeat_import_is_insert_only_and_idempotent(legacy):
    conn, manifest = legacy
    first = apply(conn,manifest)
    second = apply(conn,manifest)
    assert second['insert'] == 0
    assert second['already_present'] == first['reconciled_rows']


@pytest.mark.parametrize('change', [
    "UPDATE products SET price=12.35",
    "INSERT INTO products VALUES ('p2','a','OTHER','Other',1,'Apparel')",
])
def test_source_changed_since_plan_blocks_import(legacy,change):
    conn,manifest=legacy
    plan=execute(conn,manifest)
    select_schema(conn,manifest['source_schema'])
    conn.execute(change)
    with pytest.raises(SchemaError,match='Plan digest changed'):
        execute(conn,manifest,True,plan['plan_digest'])
    select_schema(conn,manifest['target_schema'])
    assert conn.execute('SELECT count(*) FROM tenants').fetchone()[0] == 0


def test_no_overwrite_after_import_or_source_change(legacy):
    conn,manifest=legacy
    apply(conn,manifest)
    select_schema(conn,manifest['target_schema'])
    conn.execute("UPDATE variants SET price_cents=1235")
    plan=execute(conn,manifest)
    assert any('refusing overwrite' in issue for issue in plan['issues'])
    with pytest.raises(SchemaError,match='Import blocked'):
        execute(conn,manifest,True,plan['plan_digest'])


def test_deleted_source_and_modified_imported_source_are_detected(legacy):
    conn,manifest=legacy
    apply(conn,manifest)
    select_schema(conn,manifest['source_schema'])
    conn.execute('DELETE FROM barcodes')
    assert any('disappeared' in issue for issue in execute(conn,manifest)['issues'])
    select_schema(conn,manifest['source_schema'])
    conn.execute("UPDATE users SET password_hash='new-hash'")
    assert any('changed since prior import' in issue for issue in execute(conn,manifest)['issues'])


def test_tampered_crosswalk_is_detected(legacy):
    conn,manifest=legacy
    apply(conn,manifest)
    select_schema(conn,manifest['target_schema'])
    conn.execute("UPDATE import_rows SET target_key='{}' WHERE target_table='users'")
    assert any('changed since prior import' in issue for issue in execute(conn,manifest)['issues'])


@pytest.mark.parametrize('change,expected', [
    ("CREATE TABLE journals(id text); INSERT INTO journals VALUES ('journal')",'dedicated importer'),
    ("UPDATE products SET price=NULL",'missing price'),
    ("UPDATE products SET price=1.001",'exact nonnegative cents'),
    ("UPDATE products SET price=-1",'exact nonnegative cents'),
    ("UPDATE inventory_items SET allocated=100",'invalid stock'),
    ("INSERT INTO users VALUES ('u2','a','shop@example.invalid','another','Duplicate',true)",'email collision'),
    ("UPDATE product_variants SET product_id='missing'",'unknown parent'),
    ("UPDATE user_roles SET role_id='missing'",'unknown role'),
])
def test_unsafe_source_shapes_fail_closed(legacy,change,expected):
    conn,manifest=legacy
    select_schema(conn,manifest['source_schema'])
    conn.execute(change)
    plan=execute(conn,manifest)
    assert any(expected in issue for issue in plan['issues'])
    select_schema(conn,manifest['target_schema'])
    assert conn.execute('SELECT count(*) FROM tenants').fetchone()[0] == 0


def test_location_ownership_must_be_explicit_and_real(legacy):
    conn,manifest=legacy
    for owners,expected in [({},'explicit location_owners'),({'shop':['missing']},'does not exist')]:
        altered={**manifest,'location_owners':owners}
        assert any(expected in issue for issue in execute(conn,altered)['issues'])


def test_ambiguous_sku_across_tenants_does_not_merge_stock(legacy):
    conn,manifest=legacy
    select_schema(conn,manifest['source_schema'])
    conn.execute("INSERT INTO products VALUES ('p2','b','SKU','B Shirt',4,'Apparel')")
    conn.execute("INSERT INTO product_variants VALUES ('v2','p2','SKU','quantity')")
    assert any('ambiguous or unknown SKU owner' in issue for issue in execute(conn,manifest)['issues'])


def test_dry_run_validates_db_constraints_without_writes(legacy):
    conn,manifest=legacy
    select_schema(conn,manifest['source_schema'])
    conn.execute("INSERT INTO barcodes VALUES ('b2','456','v1',true,'EAN13')")
    plan=execute(conn,manifest)
    assert any('Target constraint validation failed' in issue for issue in plan['issues'])
    select_schema(conn,manifest['target_schema'])
    assert conn.execute('SELECT count(*) FROM tenants').fetchone()[0] == 0


def test_mid_import_failure_rolls_back_all_rows(legacy):
    conn,manifest=legacy
    select_schema(conn,manifest['source_schema'])
    conn.execute("INSERT INTO barcodes VALUES ('b2','456','v1',true,'EAN13')")
    plan=execute(conn,manifest)
    with pytest.raises(psycopg.errors.UniqueViolation),conn.transaction():
        execute(conn,manifest,True,plan['plan_digest'])
    select_schema(conn,manifest['target_schema'])
    assert conn.execute('SELECT count(*) FROM tenants').fetchone()[0] == 0
    assert conn.execute('SELECT count(*) FROM import_rows').fetchone()[0] == 0


def test_unprivileged_migration_does_not_report_rls_filtered_success(legacy):
    conn,manifest=legacy
    role='import_role_'+uuid.uuid4().hex
    conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
    conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
    with pytest.raises(SchemaError,match='BYPASSRLS'):
        execute(conn,manifest)
    conn.execute('RESET ROLE')


def test_single_sku_product_is_preserved_as_parent_and_variant(legacy):
    conn,manifest=legacy
    select_schema(conn,manifest['source_schema'])
    conn.execute('DELETE FROM barcodes; DELETE FROM product_variants')
    apply(conn,manifest)
    select_schema(conn,manifest['target_schema'])
    assert conn.execute('SELECT id,product_id,price_cents FROM variants').fetchone() == ('p1','p1',1234)


def test_missing_tenant_cannot_silently_drop_global_roles():
    records,issues=convert({'roles':[{'id':'admin','name':'Admin'}]}, {})
    assert records == []
    assert any('No tenant records' in issue for issue in issues)
