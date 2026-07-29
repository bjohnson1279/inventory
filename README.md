# Polyglot Inventory Management DDD Study

An enterprise-grade, multi-backend Domain-Driven Design (DDD) comparative architecture study. This repository orchestrates multiple independent backend implementations, a React single-page application client, an AI/ML FastAPI microservice sidecar, and a black-box cross-backend conformance test suite.

---

## 🏛️ Architecture Overview

The system models a complex warehouse inventory domain featuring multi-tenancy, transactional outbox event streams, FEFO lot expiration, serial lifecycles, and AI-driven warehouse slotting optimization.

```
                                  +------------------------------+
                                  |  react-ddd-inventory-client  |
                                  +--------------+---------------+
                                                 |
                       +-------------------------+-------------------------+
                       |                         |                         |
                       v                         v                         v
            +--------------------+    +--------------------+    +--------------------+
            |  gql-ddd-inventory |    |  js-ddd-inventory  |    |  php-ddd-inventory |
            |  (GraphQL / TS)    |    |  (Express REST / TS|    |  (Hexagonal / PHP) |
            +----------+---------+    +----------+---------+    +----------+---------+
                       |                         |                         |
                       +-------------------------+-------------------------+
                                                 |
                                                 v
                                 +-------------------------------+
                                 |   inventory-python-sidecar    |
                                 | (FastAPI 3D Slotting & AI)    |
                                 +-------------------------------+
```

---

## 📦 Submodule Ecosystem

This parent repository links five standalone Git repositories as submodules:

| Submodule | Technology Stack | Architecture Pattern | Key Features |
| :--- | :--- | :--- | :--- |
| **[gql-ddd-inventory](https://github.com/bjohnson1279/gql-ddd-inventory)** | TypeScript, Node.js, Express, Apollo Server, Prisma, PostgreSQL | Layered DDD / Subgraph Federation | GraphQL API, Apollo Federation v2, Prisma ORM |
| **[js-ddd-inventory](https://github.com/bjohnson1279/js-ddd-inventory)** | TypeScript, Node.js, Express, Prisma, PostgreSQL | Bounded Context DDD | REST API, Bounded Context module structure |
| **[php-ddd-inventory](https://github.com/bjohnson1279/php-ddd-inventory)** | PHP 8.2, Eloquent ORM, TimescaleDB, Mosquitto MQTT | Hexagonal (Ports & Adapters) | Pure PHP Hexagonal architecture, TimescaleDB ledgers |
| **[react-ddd-inventory-client](https://github.com/bjohnson1279/react-ddd-inventory-client)** | React, TypeScript, Vite, TailwindCSS | SPA Client | Multi-backend admin dashboard & developer panels |
| **[inventory-python-sidecar](https://github.com/bjohnson1279/inventory-python-sidecar)** | Python 3.11, FastAPI, NumPy, SciPy | Microservice Sidecar | 3D Manhattan distance slotting & ML shrinkage detection |

---

## 🚀 Quick Start

### 1. Clone with Submodules

To clone the entire repository along with all 5 submodules:

```bash
git clone --recursive https://github.com/bjohnson1279/inventory.git
cd inventory
```

If you already cloned without `--recursive`, initialize and pull the submodules:

```bash
git submodule update --init --recursive
```

---

## 🧪 Cross-Backend Conformance Test Suite

The repository includes an automated pytest-based black-box conformance test suite ([docker-compose.conformance.yml](docker-compose.conformance.yml)) that runs identical test vectors against all three backend variants to verify 100% behavioral, API payload, and error parity.

### Run Conformance Tests via Docker Compose

```bash
docker-compose -f docker-compose.conformance.yml up --build --exit-code-from conformance-runner
```

The conformance suite verifies:
* **Inventory CRUD & Allocations**: Stock receiving, dispatches, reservations, and backorders.
* **Lot Expiration & FEFO Recalls**: First-Expired-First-Out picking logic and lot quarantine.
* **Serial Item Lifecycles**: Serialized barcode registration, state transitions, and audit logs.
* **Kit Assembly & Disassembly**: Bill of Materials (BOM) explosion and multi-component stock checks.
* **Warehouse Slotting Optimization**: 3D grid spatial layout and travel-distance minimization via Python sidecar.
* **Cryptographic Compliance Ledger**: Sequence numbering, SHA-256 hash chains, and tamper verification.

---

## 📑 Core Documentation

* 📜 **[Architecture Summary](ARCHITECTURE_SUMMARY.md)**: In-depth comparison of the DDD patterns used across GraphQL, Express, and PHP backends.
* 🗺️ **[Feature Roadmap](roadmap.md)**: Active and completed features across domain components, resilience patterns, and AI automation.

---

## 🔄 Updating Submodules

To pull the latest updates across all submodules simultaneously:

```bash
git submodule update --remote --merge
```

---

## 📜 License

This comparative DDD study is open source under the MIT License.
