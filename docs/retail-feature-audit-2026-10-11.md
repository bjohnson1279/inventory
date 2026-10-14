# Small-retail feature evaluation and implementation plan

Date: 2026-10-11. Scope: current local checkout of GraphQL TypeScript, REST TypeScript, PHP REST, Python FastAPI, shared React client, and parent conformance/CI configuration. This is a source and targeted-test evaluation, not a production certification or a measured whole-repository coverage report. No application implementation was changed.

This is the original audit snapshot. Subsequent Python work has implemented
authenticated catalog/stock workflows, costing/valuation, and tenant/security
controls. See [identity/catalog progress](../python-ddd-inventory/IDENTITY_CATALOG.md),
[costing](../python-ddd-inventory/COSTING.md) and
[security coverage](../python-ddd-inventory/SECURITY.md). Count ownership and line
persistence and reviewed stock reconciliation are implemented; see
[physical counts and adjustments](../python-ddd-inventory/COUNTS.md). Procurement
and replenishment are also implemented; see
[procurement progress](../python-ddd-inventory/PROCUREMENT.md). Customer/supplier
returns, quarantine decisions and inventory write-offs are implemented; see
[returns progress](../python-ddd-inventory/RETURNS.md). Internal transfers and
named-unit stock conversions are now implemented; see
[transfers and units](../python-ddd-inventory/TRANSFERS_UOM.md). Acknowledged Kafka
delivery, tenant-scoped leased retries and dead-letter recovery are now implemented;
see [event delivery](../python-ddd-inventory/EVENT_DELIVERY.md). Serial lifecycles
and quantity kits are now implemented; see
[serials and kits](../python-ddd-inventory/SERIALS_KITS.md). Financial journals,
commercial settlements/credits/refunds and ledger reporting are now implemented;
see [financial accounting](../python-ddd-inventory/FINANCIAL_ACCOUNTING.md).
Signed store-order reservations/fulfillment and acknowledged inventory/journal
connector deliveries are now implemented; see
[integrations](../python-ddd-inventory/INTEGRATIONS.md). Durable report snapshots,
private JSON/CSV exports, UTC schedules, remaining-stock aging and active
low-stock/expiry alerts are now implemented; see
[reporting and alerts](../python-ddd-inventory/REPORTING_ALERTS.md). Native provider
adapters, external reconciliation, email/PDF exports and public sharing remain
unfinished. Native PO packaging
and dedicated transfer/UOM screens remain follow-up work.

Python workforce refinements now include persisted operator profiles, validated
shift assignments and clock transitions, source-backed activity metrics, and
explicit-input staffing plans. The Python client uses actual records and unknown
measurement states; see [workforce](../python-ddd-inventory/WORKFORCE.md).
Payroll, staff availability/leave and automated demand-forecast linkage remain
outside these refinements.

Workforce verification passed 20 focused backend cases, 51 broader
security/count checks, the final three SQLite/PostgreSQL security contracts,
and four concurrency/migration checks. The final client selection passed 40
tests and TypeScript compilation. These selections overlap; they are not a new
full-suite coverage measurement. Deployment requires the reviewed migration
for the four workforce tables.

## Assessment

The conformance harness has since been repaired to include all four backends,
verify actual setup/authentication, propagate failures and require complete,
attributed reports. All forty original business scenarios now have executable
workflows and assertions; missing backend capabilities remain genuine failures.
New empty scenarios still fail explicitly. Mandatory smoke probes establish
health/identity wiring separately from full parity. See the updated
[harness guide](../tests/conformance/README.md).

The application has substantial inventory-domain breadth, especially in the TypeScript and PHP implementations. It is not yet supported by credible evidence of four-backend behavioral parity. Several features with immediate retail value—physical counts, aging, reliable notifications, and complete Python workflows—are unfinished at the API/persistence boundary. Stock transaction consistency and tenant isolation deserve attention before additional advanced automation.

For a small retailer, reliable receiving, sales deductions, returns, counts, replenishment, and clear exceptions matter more than the current breadth of warehouse/AI panels. Treat the three mature implementations as candidates for a retail pilot after the critical work below; Python needs a larger implementation effort before it can offer the same product.

