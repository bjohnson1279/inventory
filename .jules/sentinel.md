# Jules Sentinel Directives for Inventory Parent Repository

## 🛑 Security & Submodule Boundary Guidelines
- **NEVER MODIFY SUBMODULES**: Never commit changes to `gql-ddd-inventory/`, `js-ddd-inventory/`, `php-ddd-inventory/`, `react-ddd-inventory-client/`, or `inventory-python-sidecar/` from this parent repository. Security patches targeting child services must be submitted in separate PRs in those respective repositories.
- **NO SUBMODULE COMMITS**: Never stage submodule commit pointer updates in the parent repo.
- **PARENT REPO FOCUS**: Security remediation in the parent repo is limited to root Docker compose environment configurations, shared network definitions, and conformance test fixtures.

## 🚫 Safe Refactoring Directives
- **Environment Variable Fallbacks**: Preserve local testing workflows when hardening environment variables in conformance tests and compose files.
- **No Scratch Files**: Do not commit exploratory verification scripts (`test_*.py`, `test_*.js`, `*.scratch`).
- **Zero-Diff Guard**: Terminate execution cleanly without creating PRs if security checks are already compliant on `main`.

## Prevention Directives for Automated Refactoring
- **Never Overwrite Complete Files**: Always use range-scoped replacement chunks (`StartLine`/`EndLine`) for edits to `schema.prisma`, `index.ts`, `public/index.php`, or DDL SQL scripts.
- **Do Not Remove Core Declarations**: Do not delete existing route registrations or database DDL tables.
- **Environment Isolation Compatibility**: When replacing fallback secrets, preserve test environment execution via `!getenv('APP_ENV')` or `getenv('APP_ENV') === 'testing'`.
- **No Scratch Files**: Never stage or commit `test_*.ts`, `test_*.js`, `test.cjs`, `fix_*.php`, or `test.js` files to git.
- **No Unresolved Conflict Markers**: Never stage or commit files containing Git merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`, `|||||||`). Always resolve conflicts cleanly before committing.

## Hallucinatory Task & Empty PR Directives
- **Zero-Diff Task Termination**: If the requested optimization, refactor, or fix is ALREADY natively present in the target branch, DO NOT create an empty pull request or commit an acknowledgment PR. Exit the task cleanly without opening a PR.
- **Stale Suggestion Guard**: Always verify the current code on `main`/`master` before planning changes. If no actionable diff is required, cancel task execution immediately.


## Prevention Directives for Automated Refactoring
- **Never Overwrite Complete Files**: Always use range-scoped replacement chunks for edits to `schema.prisma`, `index.ts`, `public/index.php`, `db/schema.rb`, or DDL SQL scripts.
- **Do Not Remove Core Declarations**: Do not delete existing route registrations or database DDL tables.
- **Environment Isolation Compatibility**: When replacing fallback secrets, preserve test environment execution via `!getenv('APP_ENV')` or `getenv('APP_ENV') === 'testing'`.
- **No Scratch Files**: Never stage or commit `test_*.ts`, `test_*.js`, `test.cjs`, `fix_*.php`, or `test.js` files to git.
- **No Unresolved Conflict Markers**: Never stage or commit files containing Git merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`, `|||||||`). Always resolve conflicts cleanly before committing.

## Completeness & Verification Directives
- **Explicit Parameter & Contract Validation**: When creating or modifying API endpoints (Express, Fastify, Rails, Laravel), always implement explicit parameter and request body validation schemas (e.g. `z.string().uuid()`) to prevent unhandled 404/500 fallthroughs.
- **Database Indexing for Queries**: When addressing query bottlenecks or adding query lookup filters, always implement native database index migrations rather than loading collections into memory and performing array filtering (`.filter()`, `.select`).
- **Co-Occurring Dependency Auditing**: When bumping any dependency version, verify that other transitive dependencies do not carry high/critical security advisories (e.g. run `bundler-audit`, `npm audit`). Never introduce a version bump that breaks underlying framework APIs.
- **Self-Verification Before Commit**: Always run syntax checks (`bash -n` for shell scripts, `tsc --noEmit` for TypeScript, linter checks) and targeted test runners locally before opening or updating a PR.

