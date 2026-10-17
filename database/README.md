# Canonical database contract

The parent repository owns the canonical PostgreSQL DDL in `migrations/`.
The latest contract is **0003**. The SQL files are the physical source of truth;
backend ORM models must eventually map to these tables and columns explicitly.

It creates the dedicated **`inventory`** schema alongside the existing `public`
tables. The importer below copies supported existing data without switching
backend repositories or establishing shared-storage parity yet.
Legacy tables with the same names have incompatible meanings; automatic adoption
or merging would risk associating stock and money with the wrong tenant.

## Contract decisions

| Concern | Canonical rule |
| --- | --- |
| Platform | PostgreSQL 16; plain PostgreSQL features, no Timescale extension required. SQLite remains a backend unit-test store, not proof of this physical contract. |
| Names | Snake_case, explicitly qualified by the `inventory` namespace in ORM mappings. No backend prefixes. |
| IDs | `varchar(100)` consistently for identifiers and references; accepts existing string IDs and UUID strings. No implicit UUID casting. IDs are supplied by the caller. |
| Ownership | Tenant ID is part of every owned primary/foreign key. Reused IDs, emails, SKUs and barcodes across tenants are valid. Cross-tenant references are invalid. |
| Authorization | All domain tables have forced RLS. Set `inventory.tenant_id` locally in every request/worker transaction. Missing/empty context sees no rows. Runtime roles must have neither superuser nor BYPASSRLS privileges. Tenant authentication must precede setting context. Version 0003 adds tenant-owned roles, permissions and memberships to preserve full RBAC. `users.role` is a compatibility projection; MULTIPLE/NONE never substitute for checking memberships. |
| Catalog | `products` are parents; `variants` are sellable SKUs, including a product with one SKU. Price/currency belong to the variant. Barcodes identify variants. |
| Quantity | `numeric(20,6)` in base units. Nonnegative balances; allocation cannot exceed on-hand stock. Version enables repository compare-and-swap. Mutation IDs are tenant-unique. Updating balances and inserting movements must share a transaction. |
| Money | Integer minor units (`*_cents`), bounded to JavaScript's exact integer range. One three-letter uppercase currency per journal; zero-decimal/multi-decimal currency conversion remains a future contract extension. |
| Accounting | Accounting method is CASH/ACCRUAL, independent of inventory costing strategy. Assemble DRAFT journals and lines, then POST. Posted journals must have 2–100 lines, equal nonzero debit/credit totals within the exact integer range. Headers and lines are immutable after posting; corrections use a reversal. Source and reversal IDs are tenant-unique. |
| Events | JSONB objects, never JSON encoded inside strings. Tenant/stream sequence is unique. PENDING, RETRY, INFLIGHT, PUBLISHED, DEAD_LETTER states retain lease, retry-cycle, optimistic version and publication metadata. INFLIGHT requires a token/expiry; PUBLISHED requires a timestamp. |
| Time | `timestamptz` for instants; `date` for accounting dates. Display timezone is a client concern. |

These storage rules complement domain logic. Stock movement reconciliation,
optimistic-update row counts, journal numbering/period closing, outbox sequence
allocation, ordering, lease expiry/fencing and retries still require transactional
repository implementations. The initial contract does not replace those existing
Python safeguards. Accounting periods/documents, cost layers, lots, serials,
kits, procurement, transfers and other feature stores will get subsequent
migrations before their repositories are adopted.

## Install, inspect, upgrade

Install the runner dependency, then explicitly select the target database. This
uses the existing PostgreSQL service; it works for fresh and existing volumes.
It does not depend on `/docker-entrypoint-initdb.d` running again.

```powershell
python -m pip install -r database/requirements.txt
$env:CANONICAL_DATABASE_URL = 'postgresql://USER:PASSWORD@localhost:5432/inventory_db'
python scripts/canonical_schema.py status
python scripts/canonical_schema.py apply
python scripts/canonical_schema.py check
```

`status` validates migration history and lists pending versions without creating
objects. It does not certify physical drift. `apply` checks the installed version,
applies pending files and verifies the resulting physical schema in one atomic
transaction. A repeat apply preserves rows and adds no history entries. `check`
fails on pending versions or drift. Errors return a nonzero exit code. The runner
does not print connection strings or row contents on database errors.

`check` and `apply` build a reference schema inside a savepoint and roll it back.
They compare tables, column types/defaults/nullability, PK/FK/unique/check
constraints, indexes, RLS flags/policies, trigger definitions/enabled state and
function definitions against the applied SQL. This requires a migration role
with schema creation privileges, even for `check`. Grants, ownership, external
schemas, backend ORM mappings and business data are outside this drift check.
Do not run it with an application's limited runtime role.

Migration history includes SHA-256 checksums (normalized LF line endings), names
and versions. Missing/unknown/reordered/edited applied migrations fail closed.
A transaction-scoped advisory lock prevents concurrent runners for a database
and namespace. Unversioned namespaces are rejected, as are `public` and system
namespaces. `--schema` is available for isolated environments; every backend
in an environment must target the same agreed namespace.

## Migration authoring and recovery

1. Never edit an applied migration. Add the next contiguous `0004_name.sql` file.
   Keep identifiers unqualified so the runner can install/check isolated schemas.
   Do not reference or mutate `public`/legacy tables in foundation DDL.
2. Keep changes transactional: no `CONCURRENTLY`, explicit transaction control,
   external side effects, or destructive resets. Use additive changes and reviewed
   backfills. The runner owns the transaction and the registry.
3. Test clean installation, previous-version upgrade with rows, constraints,
   drift, repeat apply and failure rollback. CI runs real PostgreSQL tests.
