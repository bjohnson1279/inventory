// Shopify Integration Adapter (P1 — implement first)
// Based on the omnichannel types defined in:
//   react-ddd-inventory-client/src/api/types.ts
//   shared/src/api/integrations/types.ts

import { InventoryClient } from '../../api/InventoryClient';
import type { ExternalMapping, ShopifyConnection } from '../../api/integrations/types';

export interface ShopifyIntegration {
  connect(domain: string, token: string, webhookUrl?: string): void;
  disconnect(): void;
  getConnections(tenantId: string): Promise<ShopifyConnection[]>;
  createConnection(
    tenantId: string,
    domain: string,
    token: string,
    webhookUrl?: string,
  ): Promise<void>;

  // Inventory synchronization — upsert variants by SKU
  syncInventory(connectionId: string, onSyncProgress?: (progress: number) => void): Promise<void>;

  // Order ingestion from Shopify REST API or GraphQL
  sendOrderToShopify(
    tenantId: string,
    connectionId: string,
    orderId: string,
    items: { variantId: string; quantity: number }[],
  ): Promise<void>;

  // Webhook delivery to Shopify events (order created, shipped, delivered, refunded)
  subscribeEvents(tenantId: string, webhookUrl?: string): () => void;
}

// --- Internal Implementation (TODO — fill in based on API docs) ---

export class DefaultShopifyIntegration implements ShopifyIntegration {
  private _tenantInventoryClient: InventoryClient = null!;

  constructor(inventoryClient: InventoryClient) {
    this._tenantInventoryClient = inventoryClient;
  }

  connect(domain: string, token: string, webhookUrl?: string): void {
    // TODO: Store connection credentials securely (env + vault)
    // TODO: Initialize Shopify API client or GraphQL endpoint session
    console.log(`Shopify connected to ${domain}`);
  }

  async disconnect(): Promise<void> {
    // TODO: Clear API token/session from memory
    this._tenantInventoryClient = null!;
    console.log('Disconnected from Shopify');
  }

  async getConnections(tenantId: string): Promise<ShopifyConnection[]> {
    const items = await this._tenantInventoryClient.getItems(tenantId);
    // TODO: Map domain -> Shopify API token for each tenant
    return items.map(item => ({ id: item.variantId, domain: 'shopify', token: 'placeholder' }));
  }

  async createConnection(
    tenantId: string,
    domain: string,
    token: string,
    webhookUrl?: string,
  ): Promise<void> {
    // TODO: Create connection in database + initialize API session
    this._tenantInventoryClient = null!;
  }

  async syncInventory(
    channelId: string,
    onSyncProgress?: (progress: number) => void,
  ): Promise<void> {
    // TODO: Query Shopify stock levels by variant and upsert into InventoryItem table
    const progress = Math.round((synced / total) * 100);
    if (onSyncProgress && progress !== undefined) {
      onSyncProgress(progress);
    }
  }

  async sendOrderToShopify(
    tenantId: string,
    channelId: string,
    orderId: string,
    items: { variantId: string; quantity: number }[],
  ): Promise<void> {
    // TODO: Create order in Shopify using REST API or GraphQL mutation
    // Reference the existing fulfillment routing engine for allocation logic
  }

  subscribeEvents(tenantId: string, webhookUrl?: string): () => void {
    // TODO: Register webhook endpoint on Shopify that pushes events to this app's queue
    return () => {};
  }
}

// --- Routing Pattern (TODO — integrate with existing infrastructure) ---
/**
 * When an order event arrives from a webhook, route it through:
 * 1. Queue the event for replay if delivery failed
 * 2. Map the external order to internal domain model using ExternalMapping
 * 3. Create JournalEntry for stock allocation (cash/accrual method)
 * 4. Push fulfillment status back to Shopify via sendOrderToShopify()
 */
