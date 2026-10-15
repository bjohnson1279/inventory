CREATE TABLE IF NOT EXISTS journals (
    tenant_id varchar(100) NOT NULL REFERENCES tenants(id),
    id varchar(100) NOT NULL,
    number bigint NOT NULL CHECK (number BETWEEN 1 AND 9007199254740991),
    entry_date date NOT NULL,
    description text NOT NULL,
    accounting_method text NOT NULL CHECK (accounting_method IN ('CASH','ACCRUAL')),
    currency varchar(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    status text NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','POSTED')),
    source_id varchar(100),
    reversal_of varchar(100),
    reference_id varchar(100),
    actor_id varchar(100) NOT NULL,
    kind text NOT NULL CHECK (kind IN ('MANUAL','REVERSAL','INVENTORY','OPENING','SOURCE_RESOLUTION','DOCUMENT','SETTLEMENT','CREDIT','REFUND')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, number),
    UNIQUE (tenant_id, source_id),
    UNIQUE (tenant_id, reversal_of),
    FOREIGN KEY (tenant_id, reversal_of) REFERENCES journals(tenant_id, id),
    CHECK (reversal_of IS NULL OR reversal_of <> id)
);
CREATE TABLE IF NOT EXISTS journal_lines (
    tenant_id varchar(100) NOT NULL,
    id varchar(100) NOT NULL,
    journal_id varchar(100) NOT NULL,
    account_code varchar(100) NOT NULL,
    account_name text NOT NULL,
    account_category text NOT NULL,
    side text NOT NULL CHECK (side IN ('DEBIT','CREDIT')),
    amount_cents bigint NOT NULL CHECK (amount_cents BETWEEN 1 AND 9007199254740991),
    memo text,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, journal_id) REFERENCES journals(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS journal_lines_journal ON journal_lines (tenant_id, journal_id);

-- Deferred checks allow header + lines to be written atomically in either order.
-- Resolve storage by trigger schema, never a caller-controlled search_path.
CREATE FUNCTION enforce_journal_balance() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target record; posted boolean; line_count bigint; balance numeric; total_debits numeric;
BEGIN
    FOR target IN SELECT DISTINCT tenant_id, journal_id FROM (
        SELECT CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW)->>'tenant_id' END AS tenant_id,
               CASE WHEN TG_OP <> 'DELETE' THEN COALESCE(to_jsonb(NEW)->>'journal_id', to_jsonb(NEW)->>'id') END AS journal_id
        UNION ALL
        SELECT CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD)->>'tenant_id' END,
               CASE WHEN TG_OP <> 'INSERT' THEN COALESCE(to_jsonb(OLD)->>'journal_id', to_jsonb(OLD)->>'id') END
    ) affected WHERE tenant_id IS NOT NULL LOOP
        EXECUTE format('SELECT status = ''POSTED'' FROM %I.journals WHERE tenant_id = $1 AND id = $2', TG_TABLE_SCHEMA)
            INTO posted USING target.tenant_id, target.journal_id;
        IF posted THEN
            EXECUTE format('SELECT count(*), COALESCE(sum(CASE side WHEN ''DEBIT'' THEN amount_cents ELSE -amount_cents END),0), COALESCE(sum(amount_cents) FILTER (WHERE side = ''DEBIT''),0) FROM %I.journal_lines WHERE tenant_id = $1 AND journal_id = $2', TG_TABLE_SCHEMA)
                INTO line_count, balance, total_debits USING target.tenant_id, target.journal_id;
            IF line_count < 2 OR line_count > 100 OR balance <> 0 OR total_debits > 9007199254740991 THEN
                RAISE EXCEPTION 'Posted journal must contain balanced debit and credit lines' USING ERRCODE = '23514';
            END IF;
        END IF;
    END LOOP;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER journals_balance AFTER INSERT OR UPDATE ON journals DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION enforce_journal_balance();
CREATE CONSTRAINT TRIGGER journal_lines_balance AFTER INSERT OR UPDATE OR DELETE ON journal_lines DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION enforce_journal_balance();

