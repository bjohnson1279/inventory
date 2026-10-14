"""Reversible, row-scoped faults in explicitly enabled disposable databases only."""
import os
from contextlib import contextmanager
from urllib.parse import urlsplit
from scripts.conformance_runtime import HarnessError, BackendType


@contextmanager
def altered_ledger_payload(api, identifier):
    if os.getenv('CONFORMANCE_DB_FAULTS') != '1' or os.getenv('CONFORMANCE_SEED') != '1' or not api.tenant.startswith('conformance-'):
        raise HarnessError('Tamper scenario requires --stack conformance --seed, or explicit CONFORMANCE_DB_FAULTS=1 and a disposable database URL')
    url = os.getenv(f'CONFORMANCE_{api.backend.value.upper()}_DATABASE_URL', '')
    parsed = urlsplit(url)
    expected = {BackendType.GRAPHQL: 'inventory_gql', BackendType.EXPRESS_REST: 'inventory_express',
        BackendType.PHP_REST: 'inventory_php', BackendType.PYTHON_REST: 'inventory_python'}[api.backend]
    if parsed.scheme not in ('postgresql', 'postgres') or parsed.path != '/' + expected:
        raise HarnessError(f'Tamper scenario requires an explicit disposable {expected} PostgreSQL URL')
    import psycopg
    from psycopg import sql
    table, tenant_column = ('ComplianceLedgerModel', 'tenantId') if api.gql else ('compliance_ledgers', 'tenant_id')
    read = sql.SQL('SELECT payload FROM {} WHERE id = %s AND {} = %s').format(sql.Identifier(table), sql.Identifier(tenant_column))
    write = sql.SQL('UPDATE {} SET payload = %s WHERE id = %s AND {} = %s AND payload = %s').format(sql.Identifier(table), sql.Identifier(tenant_column))
    with psycopg.connect(url, autocommit=True, connect_timeout=5) as connection:
        original = connection.execute(read, (identifier, api.tenant)).fetchone()
        assert original is not None, 'Ledger entry must exist durably in this scenario tenant'
        corrupted = '{"conformance_tampered":true}'
        changed = connection.execute(write, (corrupted, identifier, api.tenant, original[0]))
        assert changed.rowcount == 1, 'Fault must change exactly one owned entry'
        try:
            yield
        finally:
            restored = connection.execute(write, (original[0], identifier, api.tenant, corrupted))
            assert restored.rowcount == 1, 'Failed to restore the single owned ledger entry'
