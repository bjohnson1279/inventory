#### 1. Backend Feature & Implementation Parity

• ~~Database Backup & Restore Helpers: Standardized compressed daily/weekly/monthly database snapshot automation
exists for PostgreSQL in gql-ddd-inventory/infra/db/ but has not been ported to the js-ddd-inventory (Express)
or php-ddd-inventory (Laravel) infrastructure.~~ (Completed)
• ~~Kafka & Outbox Worker Integration: The Laravel backend (README.md) features distributed Kafka messaging and
a dedicated background outbox worker. The TypeScript backends use local listeners / event-emitters or in-memory
publish-subscribe patterns and need parity for high-scale environments.~~ (Completed)
• ~~Row-Level Security (RLS): Multi-tenant database RLS is fully configured on PostgreSQL in the Laravel/PHP app, but
hasn't been adapted for the Express/Prisma and GraphQL/Prisma setups.~~ (Completed)

#### 2. Architecture & Code Health Refactoring

• ~~Concrete Domain Events in PHP: As noted in the PHP README.md, domain events in the PHP app currently use
lightweight placeholder types. These need to be refactored into concrete classes and paired with an event-
dispatcher pipeline.~~ (Completed)
• ~~UUID Generation Library in PHP: PHP integration tests rely on an internal utility for generating mock UUIDs; this
should be updated to a robust community library like ramsey/uuid .~~ (Completed)
• ~~Performance Optimization Porting: Several N+1 bottlenecks and spatial/memory allocation issues (like caching
spread arrays on getters or converting sequential Promise.all fallbacks to batch transactions) have been
implemented dynamically in Express/Prisma, but need to be systematically audited and ported to the GraphQL and
Laravel repository codebases.~~ (Completed)

#### 3. Frontend Consolidation

• ~~Deprecated Frontend Codebases: While the new unified App.tsx handles all 3 backends, legacy independent
frontends still exist in js-ddd-inventory/webapp/ and php-ddd-inventory/frontend/ . Deleting these folders and
fully relying on the centralized client remains to be finalized.~~ (Completed)

#### 4. Advanced Domain Features & Observability

• ~~**Distributed Tracing & Observability Parity**: Integrate OpenTelemetry to correlate and trace actions (like stock updates, Kafka outbox events, and accounting mappings) across the GraphQL, Express, and PHP backends.~~ (Completed)
• ~~**Plug-and-Play Costing Strategies**: Implement a domain-layer strategy pattern to support LIFO and WAC (Weighted Average Cost) costing methods in addition to FIFO.~~ (Completed)
• ~~**Intelligent Multi-Location Order Routing**: Build a warehouse routing engine optimizing splits, shipping fees, and location distance.~~ (Completed)
• ~~**Dynamic Reorder Point (ROP) Tuning**: Implement automated ROP calculations based on sales velocity and lead-time variance.~~ (Completed)
• ~~**Auto-Retry Use Case Decorator**: Intercept version-based `ConcurrencyException` failures and automatically retry command execution with exponential backoff.~~ (Completed)
• ~~**Outbound Webhook Delivery Engine**: Build webhook subscription, payload signing, and retry queues for tenant-facing integrations.~~ (Completed)

#### 5. Enterprise Scaling & Predictive Systems

• ~~**Real-Time Collaborative UI via WebSocket Event Sync**: Transition unified client to react immediately to backend WebSocket events (stock changes, discrepancy updates, webhook delivery issues).~~ (Completed)
• ~~**Interactive 2D Warehouse Bin Map & Heat Visualizer**: Design spatial warehouse visualization in UI highlighting capacity metrics and drawing optimized pick routing paths.~~ (Completed)
• ~~**Machine Learning-Based Demand Forecasting**: Upgrade reorder point calculations with seasonal forecasting algorithms and automated draft Purchase Order creation.~~ (Completed)
• ~~**Cryptographically Signed Compliance Ledger**: Add an immutable event-sourced audit trail securing inventory transactions with cryptographic hash chaining.~~ (Completed)
• ~~**Offline Barcode Buffer & Sync (PWA)**: Implement PWA and IndexedDB support to buffer scan items locally in industrial network dead zones and sync on connection recovery.~~ (Completed)

#### 6. High-Scale Cloud & Autonomous Systems

• ~~**Dynamic Multi-Database Tenant Provisioning (SaaS)**: Move beyond shared-database Row Level Security (RLS) to support runtime database/schema partitioning per tenant.~~ (Completed)
• ~~**Federated GraphQL Gateway**: Subgraph-based architecture (Apollo Federation) dividing Domain contexts (Inventory, Catalog, Accounting) into standalone microservices.~~ (Completed)
• ~~**AI-Driven Slotting Optimization**: Automatically analyze grid coordinate maps and seasonal sales aggregates to recommend relocations of high-velocity items closer to dispatch areas.~~ (Completed)
• ~~**RFID Bulk Scanning & IoT Integrations**: Integrate event brokers with IoT endpoints to ingest thousands of serial number check-ins simultaneously without UI latency.~~ (Completed)
• ~~**Multi-Region Active-Active Replication & Conflict Resolution**: Strategies and schemas for geo-distributed database clusters utilizing conflict-free replicated data types (CRDTs).~~ (Completed)
• ~~**Autonomous Inventory Management**: Implement an autonomous agentic inventory rebalancing and purchase order engine driven by predictive stockout risk, lead-time variance, and automated supplier workflows.~~ (Completed)

#### 7. Enterprise Supply Chain & Operational Resilience

• ~~**Lot Expiration, FEFO Quarantine & Automated Recall Engine**: Traceability engine with serial lot tracking, expiration enforcement (FEFO), automated lot quarantine, and recall notification pipelines across all 3 backends.~~ (Completed)
• ~~**Dynamic Cross-Docking & Direct Supplier Fulfillment Routing**: Direct transfer from inbound receiving docks to outbound dispatch bays bypassing warehouse bin put-away, and third-party supplier drop-ship routing logic.~~ (Completed)


#### 8. Cross-Backend Conformance & Developer Experience

• ~~**Polyglot Cross-Backend Conformance Test Suite**: Unified black-box integration test runner verifying 100% functional and behavioral parity across GraphQL, Express REST, and PHP REST backends.~~ (Completed)
• ~~**Automated OpenAPI & GraphQL Schema Specification Synchronizer**: Automated generator and schema linting tool keeping OpenAPI 3.0 specs and GraphQL IDL definitions in sync with zero drift.~~ (Completed)

#### 9. AI & Intelligent Automation

• ~~**AI Inventory Anomaly & Shrinkage Detection Engine**: Machine learning model in Python sidecar analyzing stock adjustments, cycle counts, and scan timestamps to flag inventory theft, damage, or data entry errors.~~ (Completed)
• ~~**Multi-Warehouse Rebalancing Optimization Matrix**: Smart rebalancing algorithm calculating inter-warehouse transfers based on regional demand spikes, lead times, and shipping costs.~~ (Completed)

#### 10. Platform Resiliency & Event Sourcing

• ~~**Event-Sourced Point-in-Time State Reconstruction & Audit Replay**: Reconstruct historical stock levels, bin configurations, and account balances as of any exact timestamp using the cryptographic ledger.~~ (Completed)
• ~~**Tier-2 Distributed Redis Cache with Outbox Invalidation**: High-performance caching layer in front of DB repositories with pub/sub cache invalidation driven by transactional outbox events.~~ (Completed)