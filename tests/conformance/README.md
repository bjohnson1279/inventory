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

Set `CONFORMANCE_ADMIN_PASSWORD` to a test-only password of at least eight
characters. The default test email is `admin@conformance.example`; override it
with `CONFORMANCE_ADMIN_EMAIL` if needed. With `--seed`, each run creates a unique
tenant per backend, confirms setup success, then logs in with that account.
Existing-tenant runs omit `--seed` and require `CONFORMANCE_TENANT_ID`. Bootstrap
honors PHP's `/api/setup` route and snake-case login field, and GraphQL variables.

```powershell
python scripts/run_conformance.py --seed --suite smoke
python scripts/run_conformance.py --seed --suite full
```

Smoke runs three mandatory scenarios on all four backends: genuine healthy JSON,
authenticated access to the seeded administrator, and denial of unauthenticated
access. Its twelve passes prove basic harness/identity wiring, not inventory parity.

Full is the default and includes all declared scenarios. **Forty original
scenarios remain `pass`-only placeholders.** Collection identifies these and
execution reports them as explicit failures on every backend: 160 coverage-gap
results. Full conformance must remain nonzero until those business scenarios are
implemented and passing. Unsupported AI endpoints are also genuine failures;
they are not redirected into another backend or hidden behind offline skips.

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
migration scripts. Development setup and public Python bootstrap are enabled
only in this test-stack configuration; event delivery is disabled for these
HTTP conformance probes.

Use a fresh, dedicated Compose project/volume. Existing volumes created with the
old shared-database configuration do not receive initialization automatically.
Do not run test seeding or this configuration against a store database.

```powershell
docker compose --project-name inventory-conformance-check -f docker-compose.conformance.yml up --build --abort-on-container-exit --exit-code-from conformance-runner
```

This runs full conformance and currently exposes the unfinished scenarios.
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
including GraphQL's independent authentication path and 160 placeholder failures.
These servers are test doubles and do not certify the live applications' parity.

The final harness verification passed all 37 self-tests on 2026-10-14.
Python compilation, YAML parsing and Compose configuration validation passed.
A live four-backend inventory parity run has not been certified by these checks.

## Structure
- `scripts/conformance_runtime.py`: Explicit backend protocols and bootstrap
- `scripts/run_conformance.py`: Readiness, execution, manifest and report validation
- `conftest.py`: Real identity/client fixtures and result metadata
- `comparator.py`: Legacy normalization helpers; ordered picks, serial IDs and monetary invariants need scenario-specific assertions
- `canonical_types.yaml`: Canonical types schema
- `test_*.py`: Test modules covering different domain areas
