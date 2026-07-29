# Inventory Workspace Copilot Instructions

This workspace contains three separate inventory application implementations, each using a different technology stack and architecture style. Use this file as the primary context reference for Copilot in this workspace.

## Workspace overview

- Root folder: `c:\Users\johns\DEV\inventory`
- Contains three inventory apps:
  1. `gql-ddd-inventory`
  2. `js-ddd-inventory`
  3. `php-ddd-inventory`
- Each repo is a complete inventory application built around Domain-Driven Design (DDD) concepts.
- Do not assume a single shared codebase or common runtime; each folder is an independent implementation.

## Common domain context

All three applications implement an inventory domain with these shared themes:

- inventory stock management
- product/catalog and SKU modeling
- opening balance onboarding and count reconciliation
- multi-unit-of-measure (UOM) conversions
- kitting / SKU variance and bundle assembly
- serial number / lifecycle tracking
- accounting-ledger or cost-layer inventory accounting
- integration with external systems such as Shopify or webhook-driven sync

## Repository summaries

### 1. gql-ddd-inventory

- Stack: TypeScript, GraphQL, Apollo Server, Express, React frontend
- Key folders:
  - `src/` backend GraphQL server and DDD implementation
  - `web/` React administration dashboard
  - `prisma/` database schema and client
  - `plan/` DDD design documentation
- Important details:
  - Uses `@apollo/server`, GraphQL subscriptions, JWT authentication, Redis pub/sub patterns
  - Docker Compose support for Postgres/Timescale and frontend
  - Backend server runs from `npm run dev` and web client runs from `cd web && npm run dev`

### 2. js-ddd-inventory

- Stack: TypeScript, Express.js REST API, Prisma, webapp frontend
- Key folders:
  - `src/` separated into `application/`, `domain/`, `infrastructure/`
  - `webapp/` frontend app and UI
  - `prisma/` schema definitions
  - `plan/` design documentation and `API.md`
- Important details:
  - DDD architecture with ports/adapters and Prisma database adapter
  - Shopify sync and inventory setup experience via webapp
  - Docker Compose for TimescaleDB and app services
  - Common commands: `npm install`, `npm run dev`, `npm run test`

### 3. php-ddd-inventory

- Stack: PHP 8.1, Illuminate Database / Eloquent, PHPUnit, Docker Compose
- Key folders:
  - `src/` `Application/`, `Domain/`, `Infrastructure/`
  - `docs/` API docs and OpenAPI specification
  - `docker/` Postgres init scripts and container helpers
- Important details:
  - DDD example with both in-memory and Eloquent repository implementations
  - Unit and integration tests via PHPUnit
  - Docker workflow uses `docker compose up -d db` and `vendor/bin/phpunit`
  - API endpoints documented in `docs/ENDPOINTS.md`

## How to use this file

- When asked to make changes, first determine which of the three repos is the target.
- If the user does not specify a repo, ask for clarification before editing.
- Preserve the independence of each implementation and do not mix files across repo boundaries.
- Prefer repo-specific commands and architecture notes when editing or adding features.

## Helpful commands

### gql-ddd-inventory
```bash
cd gql-ddd-inventory
npm install
npx prisma generate
npm run dev
cd web
npm run dev
```

### js-ddd-inventory
```bash
cd js-ddd-inventory
npm install
npm run dev
npm run test
```

### php-ddd-inventory
```bash
cd php-ddd-inventory
composer install
docker compose up -d db
vendor/bin/phpunit
```

## Notes for Copilot

- This repository is intentionally multi-stack; do not unify code from one app into another unless the user explicitly asks to port features.
- When generating examples or commands, mention the specific repo folder.
- If the user asks for architecture comparisons or feature alignment, compare the three stacks explicitly.
