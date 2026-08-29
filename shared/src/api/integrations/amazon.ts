// --- Amazon SP-API Integration Interface (P1) ---

/**
 * Amazon Selling Partner API connection.
 */
export interface AmazonConnection {
  id: string;
  tenantId: string;
  accessToken: string;
  apiVersion: string; // '2018-03-16' for inventory sync, '2021-12-04' for orders
  mapping?: ExternalMapping[];
}

/**
 * AmazonSellingPartnerApiInventoryInterface — Inventory synchronization.
 */
interface AmazonInventorySync {
  /** List all items with current stock levels (2018-03-16 API). */
  listItems(input: { marketplace: string }): Promise<AmazonItem[]>;
  
  /** Update inventory level for a specific SKU. */
  updateInventoryLevel(
    itemId: string,
    quantity: number,
  ): Promise<void>;

  /** Apply low-stock threshold to trigger fulfillment engine. */
  applyLowStockThreshold(itemId: string, thresholdUnits: number): Promise<void>;
}

/**
 * AmazonSellingPartnerApiOrdersInterface — Order ingestion from AWS.
 */
interface AmazonOrderIngestion {
  /** Get orders by status filter. */
  listOrders(
    input: {
      marketplace: string;
      dateFrom?: string; // ISO8601
      status: 'NEW' | 'PROCESSING' | 'SHIPPED' | 'DELIVERED' | 'RETURNED',
    },
  ): Promise<AmazonOrder[]>;

  /** Map order to internal model using external mapping. */
  createFromOrder(
    amazonOrderId: string,
    mapping: ExternalMapping | null,
  ): Order;
}

/**
 * AmazonSellingPartnerApiFulfillmentInterface — Fulfillment status pushback.
 */
interface AmazonFulfillmentPushback {
  /** Update order shipment status after warehouse processing completes. */
  updateOrderStatus(amazonOrderId: string, status: 'pending' | 'shipped' | 'delivered'): Promise<void>;

  /** Create label with shipping address and tracking number. */
  createLabel(
    amazonOrderId: string,
    shipperInfo: { name: string; address: string; city: string; state: string; zip: string; country: string },
    trackingNumber?: string,
  ): Promise<{ url: string }>;
}

/** Amazon item type with inventory level. */
interface AmazonItem {
  itemId: string;
  quantityAvailable: number;
  sku: string;
  price: number; // USD
}

/** Amazon order from the AWS API. */
interface AmazonOrder {
  orderId: string;
  dateOrdered: string;
  lineItems: {
    quantitySolded: number;
    shippingAddress: { address1?: string; city: string; state: string; zip: string; countryCode: string };
  }[];
}

/**
 * AmazonSellingPartnerApiWebhookInterface — Webhook delivery to AWS.
 */
interface AmazonWebhookDelivery {
  /** Register webhook URL for order events. */
  createWebhookUrl(input: { url: string }): Promise<void>;
  
  /** Remove webhook URL. */
  removeWebhookUrl(amazonOrderId: string): Promise<void>;
}

/**
 * Combined Amazon Integration Interface (P1 implementation pattern).
 */
export interface AmazonIntegration {
  connect(marketplaceId: string, accessToken: string, apiVersion?: string): void;
  disconnect(): void;

  syncInventory(connectionId: string): Promise<void>;
  sendOrderToAmazon(connectionId: string, orderId: string): Promise<void>;
  
  subscribeEvents(tenantId: string, webhookUrl?: string): () => void;
}