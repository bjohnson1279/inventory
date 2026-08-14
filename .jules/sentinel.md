# Jules Sentinel Directives for Inventory Parent Repository

## 🛑 Security & Submodule Boundary Guidelines
- **NEVER MODIFY SUBMODULES**: Never commit changes to `gql-ddd-inventory/`, `js-ddd-inventory/`, `php-ddd-inventory/`, `react-ddd-inventory-client/`, or `inventory-python-sidecar/` from this parent repository. Security patches targeting child services must be submitted in separate PRs in those respective repositories.
- **NO SUBMODULE COMMITS**: Never stage submodule commit pointer updates in the parent repo.
- **PARENT REPO FOCUS**: Security remediation in the parent repo is limited to root Docker compose environment configurations, shared network definitions, and conformance test fixtures.

## 🚫 Safe Refactoring Directives
- **Environment Variable Fallbacks**: Preserve local testing workflows when hardening environment variables in conformance tests and compose files.
- **No Scratch Files**: Do not commit exploratory verification scripts (`test_*.py`, `test_*.js`, `*.scratch`).
- **Zero-Diff Guard**: Terminate execution cleanly without creating PRs if security checks are already compliant on `main`.
