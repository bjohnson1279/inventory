"""Inspect or apply the additive shared-development ledger compatibility migration."""
import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit
import psycopg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database-url', default=os.getenv('LOCAL_LEDGER_DATABASE_URL'))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.database_url or urlsplit(args.database_url).hostname not in ('localhost', '127.0.0.1', '::1'):
        parser.error('Supply a local PostgreSQL URL using --database-url or LOCAL_LEDGER_DATABASE_URL')
    migration = Path(__file__).resolve().parents[1]/'php-ddd-inventory/docker/postgres/init/21_shared_ledger_compat.sql'
    with psycopg.connect(args.database_url, connect_timeout=5) as connection:
        connection.execute("SET LOCAL lock_timeout='5s'")
        connection.execute("SET LOCAL statement_timeout='30s'")
        count = connection.execute('SELECT count(*) FROM journal_entries').fetchone()[0]
        columns = {row[0] for row in connection.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='journal_entries'")}
        print(f'Journal headers: {count}; accounting_method present: {"accounting_method" in columns}')
        if not args.apply:
            print('Inspection only. Use --apply to run the tested compatibility migration.')
            return
        connection.execute(migration.read_text(encoding='utf-8'))
        assert connection.execute('SELECT count(*) FROM journal_entries').fetchone()[0] == count
        connection.execute('SELECT accounting_method FROM journal_entries LIMIT 1')
        connection.execute('SELECT journal_entry_id,account_name,account_category,debit_or_credit FROM journal_lines LIMIT 1')
    print('Ledger compatibility migration committed; existing journal headers preserved.')


if __name__ == '__main__':
    main()
