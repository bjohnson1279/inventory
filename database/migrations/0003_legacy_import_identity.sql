-- Keep imported business fields until their repository mappings are adopted.
ALTER TABLE tenants ADD COLUMN source_metadata jsonb NOT NULL DEFAULT '{}';
ALTER TABLE users ADD COLUMN display_name text;
ALTER TABLE users ADD COLUMN source_metadata jsonb NOT NULL DEFAULT '{}';
ALTER TABLE locations ADD COLUMN source_metadata jsonb NOT NULL DEFAULT '{}';
ALTER TABLE products ADD COLUMN source_metadata jsonb NOT NULL DEFAULT '{}';
ALTER TABLE variants ADD COLUMN source_metadata jsonb NOT NULL DEFAULT '{}';
ALTER TABLE barcodes ADD COLUMN source_metadata jsonb NOT NULL DEFAULT '{}';
ALTER TABLE stock ADD COLUMN source_metadata jsonb NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS roles (
    tenant_id varchar(100) NOT NULL REFERENCES tenants(id),
    id varchar(100) NOT NULL,
    name text NOT NULL,
    source_metadata jsonb NOT NULL DEFAULT '{}',
    PRIMARY KEY (tenant_id, id)
);
CREATE TABLE IF NOT EXISTS permissions (
    tenant_id varchar(100) NOT NULL REFERENCES tenants(id),
    id varchar(255) NOT NULL,
    source_metadata jsonb NOT NULL DEFAULT '{}',
    PRIMARY KEY (tenant_id, id)
);
CREATE TABLE IF NOT EXISTS role_permissions (
    tenant_id varchar(100) NOT NULL,
    role_id varchar(100) NOT NULL,
    permission_id varchar(255) NOT NULL,
    source_metadata jsonb NOT NULL DEFAULT '{}',
    PRIMARY KEY (tenant_id, role_id, permission_id),
    FOREIGN KEY (tenant_id, role_id) REFERENCES roles(tenant_id, id),
    FOREIGN KEY (tenant_id, permission_id) REFERENCES permissions(tenant_id, id)
);
CREATE TABLE IF NOT EXISTS user_roles (
    tenant_id varchar(100) NOT NULL,
    user_id varchar(100) NOT NULL,
    role_id varchar(100) NOT NULL,
    source_metadata jsonb NOT NULL DEFAULT '{}',
    PRIMARY KEY (tenant_id, user_id, role_id),
    FOREIGN KEY (tenant_id, user_id) REFERENCES users(tenant_id, id),
    FOREIGN KEY (tenant_id, role_id) REFERENCES roles(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS import_rows (
    tenant_id varchar(100) NOT NULL REFERENCES tenants(id),
    source_id varchar(100) NOT NULL,
    source_table varchar(100) NOT NULL,
    source_key text NOT NULL,
    target_table varchar(100) NOT NULL,
    target_key jsonb NOT NULL,
    source_hash varchar(64) NOT NULL,
    target_hash varchar(64) NOT NULL,
    imported_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, source_id, source_table, source_key, target_table)
);

DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['roles','permissions','role_permissions','user_roles','import_rows'] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (tenant_id = current_setting(''inventory.tenant_id'', true)) WITH CHECK (tenant_id = current_setting(''inventory.tenant_id'', true))', table_name);
    END LOOP;
END $$;
