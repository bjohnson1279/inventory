# Database unification: confirmed remaining gaps

Source inspection and the running local PostgreSQL database, 2026-10-14. This is
a targeted assessment, not an exhaustive migration diff of every table.

The four backends do not currently implement one interchangeable physical schema.
Using the same PostgreSQL server/database in development has obscured differences
in table names, row ownership, field names, representations and constraints.

| Area | Confirmed divergence | Consequence |
| --- | --- | --- |
| Journals | PHP uses `journal_entries.method` and JSONB `lines`; Express expects `accounting_method` plus normalized `journal_lines` with `journal_entry_id`, account metadata and `debit_or_credit`. Python uses `python_journals` and `python_journal_lines`. | Express ledger returned HTTP 500 against the existing PHP-initialized database. |
| Inventory | GraphQL maps stock to `inventory_items`; Express to `inventories`; PHP uses `product_locations`; Python uses `python_stock`. | Switching backends does not read the same stock records. |
| Catalog | GraphQL/Express model parent products with variants; Python's `products` is a tenant-scoped SKU with price fields, supplemented by `python_catalog` and `python_variant_links`. | Identical table names can conceal incompatible meanings and required columns. |
| Events | All three ORM definitions use `outbox_events`, but GraphQL requires `event_type`, `created_at` and status; Express uses `event_name` and `occurred_on`; Python additionally requires aggregate fields, JSON payload, leased delivery, stream and sequence metadata. | A table created for one backend is not sufficient for the others; payload/storage and delivery semantics also differ. |
| Identity and ownership | Python has its own tenant/identity stores and tenant-scoped stock/catalog keys. The inspected TS inventory models identify rows by SKU/location without the same tenant key. | Unification requires agreement on ownership and uniqueness, not just renaming columns. |
| Types | GraphQL product/variant IDs use PostgreSQL UUIDs, while inspected PHP DDL and Python mappings use string identifiers. | Shared foreign keys and fixtures need a common identifier contract. |
| Deployment | Development Compose points the backends at the same database. SQL initialization runs only for fresh volumes; the conformance stack separately initializes each backend's database. | Existing volumes can lag application code. Separate test databases prove behavior per backend, not shared-storage compatibility. |
| Drift detection | `scripts/lint_schema_drift.py` compares JS/PHP OpenAPI path names and loosely counts GraphQL/client coverage. It does not inspect PostgreSQL, SQL migrations, Prisma mappings or SQLAlchemy models. | Its success message cannot certify database unification or Python database compatibility. |

## Ledger incident and repair

The actual local `inventory_db` had `journal_entries.method`, JSONB `lines`, and
legacy `journal_lines.entry_id`/`type`, with none of the corresponding Express
columns. Logs showed Prisma P2022 for `journal_entries.accounting_method` and P2021
for the separate `barcode_assignments` table. There were zero journal headers.

`21_shared_ledger_compat.sql` adds the missing journal columns and synchronizes the
legacy JSON and normalized rows. It preserves accounting methods, integer cents,
header IDs and existing normalized IDs, and can be rerun. Six PostgreSQL tests
exercise empty/historical databases, PHP/Express writes, updates and repeatability
inside temporary schemas rolled back after each test. The repair was applied to
the local database and the authenticated Express ledger returned HTTP 200.

This localized compatibility repair does not unify the other tables, add the
missing barcode table, or move Python journals into the common ledger.

## Implementation order

1. Establish a versioned canonical physical schema: table purposes, tenant keys,
   identifiers, money, JSON representation and event delivery states. Preserve the
   stronger Python isolation, exact-cents and delivery guarantees.
2. Provide reviewed upgrade migrations for existing volumes as well as clean
   initialization. Include data conversion, reconciliation counts and rollback
   procedures. Do not use destructive `prisma db push` against a shared store.
3. Align each ORM/repository with that schema in vertical slices: identity/catalog,
   stock/lots, costing/journals, events, then the remaining retail features.
4. Replace the current schema-drift claim with actual database checks for all four
   backends: columns, types, nullability, foreign keys, tenant keys and indexes.
5. Add shared-storage integration tests: initialize once, write through backend A,
   read/change through B/C/D, then verify stock, accounting, tenant boundaries and
   outbox facts. Keep isolated behavioral conformance as a separate check.

Primary evidence: `docker-compose.yml`, both `prisma/schema.prisma` files, PHP's
`docker/postgres/init/01_init.sql` and `20_conformance_parity.sql`, Python's
`catalog_models.py`, `stock_models.py`, `financial_models.py`, messaging models,
and `scripts/lint_schema_drift.py`.
