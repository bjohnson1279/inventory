// --- WooCommerce Integration Interface (P1) ---

/** WooCommerce REST API connection. */
export interface WooCommerceConnection {
  id: string;
  tenantId: string;
  url: string; // e.g., https://mystore.myshopify.com/api/v3.0
  apiKey: string;
  mapping?: ExternalMapping[];
}

/** Inventory sync via REST API (POST /products). */
interface WooCommerceInventorySync {
  /** Upsert variant by SKU — handles existing and new SKUs. */
  upsertVariant(
    url: string,
    apiKey: string,
    data: { sku: string; priceCents: number; quantityAvailable: number },
  ): Promise<void>;

  /** Bulk update stock levels with low-stock threshold trigger. */
  applyLowStockThreshold(url: string, apiKey: string, thresholdUnits: number): Promise<void>;
}

/** Order ingestion from WooCommerce REST API (GET /products/order). */
interface WooCommerceOrderIngestion {
  /** List orders by date range and status filter. */
  listOrders(
    url: string,
    apiKey: string,
    options: { dateFrom?: string; dateTo?: string; status?: 'pending' | 'processing' | 'completed' },
  ): Promise<WooCommerceOrder[]>;

  /** Map order to internal model using external mapping. */
  createFromOrder(
    url: string,
    apiKey: string,
    orderId: string,
    mapping: ExternalMapping | null,
  ): Order;
}

/** Fulfillment status pushback via WooCommerce REST API (PATCH /products/order). */
interface WooCommerceFulfillmentPushback {
  /** Update order shipment status after warehouse processing. */
  updateOrderStatus(
    url: string,
    apiKey: string,
    orderId: string,
    status: 'pending' | 'shipped' | 'delivered',
  ): Promise<void>;

  /** Create shipping label and return tracking URL. */
  createLabel(
    url: string,
    apiKey: string,
    orderId: string,
    shipperInfo: { name: string; address?: string; city: string; state: string; zip: string; country: string },
  ): Promise<{ trackingNumber: string; labelUrl: string }>;
}

/** WooCommerce order from REST API. */
interface WooCommerceOrder {
  id: number;
  dateCreated: string; // ISO8601 timestamp
  lineItems: { quantitySolded: number; shippingAddress?: { address1?: string; city: string; state: string; zip: string; country: string } }[];
}

/** Webhook registration to WooCommerce REST API (POST /rest/woocommerce/v1/hooks). */
interface WooCommerceWebhookDelivery {
  /** Register webhook URL for order events. */
  createWebhookUrl(url: string): Promise<void>;
  
  /** Remove webhook URL. */
  removeWebhookUrl(orderId: number): Promise<void>;
}

/** Combined WooCommerce Integration Interface (P1 implementation pattern). */
export interface WooCommerceIntegration {
  connect(
    url: string,
    apiKey: string,
  ): void;
  disconnect(): void;

  syncInventory(connectionId: string): Promise<void>;
  sendOrderToWooCommerce(connectionId: string, orderId: string): Promise<void>;

  subscribeEvents(tenantId: string, webhookUrl?: string): () => void;
}