## Feature comparison

Legend: **Present** means substantive domain/application/API artifacts exist; it does not imply every scenario was executed. **Partial** means a concrete wiring, persistence, or behavior gap was found. **Domain only / absent API** means reusable logic exists without an equivalent exposed workflow. Ratings are qualitative, not numeric coverage scores.

| Capability | GraphQL TypeScript | REST TypeScript | PHP REST | Python FastAPI | Retail assessment |
|---|---|---|---|---|---|
| Catalog, variants, barcode and UOM modeling | Present | Present | Present | Partial: flat SKU/name/price catalog; no comparable variant/barcode/UOM workflow in mounted REST API | Essential; Python contract differs materially |
| Receive and dispatch stock | Present; optimistic version checks and atomic inventory/outbox persistence | Present; inventory and cost layers saved separately | Present; inventory saved before cost-layer validation completes | No equivalent receive/dispatch REST workflow mounted | Critical consistency gap |
| Reservations, allocations and transfers | Present application paths | Present application paths | Present application paths | No equivalent mounted retail stock API found | Verify overselling and cancellation, not just entity methods |
| Procurement and replenishment | Present purchase-order and replenishment use cases | Present purchase orders/reorder policies | Present purchase-order lifecycle and reorder policies | Supplier collaboration logic/portal is partial; no equivalent purchase-order retail API found | High value; missing four-way lifecycle proof |
| Costing and valuation | FIFO/LIFO/WAC/FEFO strategies present | Accounting/cost-layer implementation present | FIFO/LIFO/WAC/FEFO strategies present | FIFO/LIFO/WAC calculations only in inspected costing module; no FEFO there and no equivalent valuation REST workflow | Standardize currency, rounding, physical picking and valuation contracts |
| Lot expiration, recall and quarantine | Present; FEFO ordering logic | Present lot-aware paths | Present lot-aware paths | Lot-domain helpers; no equivalent mounted workflow | Valuable for food/cosmetics; integration evidence weak |
| Serial lifecycles and kits | Present | Present | Present | No equivalent mounted workflow found | Useful for electronics and bundles; optional for many retailers |
| Physical/cycle counts and offline submissions | Partial: federated resolver uses module-level mock counts | Partial: plan/schedule/classification API, empty execution history | Partial: start/submit/list controller returns fixed/empty results | Partial: submission does not save line changes or adjust stock; offline sync acknowledges without executing | Must finish before routine stocktaking |
| Aging and dead stock | Partial: federated resolver feeds hard-coded stock/movement data | Partial: route-local services return empty buckets/zero value and no dead stock | Aging domain services present; durable retail reporting flow needs verification | Partial: endpoint uses mock movements | Valuable once driven by real movements |
| Notifications and low-stock action | Existing handlers plus partial federated inbox over an empty in-memory list | Notification repository/routes present; delivery configuration needs verification | Persisted notification service and event listeners present | Empty in-memory inbox | Useful only if alerts survive restart and lead to action |
| Reporting and scheduled exports | Definitions/workers/resolvers present | Reporting implementation present | Report controller and integration tests present | Partial: report creation/scheduling/queue responses are scaffolds | Do not expose successful queue status without durable work |
| Omnichannel and accounting integrations | Adapters/webhook tests present; accounting can return fabricated sync IDs | Adapters/security tests present; some credentials fall back to mock strings | Adapters and integration artifacts present | Channel services/webhook tests present; supplier portal includes mock IDs | Test replay, duplicate delivery and actual remote results |
| Roles and tenant isolation | Guards exist; inspected inventory repository queries lack explicit tenant scope | Authentication/tenant-aware paths exist; newer routes take tenant IDs from input | Roles/tenant tests exist; full workflow isolation needs verification | Role decorators exist but mounted app does not populate required auth state; product model/repository are tenantless | Release blocker for multi-tenant operation |
| AI, RFID, routing, ESG, labor and intercompany | Broad artifacts | Broad artifacts | Broad artifacts | Domain algorithms and selected scaffolds | Secondary to retail fundamentals; presence is not operational readiness |

