# Conformance Test Suite

The harness runs GraphQL TypeScript, REST TypeScript, PHP REST and Python REST.
It fails on unavailable/unhealthy backends, setup/login errors, missing tokens,
collection failures, skips/xfails, incomplete reports or missing backend results.
It does not substitute dummy credentials or guess backend attribution from IDs.

## Setup
Run from the repository root. Install the harness dependencies:

```powershell
python -m pip install -r tests/conformance/requirements.txt
```

Set `GRAPHQL_URL`, `EXPRESS_REST_URL`, `PHP_REST_URL` and `PYTHON_REST_URL` for
your disposable backend instances. Defaults are localhost ports 4000, 5000,
8000 and 8001. `GRAPHQL_URL` must name the GraphQL endpoint; health probes use
its origin's `/health`, rather than treating any successful root page as health.
GraphQL base URLs without a path are normalized to `/graphql`; an explicitly
configured endpoint path is preserved. A health response identifying another
application is rejected, even if it says `healthy`.

Set `CONFORMANCE_ADMIN_PASSWORD` to a test-only password of at least eight
characters. The default test email is `admin@conformance.example`; override it
with `CONFORMANCE_ADMIN_EMAIL` if needed. With `--seed`, each run creates a unique
tenant per backend, confirms setup success, then logs in with that account.
Existing-tenant runs omit `--seed` and require `CONFORMANCE_TENANT_ID`. Bootstrap
honors PHP's `/api/setup` route and snake-case login field, and GraphQL variables.

```powershell
$env:CONFORMANCE_ADMIN_PASSWORD = 'conformance-test-password'
python scripts/run_conformance.py --seed --suite smoke
python scripts/run_conformance.py --seed --suite full
```

Run these in the same PowerShell session. `--seed` replaces the existing-tenant
ID requirement, not the password requirement. Missing/short passwords now fail
once during runner preflight, before network polling or pytest fixture setup.

Smoke runs three mandatory scenarios on all four backends: genuine healthy JSON,
authenticated access to the seeded administrator, and denial of unauthenticated
access. Its twelve passes prove basic harness/identity wiring, not inventory parity.

Full is the default and includes 47 scenarios per backend: 40 business workflows,
four AI checks and three smoke probes, for 188 attributed results. All forty
original placeholders now execute assertions. New empty scenarios are still
rejected during collection/execution. Missing capabilities, API errors and
behavioral disagreements remain failures; implementing tests does not certify
that the backends pass them. Unsupported AI endpoints are also genuine failures.

Business workflows require `--seed` and create a fresh tenant per scenario.
This isolates costing configuration, counts, returns and empty-tenant AI probes.
Assertions preserve serial/reference identities, FEFO/route order, integer cents,
and stock/version invariants; they do not use the permissive legacy comparator.
TLS verification stays enabled, with a shared trust context to avoid repeatedly
loading the Windows certificate store for hundreds of clients.

Tamper detection temporarily changes one owned compliance-ledger payload and
restores it in `finally`, then verifies that the backend accepts the restored
chain. `--stack conformance` supplies the four disposable database URLs and enables
this fault. Configured stacks must explicitly set `CONFORMANCE_DB_FAULTS=1` and
`CONFORMANCE_{GQL,EXPRESS,PHP,PYTHON}_DATABASE_URL` as applicable. Database names must
match `inventory_gql`, `inventory_express`, `inventory_php` or `inventory_python`.
The PostgreSQL driver is included in the harness requirements. No tamper scenario
is silently skipped when this configuration or a ledger API is missing.

The runner validates the full scenario manifest on each backend. Filtering down
to smoke with `PYTEST_ADDOPTS` cannot produce a successful full conformance result.
Results carry backend, scenario and coverage-gap metadata. Stale report files are
removed before execution, and positive pytest failure exit codes are preserved.
`--skip-health-check` disables only readiness polling; the mandatory probes and
bootstrap health validation still run. JSON is written under `conformance-report`
by default; `--report-dir` selects a different directory.

## Disposable Compose stack

The Compose stack creates a separate database for each backend, applies PHP
initialization only to its database, initializes the two Prisma schemas and runs
Python's explicit migration before starting its API. The Python image includes
migration scripts. PostgreSQL readiness checks its TCP listener, so API startup
waits for initialization to finish. Express's runtime includes OpenSSL for Prisma
and receives a test-only encryption key. PHP builds its code and Composer
dependencies into the image; this stack does not mount host `vendor` files.
Development setup and public Python bootstrap are enabled
only in this test-stack configuration; event delivery is disabled for these
HTTP conformance probes.

Use a fresh, dedicated Compose project/volume. Existing volumes created with the
old shared-database configuration do not receive initialization automatically.
Do not run test seeding or this configuration against a store database.

```powershell
docker compose --project-name inventory-conformance-check --env-file tests/conformance/compose.env -f docker-compose.conformance.yml up --build --abort-on-container-exit --exit-code-from conformance-runner
```

For a host smoke run, first build/start only the six test services, then use the
conformance profile. It targets GraphQL 5040 (`/graphql`), Express 5050, PHP 5080
and Python 5081, leaving development ports 4000/5000/8000/8001 alone:

```powershell
docker compose --project-name inventory-conformance-check --env-file tests/conformance/compose.env -f docker-compose.conformance.yml up -d --build postgres redis gql-backend express-backend php-backend python-backend
$env:CONFORMANCE_ADMIN_PASSWORD = 'conformance-test-password'
python scripts/run_conformance.py --seed --suite smoke --stack conformance
```

The explicit `compose.env` prevents the development `.env` from redirecting test
port bindings onto existing services. `--stack conformance` also supplies the same
test URLs to readiness polling and pytest. Backend endpoints are printed before
execution. Older running Python images without `/api/auth/setup` must be rebuilt;
a successful health probe alone cannot establish that their routes are current.

The containerized runner runs full conformance and currently exposes the unfinished scenarios.
CI uses a per-run project name, uploads the report even after failure, and cleans
up only that project's disposable volumes. The runtime in this stack is not a
restricted-role PostgreSQL RLS certification; backend-specific database contracts
cover that separately.

## Harness verification

```powershell
python -m pytest tests/harness -q --tb=short
```

Self-tests exercise strict health/setup/authentication checks, report completeness,
skip/error handling, stale-report removal and subprocess exit codes. Local protocol
test servers exercise the actual pytest fixtures and runner for all four transports,
including GraphQL's independent authentication path and rejection of business runs
against servers that implement only smoke. Stateful assertion tests deliberately
introduce wrong balances and single-cent errors. GraphQL adapter requests are
checked against the checked-in SDL, including input and enum validation.
These servers are test doubles and do not certify the live applications' parity.

Current validation evidence and remaining failures are recorded in
`docs/conformance-scenario-status-2026-10-14.md`. A live four-backend inventory
parity run has not been certified by harness self-tests or isolated Python checks.
The separate databases used here establish behavior per backend; shared physical
schema compatibility requires additional cross-backend read/write tests.

## Structure
- `scripts/conformance_runtime.py`: Explicit backend protocols and bootstrap
- `scripts/run_conformance.py`: Readiness, execution, manifest and report validation
- `conftest.py`: Real identity/client fixtures and result metadata
- `comparator.py`: Legacy normalization helpers; ordered picks, serial IDs and monetary invariants need scenario-specific assertions
- `canonical_types.yaml`: Canonical types schema
- `test_*.py`: Test modules covering different domain areas
