# eval-scoreboard (EVAL FIXTURE)

Runs our coding-agent benchmark against two configurations ("arms") and reports the results.

- `routed`: every model call goes through the routing proxy, which picks a model per request.
- `fixed`: every model call goes straight to the provider with one pinned model.

The nightly job launches both arms on `tasks/nightly.jsonl`, aggregates the per-trial result
files into `summary.json` (pass rate, cost and tokens per arm), and posts the summary to the
`#agent-evals` channel. The weekly model review and the routing roadmap are decided from these
numbers, so see `docs/comparing-arms.md` before you quote them.

## Usage

```bash
uv sync
# launch both arms, then aggregate
uv run python -m scoreboard launch --tasks tasks/nightly.jsonl --job-dir jobs/$(date +%F)
uv run python -m scoreboard summarize jobs/$(date +%F) --post
# or both steps at once
uv run python -m scoreboard run --tasks tasks/nightly.jsonl --post
```

`--agent-cmd` overrides the agent command from `scoreboard.toml` (useful for a local build of
the agent runner).

## Agent contract

The launcher runs the agent command once per trial as `<command> --task <task_id> --out <trial_dir>`,
with these environment variables set:

| Variable | Meaning |
| --- | --- |
| `LLM_BASE_URL` | Where the agent sends model calls: the proxy for `routed`, the provider for `fixed` |
| `LLM_MODEL` | Model name (`auto` for the routed arm; the proxy picks) |
| `ROUTER_POLICY` | Routing policy, routed arm only |
| `SCOREBOARD_ARM`, `SCOREBOARD_TRIAL_ID` | For the agent's own logs |

The agent writes `<trial_dir>/result.json`:

```json
{"reward": 1.0, "error": null,
 "usage": [{"model": "atlas-mini", "input_tokens": 1200, "output_tokens": 300, "route": "r-7f2c"}]}
```

`route` is the decision id the proxy returns in its `x-route-id` header; it is `null` for calls
that did not go through the proxy.

## Layout

- `scoreboard/`: the CLI (`launch.py`, `aggregate.py`, `pricing.py`, `report.py`).
- `scoreboard.toml`: arms, proxy, agent command. `config/prices.toml`: model price catalog.
- `tasks/`: task sets (JSON lines: `id`, `difficulty`).
- `docs/`: how we compare arms, nightly runbook.