## Confirmed findings and evidence

Paths below are relative to the repository root so the report remains portable.

1. **Critical: cross-backend conformance is largely empty.** AST inspection of `tests/conformance/test_*.py` found 12 files, 44 test functions, and **40 functions whose only statement is `pass`**. Stock CRUD, concurrency, procurement, accounting, lots, serials, kits, webhooks and compliance therefore lack the advertised assertions. The four nonempty tests are AI feature checks, principally response shape and empty-tenant behavior. File names and test counts are not coverage. These files are tracked; `.gitignore`'s `test_*.py` pattern still risks hiding future tests. Tracked conformance bytecode should also be cleaned up in a follow-up change.

2. **Critical: harness can conceal failures and omit Python setup.** `tests/conformance/conftest.py` skips offline backends, falls back to `dummy-token`, and has a dummy `seed_data` fixture. `auth_token` depends on both REST and GraphQL fixtures: the REST fixture skips GraphQL, preventing the intended GraphQL login path. `scripts/run_conformance.py` lists only three backends, accepts any health response below 500 (including 404), does not fail on seed warnings, discards the pytest subprocess exit code, and returns without failure for missing/empty reports. The Compose file does include Python, so the runner and fixtures disagree.

3. **Critical: Python is not an equivalent retail backend.** `src/presentation/main.py` mounts catalog, counts, reports, supplier, webhook, notification, aging and mock GraphQL routers. It exposes no equivalent login/setup or full inventory/procurement/serial/kit endpoints expected by `react-ddd-inventory-client/src/api/python.ts`. The product endpoint returns `price_amount` and a flat SKU; the client expects the common product/variant model. Client cycle-count URLs also differ from the mounted `/api/cycle-counts` API. The mock Strawberry product query is not evidence of catalog persistence parity.

4. **Critical: Python authentication and tenancy are incomplete.** `src/infrastructure/auth/rbac.py` expects validated roles/permissions in `request.state`; the inspected application installs security-header middleware but no middleware that supplies that identity. `tests/conftest.py` patches role extraction to always return ADMIN/MANAGER/USER, masking the real application path. `ProductModel` has a globally unique SKU and no tenant column; product repository lookups and listing are global. A role-only decorator cannot enforce tenant ownership.

5. **High: stock and costing can diverge after failure.** REST TS `src/application/useCases/ReceiveStock.ts` saves quantity before checking product/variant and saving its cost layer. Its `DispatchStock.ts` saves quantity before validating a requested lot's remaining layers. PHP `src/Application/Inventory/UseCases/DispatchStock.php` saves product stock before it can throw for insufficient cost layers. No enclosing transaction is evident in these inspected use cases/controllers. These are concrete partial-write sequences; validate caller behavior with injected-failure integration tests before assuming all entry points share the same defect.

6. **High: GraphQL event delivery and tenant boundaries need integration proof.** `PostgresInventoryRepository.save` pulls events into an atomic inventory/outbox transaction and uses optimistic updates, which is a strength. `DispatchStockUseCase` then calls `pullDomainEvents()` again for its immediate dispatcher. That path may see no events; verify whether the outbox worker is the intended sole delivery mechanism. Its repository queries use SKU/location or unqualified `findAll`, with no explicit tenant filter. Establish whether the surrounding data model enforces ownership before relying on this in a multi-tenant deployment.

7. **High: counts are not complete reconciliations.** GraphQL `cycleCountResolvers.ts`, mounted by the federated inventory subgraph, uses mock counts and comments that tenant filtering is missing. REST TS `cycleCount.routes.ts` passes empty last-execution dates to its scheduler, allowing repeated scheduling. PHP `CycleCountController.php` returns `cc-123`, unconditional success and an empty list; `public/index.php` wires its start endpoint. Python's count router fabricates expected quantity 10 when lines are absent, comments out line persistence, omits ledger adjustment, and returns `synced: True` without processing offline submissions.

