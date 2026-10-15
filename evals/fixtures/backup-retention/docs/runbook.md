# Backup retention runbook

The prune job runs at 03:00 UTC from cron on the backup host:

```
0 3 * * * cd /srv/retention && python3 -m retention.cli --today "$(date -u +%F)"
```

Retention: 7 daily, then 4 weekly, then 12 monthly. The promise to the business: at any time a
backup at least 28 days old and a backup at least 12 months old exist. The tests in `tests/`
cover the policy; run them before changing it. Deleted backups are gone; there is no second
copy. A second promise: the prune job never deletes every backup. If the policy would delete all of
them (a wrong clock, a bad policy change), the job must stop and delete nothing.

Last restore drill: 2026-02 (succeeded).
