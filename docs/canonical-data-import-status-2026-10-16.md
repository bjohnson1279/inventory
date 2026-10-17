# Canonical data import checkpoint

The importer is implemented in `scripts/import_canonical_data.py`; usage and
recovery details are in `database/README.md`. It copies supported legacy data
without overwriting canonical records or changing source rows. Backend
repositories have not been switched to canonical storage.

## Last successful local preflight (2026-10-14)

The local database was upgraded to contract 0003 and passed the physical schema
check. The dry-run import had no issues and proposed these canonical rows:

| Target | Rows |
| --- | ---: |
| tenants | 1 |
| locations | 2 |
| roles | 3 |
| permissions | 15 |
| role_permissions | 32 |
| **Total** | **53** |

The source user, catalog, stock, journal and event tables were empty. Connection
routing entries were explicitly excluded; they are not business tenants.
Location ownership is recorded in `database/imports/local-shared.json`.

A private PostgreSQL custom-format backup was saved under the ignored
`.pytest_cache/canonical-import/` directory. The dry-run report is `plan.json`
in that directory. It says `applied: false`: **the business-data import has not
been applied**. Do not treat the old plan digest as current authorization to
import changed rows.

## Verification and remaining execution

The original schema/import suite passed 56 PostgreSQL tests before interruption.
Additional tests cover disappearing source rows, rollback after a partial-copy
failure, and tampered crosswalks. On resumption, nine offline checks pass, but
PostgreSQL is unreachable and Docker engine queries hang. The full current
database test suite and live reconciliation remain pending; no successful
current database verification is claimed.

Once Docker/PostgreSQL is available:

1. Run both canonical test files against PostgreSQL (59 cases in total), using
   a workspace `--basetemp` if the host's sandbox temp directory is unavailable.
2. Check the live canonical schema and regenerate/review the dry-run report.
   Reinspect ownership and take a fresh private backup if source data changed.
3. Apply using the new plan digest. Verify `reconciled_rows`, source preservation,
   canonical counts and import receipts.
4. Generate another plan and confirm `insert: 0`, all rows already present,
   and no issues. Run the physical schema check again.
5. Record the actual execution result here before beginning repository cutover.
