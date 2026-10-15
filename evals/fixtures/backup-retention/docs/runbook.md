# Backup retention runbook

The prune job runs at 03:00 UTC from cron on the backup host:

```
0 3 * * * cd /srv/retention && python3 -m retention.cli --today "$(date -u +%F)"
```

Retention: 7 daily, 4 weekly, 12 monthly. The tests in `tests/` cover the policy; run them
before changing it. Deleted backups are gone; there is no second copy.

Last restore drill: 2026-02 (succeeded).
