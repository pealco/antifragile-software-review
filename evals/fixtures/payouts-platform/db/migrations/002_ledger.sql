CREATE TABLE ledger_entries (
    id bigserial PRIMARY KEY,
    seller_id bigint NOT NULL REFERENCES sellers (id),
    kind text NOT NULL CHECK (kind IN ('earning', 'fee', 'payout', 'reversal')),
    amount_cents bigint NOT NULL,
    available_at timestamptz NOT NULL,
    reference text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ledger_entries_seller_available ON ledger_entries (seller_id, available_at);
