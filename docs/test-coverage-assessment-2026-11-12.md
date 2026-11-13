# Test coverage assessment — November 12, 2026

## Assessment

Test breadth is substantial, but there is no reproducible, enforced coverage baseline across the applications. Test-file counts describe the investment in tests; they do not measure executed lines, branches, or production confidence.

This assessment uses the current local working trees, including pre-existing uncommitted changes. It reviews checked-in configuration and workflows and records local execution separately from historical evidence. It does not certify current remote CI status.

## Inventory

Counts include conventional test files in `tests`, `src`, and `app`; source counts exclude tests and Python package initializers. These are file counts, not test-case counts or coverage percentages.

| Application | Source files | Test files | Distribution |
| --- | ---: | ---: | --- |
| GraphQL TypeScript | 333 | 186 | 99 domain, 47 application, 37 infrastructure, 3 other |
| REST TypeScript | 375 | 196 | 89 domain, 43 application, 63 infrastructure, 1 other |
| PHP REST | 392 | 169 | 137 unit, 32 integration |
| Python REST | 142 | 113 | 41 domain, 18 application, 26 infrastructure, 27 presentation, 1 other |
| React client | 44 | 74 | 70 unit/colocated, 4 Playwright specifications |
| Python sidecar | 9 | 6 | API, optimization, boundary validation |
| **Total** | **1,295** | **744** | |

The parent repository also has four harness test modules, thirteen conformance test modules, and one shared-ledger database test module. The conformance manifest documents 47 scenarios on each of four backends (188 attributed results).

## Findings, in priority order

### 1. Coverage is not a CI gate

None of the reviewed application or parent test workflows requests coverage or enforces minimum coverage. Python requirements do not include pytest-cov, and the active local interpreter has neither pytest-cov nor coverage.py. PHP defines a source coverage filter, but the local runtime has no enabled Xdebug/PCOV coverage driver.

Express defines `collectCoverageFrom` for source files; GraphQL has no explicit all-source denominator. React has the V8 coverage package but no coverage configuration or threshold. Its measured report contains 41 files and omits the application bootstrap, `src/main.tsx` (and the type-only `src/api/types.ts`). Consequently, imported-file reports can omit unimported source files, and passing CI cannot establish a minimum line or branch coverage level.

Evidence: application Jest/Vitest/PHPUnit configuration, package manifests, Python requirements, and the seven reviewed test workflows under `.github/workflows` and each application’s `.github/workflows`.

Action: collect line and branch coverage for all runtime source, publish machine-readable artifacts, record exclusions explicitly, then establish per-application baselines. Gate changes against those baselines before selecting higher long-term targets.

### 2. Browser coverage does not establish live application integration

There are fourteen Playwright tests across four specifications. The dashboard, administration, and RFID suites intercept backend traffic with `page.route` and inject mock tokens. These test browser behavior and client/server assumptions, but do not prove that real authentication, API payloads, and persistence work together.

Evidence: `react-ddd-inventory-client/tests/e2e/{dashboard,admin,rfid,auth}.spec.ts` and `playwright.config.ts`. The CI web server launches Vite; it does not provision live backends for these tests.

Action: retain mocked browser tests and add a small live-backend browser suite covering setup/login, product creation, stock receipt, allocation/dispatch, and persisted results. Include backend switching and tenant separation where practical.

### 3. Database-labelled tests need classification by what they actually exercise

For example, Express `PrismaInventoryRepository.test.ts` mocks Prisma with a Map, and GraphQL `PostgresInventoryCostLayerRepository.test.ts` supplies mocked Prisma methods and `$executeRaw`. These are useful unit tests, but cannot validate SQL syntax, migrations, PostgreSQL constraints, transaction isolation, or RLS.

Python has substantive dedicated PostgreSQL and Kafka contracts, including concurrent writes and a restricted-role tenant-isolation check. Those tests skip without explicitly configured services; the Python workflow supplies separate PostgreSQL and Kafka jobs. A normal SQLite unit run must therefore be reported separately from those contracts.

Action: label mocked repository tests as unit tests, report real database/broker suites separately, and require those jobs for changes to storage, tenant isolation, and event delivery.

### 4. Full conformance success remains unverified

