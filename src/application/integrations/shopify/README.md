# Shopify Integration Adapter (P1 — Priority)

This adapter handles synchronization with external sales channels per the omnichannel integration pattern defined in:
- `react-ddd-inventory-client/src/api/types.ts` (frontend types)
- `shared/src/api/integrations/types.ts` (backend contract)

## 1. Inventory Synchronization

**Goal**: Upsert product variants by SKU and handle low-stock threshold triggers.

**Behavior:**
- On startup: poll Shopify API for all stock levels at current prices
- On price change detection: re-sync variant pricing within the same day
- On low-stock alert (default 5 units): trigger fulfillment engine to attempt sales against alternative channels

**API call mapping:**
```typescript
// Input from Shopify REST API or GraphQL:
{ product_id, variants: [{ sku, inventory_quantity }] }

// Internal model conversion:
InventoryItem variant = new InventoryItem({
  variantId: sku,
  quantity: inventory_quantity,
  unitCostCents: priceInCents,
});
```

**Mapping logic:**
- If `variantId` on Shopify matches `sku` → direct upsert
- If `variantId` differs but `name` and `attributes` match → create new variant with mapping record

## 2. Order Ingestion from REST API / GraphQL

**Goal**: Parse external order data into the internal domain model.

**Mapping:**
```typescript
// External: { orderId, lineItems: [{ productId, quantity }] }
// Internal: { variantId, quantity } → JournalEntry (accrual method) → FulfillmentTask
```

**Steps:**
1. Map `productId` → `variantId` using the external mapping table
2. Create internal order with journal entry for stock allocation
3. Queue fulfillment task through the existing routing engine

## 3. Fulfillment Status Pushback

**Goal**: Update stock status and shipping information back to Shopify after warehouse processing completes.

**Triggers:**
- Order shipped → update `inventory_management.stock.available` in Shopify API
- Order delivered → set `inventory_management.stock.availability = 'in_stock'`
- Partial ship → update remaining quantity with appropriate status (shipped, pending)

## 4. Webhook Delivery to Shopify Events

Shopify pushes events to the registration endpoint:
- `orders/create` — incoming order ingestion
- `orders/shipping_status_update` — fulfillment tracking
- `orders/refunded` — create return/journal entry and restock
- `inventory/lowstock_threshold_reached` — trigger fulfillment engine for alternative channels

---

**Next step**: Implement the `DefaultShopifyIntegration` class with full API wrappers based on Shopify REST or GraphQL. Reference their documentation at https://shopify.dev/docs/api/http/rest-api/reference
