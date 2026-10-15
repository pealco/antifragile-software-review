# backup-retention (EVAL FIXTURE)

Nightly job that deletes old database backups according to a retention policy. See
`retention/policy.py` for the policy and `docs/runbook.md` for operations.

```bash
python3 -m unittest discover -s tests
python3 -m retention.cli --today 2026-10-15 --dry-run
```