## Hallucinatory Task & Empty PR Directives
- **Zero-Diff Task Termination**: If the requested optimization, refactor, or fix is ALREADY natively present in the target branch, DO NOT create an empty pull request or commit an acknowledgment PR. Exit the task cleanly without opening a PR.
- **Stale Suggestion Guard**: Always verify the current code on `main`/`master` before planning changes. If no actionable diff is required, cancel task execution immediately.

## Assertiveness, Decisive PR Execution & Comparative Recommendations
- **Proactive & Decisive PR Submission**: Do NOT repeatedly pause to ask permission to open a pull request (e.g., avoid "Would you like me to open a PR for this?", "Can I submit the PR?", "Should I go ahead and create the PR?"). When an optimization, fix, or feature satisfies requirements, passes local test runners/linters, and preserves architectural invariants, proceed decisively to create and submit the Pull Request with a clear, structured summary and rationale.
- **Explicit Recommendations on Options**: When presenting multiple implementation strategies or architecture options (e.g., Option A vs. Option B), NEVER leave the choice open-ended or passive. Always make an explicit, reasoned recommendation (prefixed with `(Recommended)`) based on **overall technical effectiveness**:
  1. *Algorithmic & Complexity Gains*: Time and space complexity impact (O(N*M) -> O(N+M), reduction of nested scans).
  2. *Resource Overhead*: Heap allocations, memory pressure, and GC pause reduction.
  3. *Domain & Architecture Invariants*: Strict backward compatibility, contract stability, and prevention of regression risks.
  4. *Security & Reliability*: Input validation, cryptographic safety, and concurrency safety.
- **Lead with Recommended Path**: State clearly why the recommended solution delivers the highest net value and immediately execute or propose it as the primary course of action rather than asking open-ended questions.

## Scope Verification, Minimal Churn & CI Protection Directives
- **Scope Verification Before Variable Binding**: When adding interactive states or accessibility attributes (e.g. `disabled={loading}`, `aria-busy={loading}`, `isSubmitting`), NEVER assume a variable identifier exists. Always inspect component props, local state hooks (`useState`), or declaration scope first. If not defined, declare the state hook or reuse an existing scope variable. Never introduce TS2304 / TS2552 ("Cannot find name") compile errors.
- **Surgical Edits Only (No Whole-File Formatting)**: Never run whole-file code formatters (Prettier, Black, Pint, rustfmt) across unmodified lines. Changes must be strictly range-scoped and limited to the minimal AST block needed. Avoid noisy quote/whitespace churn that masks real logic changes and causes merge conflicts. Verify with `git diff -w` that non-functional churn is zero.
- **Zero Scratch File Commits**: Never stage or commit ad-hoc verification, patch, or debug scripts (`test.cjs`, `fix_*.cjs`, `fix_*.php`, `patch_*.py`, `patch_*.sh`, `scratch_*`). Execute checks via the project's native test commands (`npm test`, `pytest`, `phpunit`, etc.) and delete temporary scripts before creating git commits.
- **Never Weaken CI Workflows**: Do not modify `.github/workflows/**` to bypass failures (e.g. adding `|| true`, setting `continue-on-error: true`, or commenting out assertions). Always resolve the defect in the source code or test fixture.
- **Explicit Parameter & Variable Types**: In TypeScript files, avoid implicit `any` by always providing explicit types on functions, parameters, and arrow callbacks (e.g. `(id: string) => ...`). Verify zero type errors with `tsc --noEmit` before committing.

## 2026-09-29 - Non-Destructive Security Patching & CI Protection
**Learning:** Security patches must never weaken CI workflow files (`.github/workflows/**`) by appending `|| true` or `continue-on-error: true` to suppress test/build failures. Furthermore, when adding defensive type assertions or input validators in TypeScript, omitting explicit types can introduce `TS7006: Parameter implicitly has an 'any' type`.
**Action:** Never modify CI workflow definitions to bypass test failures; resolve the underlying issue in source code or test fixtures. Always provide explicit types on newly introduced parameters and helper functions. Ensure zero scratch scripts (`fix_*.php`, `test_*.js`) are committed.