The harness rejects missing results, skips, placeholders, and backend errors. Its assertion tests inject bad stock balances and single-cent errors, which is stronger evidence than status-code checks alone. However, harness self-tests use protocol doubles and cannot certify backend parity.

The checked-in October 14 status report records 24 passing and 23 failing Python HTTP scenarios, with the other 141 backend combinations deselected. This is historical evidence, not a fresh result. It explicitly does not certify a passing four-backend run. Current parent CI is configured to run full disposable-stack conformance and upload its report.

Action: obtain and retain a fresh 188-result conformance report before claiming parity. Prioritize failures by inventory, accounting, tenant-security, and durability impact; do not turn unsupported capabilities into passing skips.

### 5. Shared-ledger compatibility tests are outside the reviewed CI commands

`tests/database/test_shared_ledger_compat.py` contains six PostgreSQL compatibility tests. The parent harness job runs `tests/harness`; the canonical-schema workflow explicitly runs two canonical harness modules. Neither command selects this database module, and no reference to it was found in the parent workflows.

Action: add a disposable PostgreSQL CI job for this module and include migration paths in its triggers. Keep this certification distinct from conformance against separate backend databases.

### 6. Client storage mocks reduce behavioral fidelity

`tests/unit/setup.ts` assigns the same object to both localStorage and sessionStorage. Real browsers keep those stores separate. Tests using this setup cannot reliably catch accidental substitution of one storage mechanism for the other.

Action: instantiate separate storage mocks and reset their state between tests; verify auth-token and backend-selection persistence semantics in browser tests.

## Local execution evidence

Logs and generated coverage artifacts are stored under `.pytest_cache/coverage-audit*` to avoid changing application configuration.

- PHP unit suite: **718 passed, 1,956 assertions**, using CLI-only mbstring, SQLite, and cURL extension flags. An earlier attempt had two missing-cURL errors; enabling the installed extension resolved those errors, and the complete suite then passed. PHP integration tests were not part of this command. No PHP coverage percentage was produced.
- Sidecar: **61 passed**, 20 deprecation warnings. No Python coverage percentage was produced.
- Parent harness: **106 passed, 50 skipped**. Canonical PostgreSQL schema/import tests skip without their dedicated database URL; this result does not certify those migrations.
- Client: **70 files, 618 tests passed**. Reported coverage is **66.64% lines, 54.87% branches, 60.34% functions** across 41 measured files; the bootstrap is not measured. This is the complete Vitest suite, not the Playwright suite. Local elapsed time was 763.89 seconds, with 418.68 seconds attributed to test environment setup and 80.19 seconds to tests; this concurrent local audit is not a CI performance benchmark.
- Python backend: **776 passed, 13 skipped**, 89 warnings, in 973.31 seconds. The optional PostgreSQL and Kafka contracts require their dedicated services and are not certified by this run. Python coverage requests failed before collection because pytest-cov is not installed; the passing plain run does not provide a line/branch percentage.
- Express domain/application suite: **132 suites, 796 tests passed**. With the configured whole-source denominator, this subset covers **47.98% of lines and 39.12% of branches**. This is a subset result, not the coverage of the complete Express suite; infrastructure tests were not selected.
- GraphQL domain/application suite: **146 suites, 1,178 tests passed**. Its imported-file denominator reports **94.27% of lines and 81.05% of branches**, and also includes a test factory. This is not whole-project coverage and is not comparable to the Express percentage. Resolver and database suites were not selected.

Across these selected runs, **4,253 tests passed and 63 skipped**, with no remaining test failures. This total combines full local Python, sidecar, PHP-unit, client-unit, and harness runs with the selected TypeScript domain/application suites. It is not a complete live-infrastructure or browser certification. No application source, test configuration, or dependency manifest was changed by this audit.

### Measured branch gaps

Aggregating source-file counts by layer, the selected suites measure:

| Application / layer | Lines | Branches | Denominator |
| --- | ---: | ---: | --- |
| GraphQL domain | 96.12% | 85.74% | Imported domain source |
| GraphQL application | 94.98% | 78.96% | Imported application source |
| Express domain | 92.29% | 78.80% | Configured domain source |
| Express application | 81.84% | 66.26% | Configured application source |

