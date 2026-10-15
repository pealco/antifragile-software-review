# Shared GPU box runbook

## Disk is full

Training jobs fail with `No space left on device` when `/data` fills up. Most of the space is old
run directories under `/data/ranking/runs/` that have already been archived.

1. Check usage: `df -h /data` and `du -sh /data/ranking/runs/* | sort -h | tail`.
2. From `/data/ranking`, see which runs prune would delete:

   ```bash
   runstash prune --dry-run
   ```

3. Delete them:

   ```bash
   runstash prune --force
   ```

`prune` only deletes runs whose archive is already in the bucket, so nothing is lost. If you need
a pruned run again, restore it (below).

If the disk is still full after pruning, ask in the team channel before deleting anything by hand.

## A push failed

`scripts/launch_run.sh` pushes a run when it finishes. If the upload fails, the script prints a
warning and carries on. Push the run by hand once the bucket is reachable:

```bash
runstash push <run>
```

## Resuming a run

To add trials to an existing run, start it with `--resume`:

```bash
scripts/launch_run.sh --resume <run> --trials 8
```

New trials are written to `runs/<run>/trials/`. The run is pushed again when it finishes.

## Restoring a pruned run

```bash
aws s3 cp s3://lab-run-archive/experiments/ranking/<run>.tar.gz - | tar xz -C runs/
```