-- Assemble DRAFT headers/lines, then POST in the same transaction. Corrections
-- to a posted journal are new reversal journals, never in-place changes.
CREATE FUNCTION protect_posted_journal() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target record; journal_status text;
BEGIN
    IF TG_TABLE_NAME = 'journals' THEN
        IF OLD.status = 'POSTED' THEN
            RAISE EXCEPTION 'Posted journals are immutable; create a reversal' USING ERRCODE = '23514';
        END IF;
    ELSE
        FOR target IN SELECT DISTINCT tenant_id, journal_id FROM (
            SELECT CASE WHEN TG_OP <> 'DELETE' THEN NEW.tenant_id END AS tenant_id,
                   CASE WHEN TG_OP <> 'DELETE' THEN NEW.journal_id END AS journal_id
            UNION ALL
            SELECT CASE WHEN TG_OP <> 'INSERT' THEN OLD.tenant_id END,
                   CASE WHEN TG_OP <> 'INSERT' THEN OLD.journal_id END
        ) affected WHERE tenant_id IS NOT NULL ORDER BY tenant_id, journal_id LOOP
            -- Serialize line edits with posting and other edits of this journal.
            EXECUTE format('SELECT status FROM %I.journals WHERE tenant_id=$1 AND id=$2 FOR UPDATE', TG_TABLE_SCHEMA)
                INTO journal_status USING target.tenant_id, target.journal_id;
            IF journal_status = 'POSTED' THEN
                RAISE EXCEPTION 'Posted journal lines are immutable; create a reversal' USING ERRCODE = '23514';
            END IF;
        END LOOP;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER journals_immutable BEFORE UPDATE OR DELETE ON journals FOR EACH ROW EXECUTE FUNCTION protect_posted_journal();
CREATE TRIGGER journal_lines_immutable BEFORE INSERT OR UPDATE OR DELETE ON journal_lines FOR EACH ROW EXECUTE FUNCTION protect_posted_journal();

CREATE TABLE IF NOT EXISTS outbox_streams (
    tenant_id varchar(100) NOT NULL REFERENCES tenants(id),
    id varchar(100) NOT NULL,
    next_sequence bigint NOT NULL DEFAULT 1 CHECK (next_sequence > 0),
    PRIMARY KEY (tenant_id, id)
);
CREATE TABLE IF NOT EXISTS outbox_events (
    tenant_id varchar(100) NOT NULL,
    id varchar(100) NOT NULL,
    stream_id varchar(100) NOT NULL,
    sequence bigint NOT NULL CHECK (sequence > 0),
    aggregate_type text NOT NULL,
    aggregate_id varchar(100) NOT NULL,
    event_type text NOT NULL,
    payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    occurred_at timestamptz NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RETRY','INFLIGHT','PUBLISHED','DEAD_LETTER')),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    cycle_attempts integer NOT NULL DEFAULT 0 CHECK (cycle_attempts >= 0 AND cycle_attempts <= attempts),
    version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
    next_attempt_at timestamptz,
    last_attempt_at timestamptz,
    last_error text,
    lease_token varchar(100),
    lease_expires_at timestamptz,
    published_at timestamptz,
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, stream_id, sequence),
    FOREIGN KEY (tenant_id, stream_id) REFERENCES outbox_streams(tenant_id, id),
    CHECK ((status = 'INFLIGHT') = (lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)),
    CHECK ((lease_token IS NULL) = (lease_expires_at IS NULL)),
    CHECK ((status = 'PUBLISHED') = (published_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS outbox_events_pending ON outbox_events (tenant_id, status, next_attempt_at, occurred_at) WHERE status IN ('PENDING','RETRY');

DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['journals','journal_lines','outbox_streams','outbox_events'] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (tenant_id = current_setting(''inventory.tenant_id'', true)) WITH CHECK (tenant_id = current_setting(''inventory.tenant_id'', true))', table_name);
    END LOOP;
END $$;
