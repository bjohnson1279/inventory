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

#### 11. Enterprise Logistics, Hardware & Intelligence Extensions

• ~~**Enterprise Logistics & ERP Integrations Framework**: Carrier shipping rate calculation, shipping label / BOL generation (FedEx, UPS, DHL, LTL), and 2-way sync adapters for QuickBooks, NetSuite, and Xero journal postings.~~ (Completed)
• ~~**Reverse Logistics & Supplier Portal Workflow**: Customer RMA returns inspection, quality grading (Restock, Refurbish, Scrap), and supplier ASN / OTIF performance scorecard portal.~~ (Completed)
• ~~**Thermal Printing & AR-Guided Operations**: Direct ZPL/TSPL thermal printing engine for bin/lot tags and WebXR/AR visual pick-and-pack guidance.~~ (Completed)
• ~~**Warehouse Digital Twin & Conversational AI Copilot**: Discrete-event scenario simulator for stress-testing fulfillment strategies and LLM-powered natural language warehouse metrics assistant.~~ (Completed)
• ~~**ESG Carbon Footprint & Scope 1-3 Emissions Tracking**: Transport mode and warehouse energy carbon emissions calculator for regulatory ESG sustainability reporting.~~ (Completed)

---

#### 12. Governance & Access Control 🔴 P0

• ~~**Granular Role-Based Access Control (RBAC) & Permission Engine**: Permission matrix (resource × action × scope), predefined role templates (warehouse_operator, inventory_manager, finance_auditor, admin, read_only), JWT claims enrichment with permissions array, middleware/guard decorators across all 3 backends, and a UI role management panel with permission toggles.~~ (Completed)
• ~~**Configurable Approval Workflows Engine**: Generic workflow engine defining trigger event → approval chain → escalation timeout → execution. Pre-built templates for PO approval (by $ threshold), stock adjustment sign-off, write-off dual authorization, and RMA disposition review. UI pending approvals inbox, approval history timeline, and webhook/outbox integration for external approval tools.~~ (Completed)

#### 13. Reporting & Analytics 🟠 P1

• **Reporting, Saved Views & Export Engine**: Saved report definitions (filters, date range, grouping) stored per-tenant. Scheduled report generation (daily/weekly/monthly) via cron + outbox. Export formats: CSV, PDF (branded templates), Excel (XLSX). Report sharing with expiry and viewer permissions. Dashboard builder for custom KPI widget layouts. *(Completed in js-ddd-inventory)*

#### 14. Ecosystem & Channel Integrations 🟠 P1

• ~~**Omnichannel Sales Integration Framework**: Generalized channel adapter interface (sync_inventory, ingest_orders, push_fulfillment_status). Adapters for Shopify (upgrade from stub), Amazon SP-API, WooCommerce REST, and generic CSV/EDI. Channel-specific inventory allocation pools, centralized order ingestion feeding the existing fulfillment routing engine, and oversell conflict resolution across channels.~~ *(Completed in js-ddd-inventory)*

#### 15. Operational Depth 🟡 P2

• **Advanced Cycle Count Program Management**: ABC classification-based frequency scheduling, zone/aisle/bin-based count assignments, blind count mode, variance thresholds triggering automatic recounts, count accuracy KPIs per operator/zone/SKU class, and mobile-first count entry extending the existing PWA/offline capability.
• **Supplier Collaboration Portal & ASN/OTIF Expansion**: Supplier-facing portal with separate auth and tenant scoping, electronic ASN submission with PO matching, PO acknowledgment and ship-date commitment workflows, supplier performance dashboard (OTIF %, lead time variance, defect rate), and recall collaboration tracking.
• **Notification Center & Alert Management**: Unified notification aggregator across all alert sources (low-stock, anomalies, rebalance, webhook failures), in-app notification bell with categorized inbox, per-user notification preferences (email, in-app, webhook, SMS), snooze/acknowledge/escalate workflows, and notification history with search and filtering.
• **Inventory Aging & Dead Stock Analysis**: Aging buckets (0–30d, 31–60d, 61–90d, 91–180d, 180d+), dead stock identification (zero-velocity for configurable period), overstock detection vs. projected demand, markdown/liquidation recommendation engine, and integration with ESG module for dead stock waste as Scope 3 emissions.

#### 16. Financial & Platform Maturity 🟢 P3

• **Intercompany & Multi-Entity Transfer Accounting**: Entity/legal-entity layer above tenant, intercompany transfer pricing rules (cost-plus, market-based), automatic intercompany elimination journal entries, transfer duty/tariff recording for cross-border movements, and consolidation reports across entities.
• **API Rate Limiting, Usage Metering & Tenant Billing Hooks**: Per-tenant rate limiting (sliding window, token bucket), API usage metering (requests/day, storage, active SKUs, active locations), usage dashboard per tenant, billing event hooks (outbox events for Stripe/billing system ingestion), and configurable tier limits.