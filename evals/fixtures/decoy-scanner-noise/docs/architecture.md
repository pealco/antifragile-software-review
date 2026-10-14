# Architecture

- One region (us-east-1). A second region for failover is planned, not built.
- One Postgres primary. Read replicas are not used by the worker.
- `app/` accepts orders and writes `orders.fulfilment_status`.
- `worker/` picks up unfulfilled orders and ships them. It runs as 4 long-lived processes
  that are restarted one by one during a deploy.
- Deploys run on every push to `main` (see `.github/workflows/deploy.yml`).

TODO: document the on-call rotation.
FIXME: the capacity numbers above are from 2024.
