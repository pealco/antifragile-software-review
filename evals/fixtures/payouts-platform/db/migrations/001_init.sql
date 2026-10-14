CREATE TABLE schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sellers (
    id bigserial PRIMARY KEY,
    email text NOT NULL UNIQUE,
    display_name text NOT NULL,
    bank_account_ref text,
    payouts_paused boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    token text PRIMARY KEY,
    seller_id bigint NOT NULL REFERENCES sellers (id),
    expires_at timestamptz NOT NULL
);