4. Take a database backup before deployment. Failed migrations roll back the
   whole batch, including registry writes. Fix a never-applied migration or add a
   new reviewed migration for an already deployed version. There is no automatic
   down/reset command. Once canonical writes begin, recovery requires a forward
   repair or restoring the backup; dropping the schema would lose those writes.

## Backend adoption sequence

| Slice | Existing sources | Required migration work before cutover |
| --- | --- | --- |
| Identity/catalog | Python identity/catalog/variant links; TS/PHP products and variants | Explicit tenant mapping, duplicate detection, parent/SKU conversion, ID crosswalk, decimal-price-to-cents validation. Preserve hashes and authorization semantics. |
| Stock | `inventory_items`, `inventories`, `product_locations`, `python_stock` | Resolve tenant and variant/location ownership. Reconcile on-hand/allocated/in-transit and movement history; never sum competing backend snapshots blindly. |
| Journals | Shared PHP/Express journals, Python financial stores | Preserve source/reversal lineage, currency/method/period rules and normalized cents; reconcile journal counts and debit/credit totals before enabling writes. |
| Events | Incompatible `outbox_events` definitions | Preserve delivery state/lease lineage, quarantine unknown ownership, normalize payloads, reconcile streams/sequences and avoid republishing delivered events. |

Each slice needs a dry-run importer/report, approved ownership mappings,
reconciliation totals, repository/ORM changes in all four backends, and tests
that write through one backend and read through the others. Do not point an
existing ORM at `inventory` merely by changing its search path. Existing startup
DDL/`prisma db push` must not own canonical tables. Existing conformance tests
against separate backend databases remain a separate behavioral check.

## Import existing shared data

`scripts/import_canonical_data.py` currently imports the **shared PHP/TS layout**
in the same PostgreSQL database: tenants, roles, permission definitions and
assignments, users/memberships, locations, products/variants, barcodes and stock
balances. It supports the inspected local layout, including string/UUID IDs,
PHP permission strings and TS permission IDs. It is not an importer for Python's
separate catalog, accounting history, or asynchronous delivery history yet.
Any populated unsupported table blocks the **entire** import. Empty tables are
counted and reported, not fabricated as imported data.

The local ownership manifest is `database/imports/local-shared.json`. It assigns
the two existing global location records to the only persisted business tenant,
`tenant-1`. The routing registry's seeded `system`/`test-tenant` entries are
connection metadata, not authoritative tenant records; credentials are neither
imported nor included in reports. Legacy migration histories are excluded too.
The currency in the manifest is an explicit fallback for legacy prices; there
are no product/price rows in the inspected local store.

Before applying to any other environment, review its tenant and location
ownership and supply its own manifest. Do not reuse local mappings blindly.
Global roles and permissions are copied into each actual tenant. Password hashes
are preserved byte-for-byte; normalized email collisions abort. Inactive users
and multiple/no roles retain those semantics. Source metadata retains unmapped
business fields (including the original email); hashes are stored only in the
canonical credential column. IDs are preserved and `import_rows` stores the
source/target crosswalk and checksums under tenant RLS.

No target rows are overwritten. A price must be supplied by source data; missing
prices, fractional cents, ambiguous SKUs, conflicting stock snapshots and nonzero
PHP open-box/damaged quantities block import pending a reviewed conversion.
Quantities are never summed across backends. A dry run stages records in a
savepoint to validate actual constraints and then rolls them back.

```powershell
# Take a private PostgreSQL backup first, then upgrade the canonical contract.
python scripts/canonical_schema.py apply
python scripts/import_canonical_data.py plan --manifest database/imports/local-shared.json --report .pytest_cache/canonical-import-plan.json
$canonicalPlan = Get-Content .pytest_cache/canonical-import-plan.json -Raw | ConvertFrom-Json
python scripts/import_canonical_data.py apply --manifest database/imports/local-shared.json --expect-plan $canonicalPlan.plan_digest --report .pytest_cache/canonical-import-result.json
python scripts/canonical_schema.py check
```

Run imports with a dedicated migration administrator with BYPASSRLS/superuser;
otherwise RLS could conceal source/target records. Reports contain counts, issue
categories and digests, not users, passwords or credential hashes. Apply takes
source SHARE locks and target SHARE ROW EXCLUSIVE locks, subject to the runner's
five-second lock timeout, and commits the complete copy atomically. Pause source
writes during import to avoid lock contention. Apply rechecks the reviewed plan
digest under locks; any intervening source, target or manifest change aborts.

Post-import reconciliation compares every mapped field and fingerprints complete
target rows. Repeated plan/apply is insert-only and idempotent while records stay
unchanged. Changing either imported source rows or canonical rows blocks another
import rather than overwriting newer data. A successful report is written after
commit; if report writing fails, consult database `import_rows` receipts and run
a new plan. The copy is a snapshot, **not live synchronization**. Reconcile again
and implement a controlled final delta before repository cutover if legacy
writes resume. Do not enable both sets of repositories as independent writers.

## Verification

Tests use unique schemas and transaction rollback, including test roles; no
store rows or committed schemas are changed. Use a PostgreSQL test administrator
because the RLS test creates a temporary role and transfers table ownership.

```powershell
$env:CANONICAL_SCHEMA_TEST_DATABASE_URL = 'postgresql://USER:PASSWORD@localhost:5432/TEST_DATABASE'
python -m pytest tests/harness/test_canonical_schema.py tests/harness/test_canonical_import.py -q
```

Without that variable PostgreSQL tests explicitly skip. The dedicated
`canonical-schema.yml` workflow supplies PostgreSQL 16 and always runs them.
