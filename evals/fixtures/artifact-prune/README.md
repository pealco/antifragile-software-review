# runstash (EVAL FIXTURE)

Archive experiment runs to object storage and free local disk on the shared GPU box.

A run directory (`runs/<name>/`) holds `run.json`, `logs/`, and one `trials/trial-NNNN/` directory
per trial. Runs take hours to days of GPU time, so a lost run is expensive to reproduce.

```bash
runstash push <run> [<run> ...]   # archive runs/<run> and upload it to the bucket
runstash list                     # local and remote runs side by side
runstash prune --dry-run          # show local runs that are safe to delete
runstash prune                    # delete them (asks first; --force to skip the prompt)
```

A run is safe to prune once it has been pushed: `prune` only deletes local runs whose archive is
already in the bucket. Runs are pushed automatically by `scripts/launch_run.sh` when they finish.

Settings live in `runstash.toml` (bucket, prefix, local runs directory). Per-user defaults can go in
`~/.config/runstash/config.toml`.

See `docs/runbook.md` for the shared-box procedures and `docs/design.md` for the storage layout.

## Development

```bash
uv sync
uv run pytest
```