8. **High: aging/reporting can look successful while doing no useful work.** GraphQL `agingResolvers.ts` uses hard-coded entries and costs; REST TS `aging.routes.ts` defines local placeholder analysis classes instead of a working report; Python aging/report endpoints use mock data or return IDs without durable report/outbox writes. Python notification and GraphQL federated notification resolvers initialize empty process-local inboxes. Treat these specific paths as incomplete even where another legacy API exists.

9. **High: integration success can be fabricated or hidden.** GraphQL `AccountingSyncService.ts` returns mock journal IDs when credentials are absent/mock. The Python React adapter converts several outbox/quarantine/valuation failures into empty or zero results and ignores its valuation `locationId` argument. A store owner can see apparent absence of stock/issues instead of an integration error. Use explicit capability and error states.

10. **Medium: normalization can hide meaningful disagreement.** `tests/conformance/comparator.py` ignores list order and strips IDs recursively. FEFO pick order, serial identity, reference lineage and audit sequence must be tested with stricter, feature-specific comparators. Monetary representation also differs: Python decimal currency amounts versus TS/PHP cents-based cost layers. GraphQL `Quantity` checks negativity but does not reject nonfinite values at construction; Python costing calculations lack an explicit negative-sale-quantity guard. Test these at both domain and API boundaries.

## Test evidence and coverage limitations

Fresh targeted runs:

| Backend | Selection | Result |
|---|---|---|
| GraphQL TS | AccountingMethods, DispatchStock, ReceiveStock | 3 suites, 17 tests passed; ts-jest configuration warnings |
| REST TS | Explicit DispatchStock and ReceiveStock test paths | 2 suites, 4 tests passed |
| PHP | Filter DispatchStock / Costing / ReceiveStock | 15 tests, 45 assertions passed after enabling installed mbstring extension |
| Python | Costing and product API selection | Collection blocked by missing `redis` in local venv; no tests executed |

The initial REST TS test-selection flag was incompatible with its Jest version and selected a broader suite; sandbox transform-cache permission errors invalidated that attempt. The explicit-path rerun passed. These results are targeted checks, not a whole-suite baseline or runtime parity test. No statement/branch coverage percentage is asserted. Python lists redis in requirements, so this local failure is environment drift, not proof the package declaration is absent.

Existing tests include substantial TS domain/use-case suites, PHP domain and integration tests, Python domain/API tests, and React component tests. Important gaps remain:

- **Parent CI omits PHP integration discovery:** `phpunit.xml` includes only `tests/Unit`, and parent `.github/workflows/conformance.yml` invokes the default suite. PHP's own `.github/workflows/phpunit.yml` explicitly runs `tests/Integration`; preserve that coverage and add it to parent validation of the pinned versions.
- **Production database behavior:** Python fixtures force in-memory SQLite even when CI supplies a PostgreSQL URL. They cannot prove PostgreSQL locking, numeric precision, migrations or tenant isolation. Exercise the deployment database separately.
- **Dependency isolation:** Python domain tests inherit a root conftest that imports the whole app; a missing optional/runtime dependency prevents pure costing tests from collecting.
- **Failure branches in composed stock workflows:** inspected dispatch unit tests omit optional cost-layer/reorder/ledger dependencies, so passing tests do not cover partial-write failures.
- **Browser-to-server contracts:** inspected React product tests inject callbacks and data. Add actual HTTP adapter contracts and browser journeys against each backend; component behavior alone cannot detect Python endpoint/model mismatch.
- **Concurrency and recovery:** require simultaneous sales, duplicate webhook replay, retry after commit, transfer interruption, worker restart and backup restoration evidence.
- **No enforced coverage floors seen in inspected Jest/PHP configs:** add focused branch thresholds after establishing a trustworthy baseline, with explicit exclusions. Do not use a global percentage to substitute for business invariants.

## Implementation backlog and sequence

Estimates below are relative effort for prioritization, not delivery commitments. Assign one owner per feature contract and one implementer/reviewer per backend. Each ticket should carry the same input vectors and acceptance criteria across all four runtimes.

