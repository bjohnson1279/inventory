-- Canonical storage foundation. Names resolve inside the runner-selected schema.
CREATE TABLE IF NOT EXISTS tenants (
    id varchar(100) PRIMARY KEY,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    tenant_id varchar(100) NOT NULL REFERENCES tenants(id),
    id varchar(100) NOT NULL,
    email text NOT NULL CHECK (email = lower(btrim(email)) AND length(email) > 0),
    password_hash text NOT NULL,
    role text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, email)
);

CREATE TABLE IF NOT EXISTS locations (
    tenant_id varchar(100) NOT NULL REFERENCES tenants(id),
    id varchar(100) NOT NULL,
    name text NOT NULL,
    PRIMARY KEY (tenant_id, id)
);

-- A product is a parent; a variant is the sellable SKU, including single-SKU products.
CREATE TABLE IF NOT EXISTS products (
    tenant_id varchar(100) NOT NULL REFERENCES tenants(id),
    id varchar(100) NOT NULL,
    name text NOT NULL,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id)
);

CREATE TABLE IF NOT EXISTS variants (
    tenant_id varchar(100) NOT NULL,
    id varchar(100) NOT NULL,
    product_id varchar(100) NOT NULL,
    sku varchar(100) NOT NULL,
    name text NOT NULL,
    base_unit varchar(32) NOT NULL DEFAULT 'each',
    price_cents bigint NOT NULL DEFAULT 0 CHECK (price_cents BETWEEN 0 AND 9007199254740991),
    currency varchar(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, sku),
    FOREIGN KEY (tenant_id, product_id) REFERENCES products(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS barcodes (
    tenant_id varchar(100) NOT NULL,
    value varchar(255) NOT NULL,
    variant_id varchar(100) NOT NULL,
    is_primary boolean NOT NULL DEFAULT false,
    PRIMARY KEY (tenant_id, value),
    FOREIGN KEY (tenant_id, variant_id) REFERENCES variants(tenant_id, id)
);
CREATE UNIQUE INDEX IF NOT EXISTS barcodes_one_primary ON barcodes (tenant_id, variant_id) WHERE is_primary;

-- Quantities are base units; decimal precision supports fractional units of measure.
CREATE TABLE IF NOT EXISTS stock (
    tenant_id varchar(100) NOT NULL,
    variant_id varchar(100) NOT NULL,
    location_id varchar(100) NOT NULL,
    quantity numeric(20,6) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    allocated numeric(20,6) NOT NULL DEFAULT 0 CHECK (allocated >= 0 AND allocated <= quantity),
    in_transit numeric(20,6) NOT NULL DEFAULT 0 CHECK (in_transit >= 0),
    version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
    PRIMARY KEY (tenant_id, variant_id, location_id),
    FOREIGN KEY (tenant_id, variant_id) REFERENCES variants(tenant_id, id),
    FOREIGN KEY (tenant_id, location_id) REFERENCES locations(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
    tenant_id varchar(100) NOT NULL,
    id varchar(100) NOT NULL,
    mutation_id varchar(100) NOT NULL,
    variant_id varchar(100) NOT NULL,
    location_id varchar(100) NOT NULL,
    quantity_delta numeric(20,6) NOT NULL,
    reason text NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, mutation_id),
    FOREIGN KEY (tenant_id, variant_id, location_id) REFERENCES stock(tenant_id, variant_id, location_id)
);

-- Every request/worker transaction must SET LOCAL inventory.tenant_id.
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tenants USING (id = current_setting('inventory.tenant_id', true)) WITH CHECK (id = current_setting('inventory.tenant_id', true));
DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['users','locations','products','variants','barcodes','stock','stock_movements'] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (tenant_id = current_setting(''inventory.tenant_id'', true)) WITH CHECK (tenant_id = current_setting(''inventory.tenant_id'', true))', table_name);
    END LOOP;
END $$;
