CREATE TABLE payouts (
    id bigserial PRIMARY KEY,
    seller_id bigint NOT NULL REFERENCES sellers (id),
    period date NOT NULL,
    amount_cents bigint NOT NULL CHECK (amount_cents > 0),
    bank_transfer_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (seller_id, period)
);
