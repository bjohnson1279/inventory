#!/bin/sh
set -eu
# Fresh disposable Compose volumes only. Each backend owns its schema/database.
for database in inventory_gql inventory_express inventory_php inventory_python; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "CREATE DATABASE $database"
done
for schema_file in /conformance/php/*.sql; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname inventory_php -f "$schema_file"
done
