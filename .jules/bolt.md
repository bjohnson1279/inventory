# Jules Bolt Directives for Inventory Parent Repository

## 🛑 Critical Submodule Boundaries
- **NEVER MODIFY SUBMODULES FROM PARENT REPO**: The directories `gql-ddd-inventory/`, `js-ddd-inventory/`, `php-ddd-inventory/`, `react-ddd-inventory-client/`, and `inventory-python-sidecar/` are standalone git repositories linked via `.gitmodules`.
- **NO SUBMODULE COMMITS OR POINTER UPDATES**: Never stage or commit submodule files or updated submodule commit hashes in pull requests targeting the parent `inventory` repository.
- **CHILD REPO SCOPE**: All backend and frontend application modifications (features, bug fixes, performance optimizations, migrations) must be developed and submitted to their respective child repositories directly.
- **PARENT REPO SCOPE**: The parent repository is strictly for cross-system integration, end-to-end conformance test suites (`tests/`), helper automation scripts (`scripts/`), container orchestration (`docker-compose.*.yml`), and top-level architecture documentation.

## 🚫 Prevention Directives
- **Zero-Diff Task Termination**: If the requested task, optimization, or conformance check is already satisfied on `main`, DO NOT create an empty pull request or commit log acknowledgments. Cancel task execution cleanly.
- **No Scratch Files**: Never stage or commit `test_*.py`, `test_*.ts`, `test_*.js`, `test.js`, or `*.scratch` files to git.
- **Do Not Modify `.gitmodules`**: Submodule definitions, URLs, and paths must not be modified unless explicitly instructed by a human administrator.

## Prevention Directives for Automated Refactoring
- **Never Overwrite Complete Files**: Always use range-scoped replacement chunks (`StartLine`/`EndLine`) for edits to `schema.prisma`, `index.ts`, `public/index.php`, or DDL SQL scripts.
- **Do Not Remove Core Declarations**: Do not delete existing route registrations or database DDL tables.
- **Environment Isolation Compatibility**: When replacing fallback secrets, preserve test environment execution via `!getenv('APP_ENV')` or `getenv('APP_ENV') === 'testing'`.
- **No Scratch Files**: Never stage or commit `test_*.ts`, `test_*.js`, `test.cjs`, `fix_*.php`, or `test.js` files to git.
- **No Unresolved Conflict Markers**: Never stage or commit files containing Git merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`, `|||||||`). Always resolve conflicts cleanly before committing.

## Hallucinatory Task & Empty PR Directives
- **Zero-Diff Task Termination**: If the requested optimization, refactor, or fix is ALREADY natively present in the target branch, DO NOT create an empty pull request or commit an acknowledgment PR. Exit the task cleanly without opening a PR.
- **Stale Suggestion Guard**: Always verify the current code on `main`/`master` before planning changes. If no actionable diff is required, cancel task execution immediately.

