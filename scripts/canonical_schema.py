"""Apply and verify the parent-owned canonical PostgreSQL schema.

The legacy public schema is deliberately never adopted or modified. SQL files
under database/migrations are immutable once recorded in schema_migrations.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

import psycopg
from psycopg import sql

MIGRATIONS = Path(__file__).resolve().parents[1] / 'database' / 'migrations'
REGISTRY = '''CREATE TABLE IF NOT EXISTS schema_migrations (
    version varchar(4) PRIMARY KEY,
    name text NOT NULL,
    checksum varchar(64) NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
)'''


class SchemaError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    checksum: str
    source: str


def migrations(directory: Path = MIGRATIONS) -> list[Migration]:
    result = []
    for path in sorted(directory.glob('*.sql')):
        match = re.fullmatch(r'(\d{4})_([a-z0-9_]+)\.sql', path.name)
        if not match or int(match[1]) != len(result) + 1:
            raise SchemaError(f'Migration names must be contiguous from 0001: {path.name}')
        # Normalize checkout line endings so Windows and Linux share checksums.
        source = path.read_text(encoding='utf-8').replace('\r\n', '\n')
        result.append(Migration(match[1], match[2], hashlib.sha256(source.encode()).hexdigest(), source))
    if not result:
        raise SchemaError('No canonical migrations found')
    return result


def validate_schema(schema: str) -> None:
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', schema) or schema in ('public', 'information_schema') or schema.startswith('pg_'):
        raise SchemaError('Use a dedicated lowercase schema; public and PostgreSQL system schemas are forbidden')


def select_schema(conn, schema: str) -> None:
    conn.execute(sql.SQL('SET LOCAL search_path TO {}, pg_catalog').format(sql.Identifier(schema)))


def history(conn, schema: str, available: list[Migration]) -> list[Migration]:
    exists = conn.execute('SELECT to_regnamespace(%s)', (schema,)).fetchone()[0]
    if exists is None:
        return []
    registered = conn.execute('SELECT to_regclass(%s)', (f'{schema}.schema_migrations',)).fetchone()[0]
    if registered is None:
        raise SchemaError('Existing schema has no migration registry; refusing to adopt it')
    rows = conn.execute(sql.SQL('SELECT version, name, checksum FROM {}.schema_migrations ORDER BY version').format(sql.Identifier(schema))).fetchall()
    expected = [(m.version, m.name, m.checksum) for m in available[:len(rows)]]
    if rows != expected:
        raise SchemaError('Migration history differs from committed files (unknown, missing, renamed or changed migration)')
    return available[:len(rows)]


def snapshot(conn, schema: str) -> dict:
    """Compare physical definitions, independent of generated OIDs/schema names."""
    queries = {
        'columns': '''SELECT c.relname,a.attname,pg_catalog.format_type(a.atttypid,a.atttypmod),a.attnotnull,
            pg_get_expr(d.adbin,d.adrelid),a.attidentity,a.attgenerated
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
            LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
            WHERE n.nspname=%s AND c.relkind IN ('r','p') ORDER BY 1,2''',
        'tables': '''SELECT c.relname,c.relkind,c.relrowsecurity,c.relforcerowsecurity
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=%s AND c.relkind IN ('r','p','v','m','S') ORDER BY 1''',
        'constraints': '''SELECT c.relname,k.conname,k.contype,pg_get_constraintdef(k.oid),k.convalidated
            FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=%s ORDER BY 1,2''',
        'indexes': '''SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname=%s ORDER BY 1,2''',
        'policies': '''SELECT tablename,policyname,permissive,roles::text,cmd,qual,with_check
            FROM pg_policies WHERE schemaname=%s ORDER BY 1,2''',
        'triggers': '''SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid),t.tgenabled
            FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=%s AND NOT t.tgisinternal ORDER BY 1,2''',
        'functions': '''SELECT p.proname,pg_get_function_identity_arguments(p.oid),pg_get_functiondef(p.oid)
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=%s ORDER BY 1,2''',
    }
    # Empty search_path makes catalog output consistently qualify relations.
    conn.execute('SET LOCAL search_path TO pg_catalog')
    result = {}
    for name, query in queries.items():
        rows = conn.execute(query, (schema,)).fetchall()
        result[name] = [tuple(normalize_schema(value, schema) if isinstance(value, str) else value for value in row) for row in rows]
    return result


def normalize_schema(definition: str, schema: str) -> str:
    # Schema qualification is an identifier, not text inside SQL literals such
    # as 'inventory.tenant_id'. Preserve those when comparing different schemas.
    pieces = re.split(r"('(?:''|[^'])*')", definition)
    pattern = r'(?<![a-zA-Z0-9_])(?:' + re.escape(schema) + r'|"' + re.escape(schema) + r'")\.'
    for index in range(0, len(pieces), 2):
        pieces[index] = re.sub(pattern, '@schema.', pieces[index])
    return ''.join(pieces)


def verify(conn, schema: str, applied: list[Migration]) -> None:
    actual = snapshot(conn, schema)
    reference = 'canonical_check_' + uuid.uuid4().hex
    # Nested transaction/savepoint: all reference DDL is rolled back, even on success.
    conn.execute('SAVEPOINT canonical_reference')
    try:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(reference)))
        select_schema(conn, reference)
        conn.execute(REGISTRY)
        for migration in applied:
            conn.execute(migration.source)
        expected = snapshot(conn, reference)
    finally:
        conn.execute('ROLLBACK TO SAVEPOINT canonical_reference')
        conn.execute('RELEASE SAVEPOINT canonical_reference')
    differences = [name for name in expected if actual[name] != expected[name]]
    if differences:
        raise SchemaError('Physical schema drift in: ' + ', '.join(differences))


def run(conn, command: str, schema: str = 'inventory', directory: Path = MIGRATIONS) -> dict:
    """Caller owns transaction; any exception must roll it back before reuse."""
    validate_schema(schema)
    if command not in ('status', 'check', 'apply'):
        raise SchemaError('Unknown canonical schema command')
    available = migrations(directory)
    conn.execute("SET LOCAL lock_timeout = '5s'")
    conn.execute("SET LOCAL statement_timeout = '30s'")
    locked = conn.execute('SELECT pg_try_advisory_xact_lock(hashtextextended(current_database() || %s, 0))', (':canonical:' + schema,)).fetchone()[0]
    if not locked:
        raise SchemaError('Another canonical migration/check is running')
    applied = history(conn, schema, available)
    exists = conn.execute('SELECT to_regnamespace(%s)', (schema,)).fetchone()[0] is not None
    if exists and command != 'status':
        verify(conn, schema, applied)
    pending = available[len(applied):]
    if command == 'check' and (not exists or pending):
        raise SchemaError('Canonical schema has pending migrations; run apply')
    if command == 'apply':
        if not exists:
            conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
            select_schema(conn, schema)
            conn.execute(REGISTRY)
        for migration in pending:
            select_schema(conn, schema)
            conn.execute(migration.source)
            conn.execute('INSERT INTO schema_migrations(version,name,checksum) VALUES (%s,%s,%s)', (migration.version, migration.name, migration.checksum))
        verify(conn, schema, available)
    return {'schema': schema, 'applied': [m.version for m in (available if command == 'apply' else applied)],
            'pending': [] if command == 'apply' else [m.version for m in pending],
            'physical_check': command != 'status'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('status', 'check', 'apply'))
    parser.add_argument('--schema', default='inventory')
    args = parser.parse_args()
    dsn = os.getenv('CANONICAL_DATABASE_URL')
    if not dsn:
        parser.error('Set CANONICAL_DATABASE_URL to the intended PostgreSQL database')
    try:
        with psycopg.connect(dsn, connect_timeout=5) as conn:
            result = run(conn, args.command, args.schema)
        print(json.dumps(result, indent=2))
        return 0
    except SchemaError as exc:
        print(str(exc), file=sys.stderr)
    except psycopg.Error as exc:
        # Database errors can contain row data/credentials. Report only the code.
        print(f'PostgreSQL operation failed ({exc.sqlstate or type(exc).__name__}); transaction rolled back', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