| Order / ticket | Work | Dependencies | Effort | Completion evidence |
|---|---|---|---|---|
| P0-01 | Write canonical retail contracts: catalog/variant, stock states, money, locations, errors, identity, mutation IDs; inventory capabilities per backend | None | Medium | Reviewed contract and executable vectors; unsupported features reported explicitly |
| P0-02 | Repair conformance runner/fixtures, include Python, assert health/login/seed, propagate pytest exit, reject missing/empty reports and mandatory skips | P0-01 | Medium | Deliberately broken backend, bad auth and collection error each fail CI; all four have attributed results |
| P0-03 | Replace 40 empty tests with real workflows; scope ignore exceptions for maintained tests; stop tracking generated bytecode in a reviewed cleanup | P0-02 | Large | Each mandatory test performs writes/reads and checks expected values, not merely equal responses |
| P0-04 | Implement authenticated identity and tenant-scoped persistence end to end, starting with Python and inspected GraphQL inventory boundaries | P0-01 | Large | Two tenants with identical SKUs cannot read/write/count/export each other's data; supplied tenant mismatch rejected |
| P0-05 | Make quantity, reservations, lots/cost layers, ledger and outbox changes one transaction; optimistic conflict handling and mutation idempotency | P0-01, P0-04 | Large | Failure at every write leaves all records unchanged; two buyers competing for last unit produce exactly one successful sale |
| P1-01 | Complete Python retail catalog, inventory, procurement, returns, serial/kit and valuation APIs in vertical slices; align client DTOs/paths | P0 contracts/security/transactions | Very large | Each slice passes same conformance and browser journey as other backends; API restart preserves data |
| P1-02 | Replace count scaffolds in all backends: real plans/history, assignment, blind count, review/recount, durable lines, approved stock adjustment, offline replay | P0-04, P0-05 | Large | Count expected 10 / observed 8 creates approved -2 adjustment once; repeats do not schedule or adjust twice |
| P1-03 | Implement real aging/dead-stock reports, durable notification inbox and report jobs; surface adapter failures | Reliable movement ledger | Medium–large | Seed known movement dates, verify nonzero buckets/costs; restart retains unread alert and queued export |
| P1-04 | Standardize costing/FEFO/UOM/serial/return transitions and wire all stock entry points to the same policies | P0-05 | Large | Canonical edge vectors pass, including expired/quarantined stock and insufficient requested lot |
| P1-05 | Verify integrations, remove production mock-success behavior, reconcile external stock and manage retries/dead letters | P0-05 | Medium–large | Signed duplicate webhook adjusts once; remote failure remains visible; recovery catches up without duplicate orders |
| P1-06 | Expand parent CI to actual DB integration, PostgreSQL Python tests and four-backend browser adapter journeys | P0-02 onward | Medium | Clean checkout runs required suites; counts of pass/fail/skip/collection errors published per backend |
| P2-01 | Retail mode: simplify navigation to Stock, Receive, Count, Reorder, Returns, Reports; hide unavailable capabilities | P1 core completion | Medium | Store employee completes workflows without developer panels or hidden API errors |
| P2-02 | Operational hardening: migration/upgrade tests, restart recovery, backup restore, realistic catalog latency and accessible scanning flows | P1 | Medium | Restore reconciles quantities/costs; release regression pack passes at agreed store size |

Do P0-01/02 first, then security and transactions alongside executable workflow tests. Implement each P1 feature as a complete domain → database → API → client → test slice across backends. Avoid copying a scaffold to achieve superficial symmetry. Keep advanced AI features behind capabilities until core flows are dependable.

## Required acceptance scenarios

