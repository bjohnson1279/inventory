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

// --- Core Channel Types ---
export interface ChannelAllocation {
  id: string;
  channelId: string;
  variantId: string;
  allocatedQuantity: number;
}

export interface BaseChannelConnection {
  id: string;
  tenantId: string;
  channelType: 'shopify' | 'amazon' | 'woocommerce' | 'csv_edi';
  mapping?: ExternalMapping[];
}

export interface ShopifyConnection extends BaseChannelConnection {
  channelType: 'shopify';
  domain: string;
  token: string;
  webhookUrl?: string;
}

export interface AmazonConnection extends BaseChannelConnection {
  channelType: 'amazon';
  sellerId: string;
  mwsAuthToken: string;
  marketplaceId: string;
}

export interface WooCommerceConnection extends BaseChannelConnection {
  channelType: 'woocommerce';
  storeUrl: string;
  consumerKey: string;
  consumerSecret: string;
}

export interface CsvEdiConnection extends BaseChannelConnection {
  channelType: 'csv_edi';
  ftpHost?: string;
  ftpUser?: string;
  ftpPassword?: string;
  mappingFormat: string; // e.g., 'X12_850' or 'CUSTOM_CSV'
}

/**
 * BaseChannelAdapter implements the channel adapter contract.
 */
export interface BaseChannelAdapter<T extends BaseChannelConnection> {
  connect(connectionParams: Omit<T, 'id' | 'tenantId' | 'channelType'>): void;
  disconnect(): void;
  getConnections(tenantId: string): Promise<T[]>;
  createConnection(tenantId: string, params: Omit<T, 'id' | 'tenantId' | 'channelType'>): Promise<void>;
  
  syncInventory(connectionId: string, onSyncProgress?: (progress: number) => void): Promise<void>;
  ingestOrder(orderData: any, mapping?: ExternalMapping): any; // Should return an Order domain object
  pushFulfillmentStatus(orderId: string, status: 'pending' | 'shipped' | 'delivered'): Promise<void>;
  
  subscribeEvents(tenantId: string, webhookUrl?: string): () => void;
}