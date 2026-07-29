# Repository Architecture Summary

This repository contains three independent implementations of an inventory management system, all based on a common set of Domain-Driven Design (DDD) plans. They serve as a comparative study for implementing the same business logic using different technologies and architectural styles.

## Shared Design

All three projects originate from the same detailed design documents found in the `plan/` directory of each project. These documents outline the core business concepts like accounting, barcode modeling, and product management.

## `gql-ddd-inventory` (GraphQL & TypeScript)

*   **Purpose:** A comprehensive implementation featuring a **GraphQL API**.
*   **Technology:** Built with TypeScript, Node.js, Express, and Apollo Server. It uses Prisma as its ORM for a PostgreSQL database.
*   **Architecture:** Follows a layered DDD architecture where the `domain` logic is organized by component type (e.g., entities, services, repositories). It also includes a React-based admin dashboard in the `web/` sub-directory.

## `js-ddd-inventory` (REST & TypeScript)

*   **Purpose:** An alternative implementation providing a traditional **REST API**.
*   **Technology:** Also uses TypeScript, Node.js, and Express with Prisma.
*   **Architecture:** Its key distinction is that its `domain` layer is organized by "bounded contexts" (e.g., `product`, `kit`, `accounting`), which represent different areas of the business. This showcases a different approach to structuring the core logic compared to the GraphQL project.

## `php-ddd-inventory` (REST & PHP)

*   **Purpose:** A more focused, educational example built with **PHP**.
*   **Technology:** Uses standard PHP without a full framework, but incorporates standalone components like the Eloquent ORM (from Laravel).
*   **Architecture:** It provides a very clear example of a hexagonal (or "ports and adapters") architecture, with swappable in-memory and database repository implementations.

In short, the repository is a practical exploration of architectural patterns, demonstrating how a single, complex domain can be modeled and built in different ways.