1. Create the same SKU in two tenants; tenant A sees only its variants, stock, costs, counts and reports.
2. Receive 10 units at 100 cents and 10 at 200 cents, dispatch 12: FIFO COGS 1,400 cents, LIFO 2,200, WAC 1,800; remaining quantities and values reconcile. Define rounding for fractional UOM separately.
3. Reject negative/nonfinite quantities, invalid precision, duplicate tenant SKU, unsupported currency/UOM and malformed timestamps consistently.
4. Sell the last unit concurrently; reject the loser, preserve nonnegative available stock, and emit one durable movement.
5. Inject failure after quantity save and before cost/ledger/outbox save; assert complete rollback. Retry a committed request without double deduction.
6. FEFO chooses the earliest eligible expiry in exact order; quarantined/expired lots cannot ship; null/equal expiry behavior is deterministic. Separate physical picking policy from accounting policy.
7. Receive a PO in two partial deliveries, reject unintended over-receipt, replay delivery once, and reconcile outstanding quantity/cost.
8. Count during concurrent sales using a specified snapshot/cutoff policy; approve discrepancies once; offline duplicates and obsolete submissions are handled explicitly.
9. Reserve, cancel, fulfill, transfer, assemble/disassemble and return stock; quantity conservation, serial ownership and ledger references remain valid after every transition.
10. Duplicate/out-of-order signed webhooks, publication failure, worker crash and restart produce durable, observable recovery; real notifications/reports survive restart.
11. Browser journeys—create variant, scan receive, sell/dispatch, count, reorder, return—run against each backend with real authentication and transport.

## Highest-value retail additions and extensions

These are product judgments based on the audit, assuming a small single-store retailer with optional online sales. Existing code may supply foundations; items below describe the missing complete retail experience rather than claiming every underlying concept is absent.

| Rank | Addition / extension | Value | Scope and measurable outcome |
|---|---|---|---|
| 1 | POS sale/refund reconciliation and a visible sync-health screen | Keeps shelf and online availability accurate; reduces manual corrections | Extend existing integrations to sales/refunds/voids and nightly reconciliation; measure unexplained stock differences and recovery time |
| 2 | Reorder workbench with supplier lead times, case packs/MOQs, incoming stock and PO drafts | Reduces stockouts and excess cash tied in inventory | Extend replenishment/procurement; explain suggested quantity and let owner approve; measure stockout days and aged inventory |
| 3 | Phone/scanner receiving and counts with printable labels | Reduces data entry and counting effort | Finish counts and barcode paths, support unknown scans and duplicate protection; measure receipt/count time and recount rate |
| 4 | Fast CSV onboarding with variant mapping, preview, row errors and undo | Makes adoption practical for stores with existing spreadsheets | Import suppliers/SKUs/barcodes/opening stock/costs in staged batches; measure time to first reconciled inventory |
| 5 | Owner action dashboard: days of cover, low stock, dead stock, shrink and margin | Turns inventory data into decisions | Finish aging/valuation first, use actual sales/returns, make every tile actionable; measure alert-to-action time |
| 6 | Staff-friendly damage/theft/return adjustments with reason codes and approval thresholds | Creates reliable accountability without a heavy enterprise workflow | Extend returns/audit/approvals; scan item, record disposition, reconcile stock/cost and refund reference |
| 7 | Seasonal/size-color assortment replenishment and simple markdown suggestions | Useful for apparel/gifts, where aggregate SKU forecasts miss missing sizes | Extend variants and demand planning; owner-approved rules, explain sales velocity and aged stock |
| 8 | Expiry alerts and markdown/waste workflow | High value specifically for food, cosmetics and other perishables | Extend FEFO/quarantine; measure expired stock value; prioritize higher only for these retailers |

Market context supports prioritizing counts, barcode workflows, replenishment and channel stock accuracy: [Shopify inventory management](https://www.shopify.com/inventory-management) describes barcode counts, stock tracking and reporting; [Shopify's stock-count documentation](https://help.shopify.com/en/manual/inventory-and-locations/inventory-counts/creating-inventory-counts) describes location counts and staff permissions. These are product examples, not independent evidence of ROI for this application. Validate priorities with actual store operators and observed tasks before committing delivery estimates.

Defer autonomous purchasing, computer vision, 3D slotting, labor optimization and intercompany complexity until the core inventory and reconciliation checks pass. For a small-retail release, readiness means dependable daily workflows and recoverable failures, not the number of implemented classes or dashboard panels.
