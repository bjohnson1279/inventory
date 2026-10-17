"""Plan/apply an insert-only, reconciled import from a legacy schema in one DB.

Supports the shared PHP/TS identity/catalog/stock layout. Populated unsupported
tables block the import; no source rows are changed. A plan digest binds apply
to the exact source, target and ownership manifest inspected during planning.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

try:
    from scripts.canonical_schema import SchemaError, run as check_schema, validate_schema
except ModuleNotFoundError:  # python scripts/import_canonical_data.py
    from canonical_schema import SchemaError, run as check_schema, validate_schema

EXCLUDED = {'tenant_registry': 'Connection routing configuration, not tenant business records',
            '_prisma_migrations': 'Legacy migration history', 'schema_migrations': 'Legacy migration history'}
SUPPORTED = {'tenants','users','roles','permissions','user_roles','role_permissions',
             'locations','products','product_variants','barcodes','barcode_assignments',
             'inventory_items','inventories','product_locations'}
KEYS = {
    'tenants': ('id',), 'roles': ('tenant_id','id'), 'permissions': ('tenant_id','id'),
    'users': ('tenant_id','id'), 'role_permissions': ('tenant_id','role_id','permission_id'),
    'user_roles': ('tenant_id','user_id','role_id'), 'locations': ('tenant_id','id'),
    'products': ('tenant_id','id'), 'variants': ('tenant_id','id'),
    'barcodes': ('tenant_id','value'), 'stock': ('tenant_id','variant_id','location_id'),
}


def json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(type(value).__name__)


def encoded(value):
    return json.dumps(value, default=json_value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def metadata(row):
    # Preserve unmapped business fields, but never duplicate credential hashes.
    return json.loads(encoded({k:v for k,v in row.items() if k not in ('password_hash','token_hash')}))


@dataclass
class Record:
    source_table: str
    source_key: str
    source_hash: str
    table: str
    values: dict

    @property
    def key(self):
        return {name:self.values[name] for name in KEYS[self.table]}

    @property
    def tenant(self):
        return self.values['id'] if self.table == 'tenants' else self.values['tenant_id']


def load_tables(conn, schema):
    names = [row[0] for row in conn.execute("SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relkind IN ('r','p') AND NOT c.relispartition ORDER BY c.relname", (schema,))]
    result = {}
    for name in names:
        # Routing metadata contains encrypted database credentials; count only.
        if name in EXCLUDED:
            count = conn.execute(sql.SQL('SELECT count(*) FROM {}.{}').format(sql.Identifier(schema),sql.Identifier(name))).fetchone()[0]
            result[name] = {'excluded_count': count}
        else:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql.SQL('SELECT * FROM {}.{}').format(sql.Identifier(schema),sql.Identifier(name)))
                result[name] = sorted(cur.fetchall(), key=encoded)
    return result


def convert(source, manifest):
    """Pure conversion: reject ambiguity instead of guessing tenant or SKU ownership."""
    issues, records = [], []
    seen = {}
    tenants = {str(r['id']) for r in source.get('tenants', [])}

    def add(stable, row, target, values, key=None):
        # Empty legacy timestamps use the DB insertion default; preserve NULL in metadata.
        values['source_metadata'] = metadata(row)
        identity = (target, encoded({name:values[name] for name in KEYS[target]}))
        record = Record(stable, encoded(key if key is not None else {k:row[k] for k in ('id',) if k in row}), digest(row), target, values)
        if identity in seen:
            issues.append(f'Multiple source rows target the same {target} key')
            return
        seen[identity] = record
        records.append(record)

    def owned(table, row):
        tenant = row.get('tenant_id')
        if tenant is not None:
            if str(tenant) not in tenants:
                raise SchemaError(f'{table}: tenant is absent from tenants')
            return [str(tenant)]
        # Roles and permission definitions are explicitly global in this layout.
        return sorted(tenants)

    for table, rows in source.items():
        if table not in SUPPORTED and table not in EXCLUDED and rows:
            issues.append(f'{table}: {len(rows)} rows need a dedicated importer')
    if not tenants and any(source.get(table) for table in SUPPORTED - {'tenants'}):
        issues.append('No tenant records; cannot assign populated legacy data')
    try:
        for row in source.get('tenants', []):
            values = {'id':str(row['id']), 'name':row['name']}
            if row.get('created_at'): values['created_at'] = row['created_at']
            add('tenants', row, 'tenants', values)
        role_owners = {}
        for row in source.get('roles', []):
            for tenant in owned('roles', row):
                role_owners[(tenant,str(row['id']))] = True
                add('roles', row, 'roles', {'tenant_id':tenant,'id':str(row['id']),'name':row['name']})

        permission_defs = {str(r['id']):r for r in source.get('permissions', [])}
        permission_ids = set(permission_defs)
        for row in source.get('role_permissions', []):
            permission_ids.add(str(row.get('permission', row.get('permission_id'))))
        for tenant in sorted(tenants):
            for identifier in sorted(permission_ids):
                row = permission_defs.get(identifier, {'id':identifier})
                if row.get('tenant_id') is not None and str(row['tenant_id']) != tenant: continue
                add('permissions' if identifier in permission_defs else 'role_permissions', row, 'permissions', {'tenant_id':tenant,'id':identifier}, {'permission':identifier})
        for row in source.get('role_permissions', []):
            role = str(row['role_id'])
            assigned = False
            for tenant in owned('role_permissions', row):
                if (tenant,role) not in role_owners: continue
                assigned = True
                permission = str(row.get('permission',row.get('permission_id')))
                add('role_permissions', row, 'role_permissions', {'tenant_id':tenant,'role_id':role,'permission_id':permission}, {'role':role,'permission':permission})
            if not assigned: raise SchemaError('role_permissions: unknown or cross-tenant role')

        user_index = {str(r['id']):r for r in source.get('users', [])}
        memberships = {}
        for row in source.get('user_roles', []):
            user = user_index.get(str(row['user_id']))
            if user is None: raise SchemaError('user_roles: unknown user')
            tenant, role = str(user['tenant_id']), str(row['role_id'])
            if (tenant,role) not in role_owners: raise SchemaError('user_roles: cross-tenant or unknown role')
            memberships.setdefault(str(user['id']), []).append(role)
        emails = set()
        for row in source.get('users', []):
            tenant = str(row['tenant_id'])
            if tenant not in tenants: raise SchemaError('users: unknown tenant')
            email = row['email'].strip().lower()
            if (tenant,email) in emails: raise SchemaError('users: normalized email collision')
            emails.add((tenant,email))
            roles = sorted(memberships.get(str(row['id']), []))
            # This compatibility field never grants a missing membership.
            role = roles[0] if len(roles) == 1 else ('MULTIPLE' if roles else 'NONE')
            values = {'tenant_id':tenant,'id':str(row['id']),'email':email,'password_hash':row['password_hash'],
                      'display_name':row.get('name'),'active':row['active'],'role':role}
            if row.get('created_at'): values['created_at'] = row['created_at']
            add('users', row, 'users', values)
        for row in source.get('user_roles', []):
            tenant = str(user_index[str(row['user_id'])]['tenant_id'])
            add('user_roles', row, 'user_roles', {'tenant_id':tenant,'user_id':str(row['user_id']),'role_id':str(row['role_id'])}, {'user':str(row['user_id']),'role':str(row['role_id'])})

        location_keys = set()
        for row in source.get('locations', []):
            owners = [str(row['tenant_id'])] if row.get('tenant_id') else manifest.get('location_owners', {}).get(str(row['id']))
            if not owners: raise SchemaError('locations: explicit location_owners mapping required')
            if len(set(owners)) != len(owners): raise SchemaError('locations: duplicate owner')
            for tenant in owners:
                if tenant not in tenants: raise SchemaError('locations: mapped tenant does not exist')
                location_keys.add((tenant,str(row['id'])))
                add('locations', row, 'locations', {'tenant_id':tenant,'id':str(row['id']),'name':row['name']})

        parents = {}
        for row in source.get('products', []):
            owners = owned('products', row)
            if len(owners) != 1 and row.get('tenant_id') is None:
                raise SchemaError('products: unscoped parent requires a dedicated tenant mapping')
            if not owners: raise SchemaError('products: unknown tenant')
            tenant = owners[0]
            parents[str(row['id'])] = (tenant,row)
            values = {'tenant_id':tenant,'id':str(row['id']),'name':row['name'],'description':row.get('description')}
            if row.get('created_at'): values['created_at'] = row['created_at']
            add('products', row, 'products', values)
        variants = list(source.get('product_variants', []))
        explicit_parents = {str(r['product_id']) for r in variants}
        for parent_id, (tenant,row) in parents.items():
            if parent_id not in explicit_parents and row.get('sku'):
                variants.append({**row,'product_id':parent_id,'_single_sku':True})
        variant_index, sku_index = {}, {}
        for row in variants:
            parent = parents.get(str(row['product_id']))
            if parent is None: raise SchemaError('product_variants: unknown parent')
            tenant, product = parent
            if row.get('tenant_id') is not None and str(row['tenant_id']) != tenant: raise SchemaError('product_variants: cross-tenant parent')
            sku = str(row['sku'])
            if (tenant,sku) in sku_index: raise SchemaError('product_variants: duplicate tenant SKU')
            amount = row.get('price_amount',row.get('price',product.get('price_amount',product.get('price'))))
            # An unknown selling price cannot safely become a zero-priced item.
            if amount is None: raise SchemaError('product_variants: missing price; explicit pricing migration required')
            cents = Decimal(str(amount)) * 100
            if not cents.is_finite() or cents != cents.to_integral_value() or not 0 <= cents <= 9007199254740991:
                raise SchemaError('product_variants: price is not exact nonnegative cents')
            currency = row.get('currency') or product.get('currency') or manifest.get('currency')
            if not currency: raise SchemaError('product_variants: currency required')
            identifier = str(row['id'])
            sku_index[(tenant,sku)] = identifier
            variant_index[identifier] = (tenant,identifier)
            add('products' if row.get('_single_sku') else 'product_variants', row, 'variants', {'tenant_id':tenant,'id':identifier,'product_id':str(row['product_id']),
                'sku':sku,'name':row.get('name',product['name']),'price_cents':int(cents),'currency':currency,'base_unit':row.get('base_unit','each')})
        for table in ('barcodes','barcode_assignments'):
            for row in source.get(table, []):
                variant = variant_index.get(str(row['variant_id']))
                if variant is None: raise SchemaError(f'{table}: unknown variant')
                tenant, identifier = variant
                if row.get('tenant_id') is not None and str(row['tenant_id']) != tenant: raise SchemaError(f'{table}: cross-tenant barcode')
                add(table, row, 'barcodes', {'tenant_id':tenant,'variant_id':identifier,'value':row.get('value',row.get('barcode_value')),'is_primary':row['is_primary']})

        for table in ('inventory_items','inventories','product_locations'):
            for row in source.get(table, []):
                if table == 'product_locations':
                    parent = parents.get(str(row['product_id']))
                    if parent is None: raise SchemaError('product_locations: unknown product')
                    tenant, product = parent
                    identifier = sku_index.get((tenant,str(product.get('sku'))))
                    if identifier is None: raise SchemaError('product_locations: ambiguous product/variant stock')
                    if row.get('open_box_quantity',0) or row.get('damaged_quantity',0):
                        raise SchemaError('product_locations: nonzero condition stock needs a disposition migration')
                    quantity, allocated, transit = row['stock_quantity'],row['allocated_quantity'],row['in_transit_quantity']
                else:
                    matches = [(t,v) for (t,sku),v in sku_index.items() if sku == str(row['sku']) and (not row.get('tenant_id') or t == str(row['tenant_id']))]
                    if len(matches) != 1: raise SchemaError(f'{table}: ambiguous or unknown SKU owner')
                    tenant, identifier = matches[0]
                    quantity, allocated, transit = row['quantity'],row['allocated'],row['in_transit']
                location = str(row.get('location_id',row.get('locationId')))
                if (tenant,location) not in location_keys: raise SchemaError(f'{table}: missing tenant location')
                quantities = [Decimal(str(v)) for v in (quantity,allocated,transit)]
                if any(not v.is_finite() or v < 0 or v != v.quantize(Decimal('.000001')) for v in quantities) or quantities[1] > quantities[0]:
                    raise SchemaError(f'{table}: invalid stock quantities')
                add(table, row, 'stock', {'tenant_id':tenant,'variant_id':identifier,'location_id':location,'quantity':quantities[0],
                    'allocated':quantities[1],'in_transit':quantities[2],'version':row.get('version',row.get('version_id',0))}, {'variant':identifier,'location':location})
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        issues.append(f'Unsupported or invalid legacy shape ({type(exc).__name__})')
    except SchemaError as exc:
        issues.append(str(exc))
    return records, issues


def select_row(conn, schema, record):
    where = sql.SQL(' AND ').join(sql.SQL('{} = %s').format(sql.Identifier(k)) for k in record.key)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql.SQL('SELECT * FROM {}.{} WHERE {}').format(sql.Identifier(schema),sql.Identifier(record.table),where), list(record.key.values()))
        return cur.fetchone()


def parameters(values):
    return [Jsonb(v) if isinstance(v,dict) else v for v in values]


def insert_records(conn, target, records):
    for record in records:
        if select_row(conn,target,record) is None:
            names = list(record.values)
            conn.execute(sql.SQL('INSERT INTO {}.{} ({}) VALUES ({})').format(sql.Identifier(target),sql.Identifier(record.table),
                sql.SQL(',').join(map(sql.Identifier,names)),sql.SQL(',').join(sql.Placeholder() for _ in names)), parameters(record.values.values()))
        imported = select_row(conn,target,record)
        if imported is None or any(imported[k] != v for k,v in record.values.items()): raise SchemaError('Post-import row reconciliation failed')
    conn.execute('SET CONSTRAINTS ALL IMMEDIATE')


def execute(conn, manifest, apply=False, expected_plan=None):
    source_schema, target = manifest['source_schema'],manifest.get('target_schema','inventory')
    validate_schema(target)
    if source_schema == target: raise SchemaError('Source and target schemas must differ')
    if not manifest.get('source_id') or len(manifest['source_id']) > 100: raise SchemaError('source_id must be 1–100 characters')
    # RLS-filtered reads must never look like an empty successful migration.
    privileged = conn.execute('SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()[0]
    if not privileged: raise SchemaError('Use a migration administrator with BYPASSRLS; runtime roles cannot import')
    check_schema(conn, 'check', target)
    source = load_tables(conn, source_schema)
    if not source: raise SchemaError('Source schema has no tables')
    if apply:
        # Freeze source writes and canonical changes while reconciling the copy.
        names = sorted(source)
        conn.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.SQL(',').join(sql.SQL('{}.{}').format(sql.Identifier(source_schema),sql.Identifier(t)) for t in names)))
        conn.execute(sql.SQL('LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE').format(sql.SQL(',').join(sql.SQL('{}.{}').format(sql.Identifier(target),sql.Identifier(t)) for t in [*KEYS,'import_rows'])))
        source = load_tables(conn, source_schema)
    records, issues = convert(source, manifest)
    target_rows = load_tables(conn, target)
    expected_receipts = {(r.tenant,r.source_table,r.source_key,r.table) for r in records}
    for receipt in target_rows['import_rows']:
        if receipt['source_id'] == manifest['source_id'] and (receipt['tenant_id'],receipt['source_table'],receipt['source_key'],receipt['target_table']) not in expected_receipts:
            issues.append('Previously imported source record disappeared; explicit reconciliation required')
    plan_digest = digest({'manifest':manifest,'source':source,'target':target_rows})
    existing, inserting = 0, 0
    for record in records:
        row = select_row(conn, target, record)
        if row is None:
            inserting += 1
        elif any(row[k] != v for k,v in record.values.items()):
            issues.append(f'{record.table}: existing target differs; refusing overwrite')
        else:
            existing += 1
        receipt = conn.execute(sql.SQL('SELECT source_hash,target_hash,target_key FROM {}.import_rows WHERE tenant_id=%s AND source_id=%s AND source_table=%s AND source_key=%s AND target_table=%s').format(sql.Identifier(target)),
            (record.tenant,manifest['source_id'],record.source_table,record.source_key,record.table)).fetchone()
        if receipt and (receipt[0] != record.source_hash or row is None or receipt[1] != digest(row) or receipt[2] != record.key):
            issues.append(f'{record.table}: imported source or target changed since prior import')
    report = {'source_id':manifest['source_id'],'source_schema':source_schema,'target_schema':target,'plan_digest':plan_digest,
        'source_counts':{t:(r['excluded_count'] if t in EXCLUDED else len(r)) for t,r in source.items()},
        'excluded':{t:reason for t,reason in EXCLUDED.items() if t in source},
        'target_counts':dict(sorted(Counter(r.table for r in records).items())),
        'insert':inserting,'already_present':existing,'issues':sorted(set(issues)),'applied':False}
    if not apply:
        if not report['issues']:
            conn.execute('SAVEPOINT canonical_import_preview')
            try:
                insert_records(conn,target,records)
            except psycopg.Error as exc:
                report['issues'].append(f'Target constraint validation failed ({exc.sqlstate})')
            finally:
                conn.execute('ROLLBACK TO SAVEPOINT canonical_import_preview')
                conn.execute('RELEASE SAVEPOINT canonical_import_preview')
        return report
    if report['issues']: raise SchemaError('Import blocked: ' + '; '.join(report['issues']))
    if expected_plan != plan_digest: raise SchemaError('Plan digest changed or missing; generate and review a new dry-run plan')
    insert_records(conn,target,records)
    for record in records:
        imported = select_row(conn,target,record)
        conn.execute(sql.SQL('INSERT INTO {}.import_rows(tenant_id,source_id,source_table,source_key,target_table,target_key,source_hash,target_hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING').format(sql.Identifier(target)),
            (record.tenant,manifest['source_id'],record.source_table,record.source_key,record.table,Jsonb(record.key),record.source_hash,digest(imported)))
    if load_tables(conn,source_schema) != source: raise SchemaError('Source changed during import')
    report['applied'] = True
    report['reconciled_rows'] = len(records)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('plan','apply'))
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--expect-plan')
    parser.add_argument('--report',type=Path,required=True)
    args = parser.parse_args()
    dsn = os.getenv('CANONICAL_DATABASE_URL')
    if not dsn: parser.error('Set CANONICAL_DATABASE_URL')
    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        with psycopg.connect(dsn,connect_timeout=5) as conn:
            report = execute(conn,manifest,args.command == 'apply',args.expect_plan)
        # Success is reported only after commit. DB receipts remain authoritative
        # if the report filesystem fails after a successful database commit.
        args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2))
        return 1 if report['issues'] else 0
    except SchemaError as exc:
        print(str(exc),file=sys.stderr)
    except psycopg.Error as exc:
        print(f'PostgreSQL import failed ({exc.sqlstate or type(exc).__name__}); transaction rolled back',file=sys.stderr)
    except (OSError, ValueError, KeyError) as exc:
        print(f'Manifest/report operation failed ({type(exc).__name__}); inspect import_rows before retrying an apply',file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
