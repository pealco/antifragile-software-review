# How we compare arms

The scoreboard answers one question each night: does routing model calls through the proxy
(`routed`) solve as many tasks as the pinned model (`fixed`), and at what cost?

## What the numbers mean

- **Pass rate**: trials with reward 1.0 divided by the trials we planned for that arm. Every
  planned trial counts. A trial that crashed, timed out, or left no result is a failure, not
  a gap: an arm must not look better because its agent fell over more often.
- **Cost**: tokens times list price from `config/prices.toml`, per arm. This is list price, not
  our negotiated rate, so use it to compare arms rather than to forecast spend.
- **Tokens**: input plus output tokens reported by the agent for every model call.

## Before you quote a result

1. Check that both arms ran the same task set and the same number of trials (`job.json`).
2. Check that the routed arm was actually routed: `routed_calls` in the summary should be close to
   the number of model calls. The proxy logs every decision under its route id.
3. A difference under about 5 points of pass rate on the nightly set (8 tasks) is noise. Use the
   weekly run (120 tasks, 3 trials each) for decisions.

## Adding a model

Add the model's list prices to `config/prices.toml` in the same PR that lets the proxy route to
it, so its calls are priced from the first night.
