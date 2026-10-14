# Conformance scenario implementation and validation

All 40 original pass-only scenarios now contain executable workflows and
assertions. The full manifest is 47 scenarios × four backends = 188 results.
No backend error, absent capability, skip or missing result is treated as success.

## Verification completed

- Harness regression suite: **97 passed**. Includes the actual runner/fixtures
  against smoke protocol doubles, rejection of full runs against those doubles,
  empty-scenario guards, state transitions, injected balance/single-cent faults,
  and 27 GraphQL adapter operations validated against the checked-in SDL.
- Current Python source served locally against a new, separate SQLite database:
  **24 passed, 23 failed**, 141 non-Python combinations deselected, no skips.
  This is actual HTTP/API execution, not a mocked backend. It is not PostgreSQL
  concurrency/RLS certification or a four-backend passing conformance run.
- Shared ledger compatibility migration: **6 PostgreSQL tests passed** in
  temporary schemas rolled back after each test. Applied to the local development
  database, then verified with an authenticated Express ledger HTTP 200.
- Client selector: **3 tests passed**, TypeScript/Vite build passed. Python is
  included in the API Node dropdown and the header switcher.

## Python results

| Scenario group | Passed | Failed | Remaining failure |
| --- | ---: | ---: | --- |
| Accounting | 5 | 0 | |
| Administration | 3 | 2 | RFID and cache-management APIs absent |
| Existing AI checks | 0 | 4 | Anomaly/rebalance APIs absent |
| Compliance | 0 | 5 | Compliance ledger/verification/reconstruction/replay APIs absent |
| Cross-docking/drop-ship | 0 | 2 | Required workflow APIs absent |
| Smoke | 3 | 0 | |
| Stock operations/concurrency | 5 | 0 | |
| Kits | 3 | 0 | |
| Lots/returns quarantine | 1 | 3 | FEFO suggestions, lot hold/release and recall APIs absent |
| Procurement | 1 | 1 | Forecast report API absent |
| Serials/barcodes/RMA | 3 | 0 | |
| Warehouse | 0 | 4 | Location, putaway, route and slotting APIs absent |
| Webhooks | 0 | 2 | Generic subscription/delivery-log APIs absent |
| **Total** | **24** | **23** | |

The failures identify mounted API gaps, not necessarily missing domain algorithms.
For example, Python has FEFO costing and signed integration ingestion, but those
do not provide the public FEFO-picking/recall or generic outbound-subscription
contracts exercised here. Backend-specific functionality is not redirected to
another service to make these scenarios pass.

## Contract decisions

- Each business scenario creates and authenticates its own tenant. Cross-scenario
  costing changes, count records and stock cannot contaminate other assertions.
- Money remains exact integer cents. Valuation tests consume stock after receiving
  two differently priced layers: FIFO 3500, LIFO 2500, WAC 3000 cents remaining.
- FEFO deliberately receives the later-expiring lot first and checks ordered
  picks. Serial history preserves the serial and persisted record ID.
- Invalid overselling/reservations must leave stock unchanged. Concurrent writes
  with the same expected version require one success, one explicit conflict.
- Python kit commands supply versions only for the affected source stock, and
  serial commands supply location metadata only for supported actions.
- Python includes quarantined physical units in on-hand; the other APIs exclude
  them until resolution. Tests verify that held units cannot be consumed, then
  verify the saleable result after inspection rather than confusing these DTOs.
- Tamper testing requires an explicitly enabled disposable PostgreSQL database,
  modifies only an identified entry owned by the newly seeded tenant, restores it
  in `finally`, and rechecks the server's verifier. Missing configuration fails.
- Webhook destinations use the reserved `.invalid` domain. Tests require persisted
  subscription/delivery facts rather than an invented successful delivery.

The harness's isolated backend databases do **not** establish shared-schema
interchangeability. See `database-schema-parity-2026-10-14.md` for confirmed storage
differences and the migration/shared-storage validation work still required.
