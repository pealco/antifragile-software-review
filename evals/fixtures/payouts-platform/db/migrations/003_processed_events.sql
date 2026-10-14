CREATE TABLE processed_events (
    event_id text PRIMARY KEY,
    received_at timestamptz NOT NULL DEFAULT now()
);
