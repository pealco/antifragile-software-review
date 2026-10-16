# Hardening Review Scorecard

## Review Summary

- System shape:
- Stressors and actors:
- Hypothesis:
- Evidence confidence:

## System Map

- Critical flows:
- State and data:
- Dependencies:
- Release path:
- Feedback loops:
- Ownership and optionality:

## Critical Flow Trace

| Step | Evidence | Missing evidence | Cheapest observation |
| --- | --- | --- | --- |
| Trigger and entrypoint |  |  |  |
| State/data mutation |  |  |  |
| Dependencies |  |  |  |
| Failure handling |  |  |  |
| Observability and ownership |  |  |  |
| Rollback/degradation path |  |  |  |

- Scanner leads that matter:
- Scanner leads deferred:

## Finding Scorecard

| Finding | Evidence quality | Blast radius | Irreversibility | Feedback delay | Dependency concentration | Ruin potential | Exposure |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  |  | 0-3 | 0-3 | 0-3 | 0-3 | 0-3 | N/15 |

## Findings

### [P1] Short Title

- Evidence:
- Evidence quality:
- Analysis area:
- Exposure score:
- Harm:
- Blast radius:
- Reversibility:
- Change:
- Invariant: (the rule the control protects, stated as the harm it prevents)
- Control strength: (today Cn, proven or unproven -> after the change Cm, with its challenge test; required Ck)
- Missing evidence:
- Cheapest observation:
- Validation:
- Confidence:

## Backlog

- Remove first:
- Reversibility and optionality:
- Safe stress tests:
- Observability and ownership:
- Structural bets:
- Missing evidence / cheapest observations:
- Scanner leads to verify:
- Next reversible patch:
