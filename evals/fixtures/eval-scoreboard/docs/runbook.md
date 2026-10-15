# Nightly eval runbook

The nightly workflow (`.github/workflows/nightly.yml`) runs at 02:00 UTC on the eval runner.

## The nightly job failed

1. Open the workflow run and read the `scoreboard run` step log.
2. If the proxy was down, the routed arm's agents fail to connect; rerun the workflow once the
   proxy health check (`curl http://127.0.0.1:8411/healthz` on the runner) is green.
3. If the agent runner itself crashed for most trials, check the runner's disk and memory, then
   rerun.

## The chat post is missing

`summary.json` is written before the post, so the numbers are not lost. Repost by hand:

```bash
uv run python -m scoreboard summarize jobs/<date> --post
```

## Rerunning one arm

```bash
uv run python -m scoreboard run --tasks tasks/nightly.jsonl --arms routed --job-dir jobs/<date>-routed --post
```

Do not mix trials from two jobs in one job directory; the summary reads only `job.json` of the
directory it is given.
