# Omnichannel Integration Adapters

This directory contains adapter classes for synchronizing with external sales channels:

## Shopify Adapter (`ShopifyIntegration`)
- **Inventory Sync**: Upsert product variants by SKU, handle low-stock threshold triggers.
- **Order Ingestion**: Parse REST API / GraphQL order data into internal domain model.
- **Fulfillment Pushback**: Update stock status and shipping info back to Shopify after warehouse processing completes.

## Amazon SP-API Adapter (`AmazonIntegration`)  
- Inventory synchronization for multi-channel allocation.

## WooCommerce Adapter (`WooCommerceIntegration`)
- REST API adapter with inventory pool management across channels.

## Generic Channel Adapter Interface
All adapters implement:
```typescript
interface ChannelAdapter<T extends Shopify | Amazon | WooCommerce> {
  syncInventory(channelId: string, onSyncProgress: (progress: number) => void): Promise<void>;
  ingestOrder(orderData: any, mapping?: ExternalMapping): Order;
  pushFulfillmentStatus(orderId: string, status: 'pending' | 'shipped' | 'delivered'): Promise<void>;
}
```

See the omnichannel types in `react-ddd-inventory-client/src/api/types.ts`.