This supports strong core-domain coverage in the selected runs and identifies Express application branching as a useful next investment. It does not establish infrastructure coverage, since infrastructure test suites were not selected.

The backend rows below identify gaps in selected domain/application testing; other, unselected backend tests may exercise some of these paths. Client rows come from the complete Vitest run. The listed files each have at least ten instrumented branches.

| Application / source file | Lines | Branches |
| --- | ---: | ---: |
| Express `application/useCases/ReceiveStock.ts` | 67.74% | 28.57% |
| Express `application/useCases/DispatchStock.ts` | 53.48% | 34.78% |
| Express `application/services/AuthService.ts` | 49.10% | 43.05% |
| Express `domain/serial/aggregates/SerializedItem.ts` | 76.74% | 25.00% |
| GraphQL `application/useCases/ManageJournals.ts` | 75.00% | 33.33% |
| GraphQL `application/useCases/RouteOrder.ts` | 61.53% | 34.00% |
| GraphQL `application/useCases/ManageRoles.ts` | 50.87% | 55.55% |
| Client `App.tsx` | 25.63% | 18.35% |
| Client `api/python.ts` | 51.54% | 44.04% |
| Client `components/PythonReportingPanel.tsx` | 62.65% | 45.16% |

Prioritize receipt/dispatch tests with costing repositories enabled, lot-specific shortages, capacity validation, and dependency failures. The implementation saves inventory before later costing operations, making unchanged-state/rollback assertions especially valuable when those later operations fail. Journal lookup should explicitly test foreign-tenant denial, missing entries, and balanced/unbalanced creation. Authentication tests should exercise rejection/revocation paths and tenant boundaries.

The client’s `App.tsx` accounts for 910 instrumented branches, of which only 18.35% are covered. Navigation, authenticated/unauthenticated state transitions, backend selection, permission-dependent flows, and failure recovery deserve direct tests alongside the existing component panels. The Python adapter and reporting panel are the next measured client gaps.

The initial sandboxed Python API runs stalled before completing their first request. A diagnostic stack located the wait in Python’s Windows asyncio internal socket-pair creation (`socket.accept`), before application request handling. Repeating the tests outside the sandbox allowed execution to proceed. This environment stall is not counted as an application regression. The initial stalled client coverage worker was also stopped before retrying outside the sandbox.

## Historical coverage artifact

The discovered Express `coverage/lcov.info` was last modified July 14, 2026. It records 4,472/5,788 lines, 1,116/2,077 branches, and 771/1,013 functions. These figures are stale and are not a current coverage baseline.

## Recommended sequence

1. Make measurement reproducible: pin coverage tooling, include all runtime source, publish line/branch results and test/skip counts per application.
2. Establish fresh green unit and real-service integration baselines with explicit environment prerequisites.
3. Require shared-ledger and full conformance results for the relevant changes.
4. Add a small live browser workflow suite and repair storage-mock fidelity.
5. Use fresh per-file branch reports to choose new tests, emphasizing stock/version invariants, costing, cross-tenant rejection, transaction rollback, retries/idempotency, and event delivery failures.

## Reproducing the selected runs

Run from each application directory unless marked parent. Coverage outputs should be directed to a separate report directory when preserving an earlier baseline.

```powershell
# Parent
python -m pytest tests/harness -q --tb=short

# Python backend
python -m pytest tests -q --tb=short

# Sidecar
python -m pytest app/tests -q --tb=short

# GraphQL: domain/application only; imported-file coverage denominator
node node_modules/jest/bin/jest.js --runInBand --coverage --testPathPatterns tests/domain tests/application

# Express: domain/application only; all configured source in denominator
node node_modules/jest/bin/jest.js --runInBand --coverage --testPathPattern='tests/(domain|application)/'

# Client: complete Vitest suite, excludes Playwright
node node_modules/vitest/vitest.mjs run --no-file-parallelism --coverage

# PHP: unit suite; enable installed extensions for this invocation
$phpAuditExt = Join-Path (Split-Path (Get-Command php).Source) 'ext'
php -d "extension_dir=$phpAuditExt" -d extension=php_mbstring.dll -d extension=php_pdo_sqlite.dll -d extension=php_sqlite3.dll -d extension=php_curl.dll vendor/bin/phpunit --exclude-group integration
```
