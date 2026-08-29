// --- Omnichannel Integration Types (Shared) ---

export interface ExternalMapping {
  id: string;
  externalId: string;
  internalId: string;
  entityType: 'Location' | 'Variant';
}

export interface WebhookSubscription {
  id: string;
  tenantId: string;
  url: string;
  eventTypes: string[];
}

// --- Backend Client Interfaces (Shared) ---
export interface InventoryClient {
  // Stock management
  getItems(tenantId: string): Promise<InventoryItem[]>;
  incrementForSaleBatch(tenantId: string, locationId: string, items: { variantId: string; quantity: number }[], memo?: string, actorId?: ActorId): Promise<void>;
  decrementForSaleBatch(tenantId: string, locationId: string, items: { variantId: string; quantity: number }[], referenceId: string, actorId: ActorId): Promise<void>;

  // ERP & Accounting
  getJournals(tenantId: string, dateFrom?: string, dateTo?: string): Promise<JournalEntry[]>;
  createJournalEntry(tenantId: string, date: string, description: string, lines: JournalLine[], method?: 'cash' | 'accrual', referenceId?: string): Promise<void>;

  // Serialized Items
  getSerializedItems(tenantId: string): Promise<SerializedItem[]>;
  traceSerial(tenantId: string, serialNumber: string): Promise<any>;

  // Real-time events (WebSocket)
  connectWsUrl: string;
  subscribe(topic: string): () => void;
  disconnect(): void;
}

// --- Shopify Integration Interface ---
export interface ShopifyConnection {
  id: string;
  domain: string;
  token: string;
  webhookUrl?: string;
  mapping?: ExternalMapping[];
}

/**
 * ShopifyIntegrationAdapter implements the channel adapter contract.
 */
interface ChannelAdapter<T extends Shopify | Amazon | WooCommerce> {
  syncInventory(channelId: string, onSyncProgress?: (progress: number) => void): Promise<void>;
  ingestOrder(orderData: any, mapping?: ExternalMapping): Order;
  pushFulfillmentStatus(orderId: string, status: 'pending' | 'shipped' | 'delivered'): Promise<void>;
}

export interface ShopifyIntegration {
  connect(domain: string, token: string, webhookUrl?: string);
  disconnect();
  getConnections(tenantId: string): Promise<ShopifyConnection[]>;
  createConnection(tenantId: string, domain: string, token: string, webhookUrl?: string): Promise<void>;
  syncInventory(connectionId: string, onSyncProgress?: (progress: number) => void): Promise<void>;
  
  // Order ingestion from Shopify REST API or GraphQL
  sendOrderToShopify(tenantId: string, connectionId: string, orderId: string, items: { variantId: string; quantity: number }[]): Promise<void>;

  // Webhook delivery to Shopify events (order created, shipped, delivered, refunded)
  subscribeEvents(tenantId: string, webhookUrl?: string): () => void;
}