## Additive Documentation & Scratch Cleanliness Directives
- **Strictly Additive Journal Updates**: When updating `.jules/*.md`, strictly append new dated entries (`## YYYY-MM-DD - Title`). NEVER delete, truncate, or overwrite historical learnings or previous entries.
- **Substantive Code Diff Requirement**: Pull requests must include substantive code changes in `src/`, `app/`, `lib/`, or `tests/`. Never open PRs that modify only `.jules/*.md` journals or root scratch scripts.
- **Zero Scratch File Commits**: Never commit `*.diff`, `*.patch`, `test_*.ts`, `test_*.js`, `test.cjs`, `fix_*.php`, or `patch_*.py` files. Always remove temporary debugging or verification scripts prior to committing.

## Scope Quarantine, Journaling & Security Test Invariants
- **Strictly Append-Only Journaling**: When adding learnings to `.jules/*.md`, append strictly at the end of the file. Do not rewrite, deduplicate, or remove lines beginning with `## YYYY-MM-DD`.
- **Surgical Scope Quarantine**: Modify only the files directly involved in the issue and their corresponding test fixtures. Do not delete, rename, or perform drive-by cleanups of unrelated root-level scripts or legacy files.
- **Coupled Test Fixture Awareness for Security Invariants**: When changing fail-open fallback behavior (such as hardening decryption to fail closed), always update upstream test mocks that rely on plaintext credentials or mock values.

- **Centralize Shared Test Doubles for Abstract Domain Repositories**: When mocking domain repositories across multiple test suites, define a single shared test double rather than duplicating inline mocks to prevent cross-suite synchronization bugs.
\n\n## Important Process Rules\n- **Only write your journal to your matching file (`.jules/sentinel.md`).** Do not edit or create journal files for other personas.\n


## 2026-10-07 - PSR-4 Standards, Sibling Target Partitioning & Method Contract Verifications
**Learning:**
1. Grouping multiple classes or enums into single `*Services.php` or `*Entities.php` files breaks PSR-4 autoloader discovery in PHP, causing unit test suites to fail with `Class not found`.
2. Concurrently generating multiple PRs against the same domain files produces painful merge conflicts and superseded PR waste.
3. Invoking entity methods without verifying exact signatures (e.g. calling `getItems()` instead of `getLines()`) causes fatal runtime errors.
**Action:**
- **Strict PSR-4 Compliance in PHP**: In PHP codebases, place every class, interface, and enum in its own file named exactly `<ClassName>.php` matching its namespace path.
- **Sibling Target Partitioning**: Before starting work on a file, inspect `git branch -r`. Avoid selecting files already modified in open PRs or active branches to prevent redundant sibling collisions.
- **Contract Signature Verification**: Always inspect entity definitions to confirm method and property names before writing service logic or test fixtures.

## 2026-10-07 - Process Streamlining, Sibling Coalescence & Autoloading Invariants
**Learning:**
1. Fragmenting stub methods across multiple micro-PRs on the same class (e.g. four PRs for RoleController) causes unavoidable sibling merge collisions and wasted CI cycles.
2. Placing multiple domain services into a single file breaks Composer PSR-4 autoloader discovery in PHP, triggering fatal Class not found errors.
3. Writing service calls against unverified entity methods (e.g. calling getItems() instead of checking lines) causes fatal runtime errors.
4. String-escaping markdown journal updates (\\n\\n) corrupts rendered formatting.

**Action:**
- **Coalesce Micro-PRs**: When implementing or scaffolding related controller endpoints, stub methods, or repository queries on a single class, consolidate all changes into a single coherent pull request. Never create separate fragmented PRs for each individual method of the same class.
- **Strict PSR-4 Isolation in PHP**: In PHP codebases, place every class, interface, and enum in its own file named <ClassName>.php matching its namespace path. Never combine multiple domain classes into a single file.
- **Domain Contract Verification**: Always inspect entity and aggregate root definitions to verify exact method and property names before writing service logic or test fixtures.
- **Clean Markdown Formatting**: Always append journal entries using actual newline characters, never literal string escape sequences.
