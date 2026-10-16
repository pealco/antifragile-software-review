# Lenses: The Ideas Behind The Review

The review is one method built from several bodies of work. Each lens gives a question to ask and a vocabulary to use; `references/review-playbook.md` is where they meet. The research behind the mistake-proofing lenses, with sources, is in `docs/mistake-proofing-research.md` in the skill repository.

## Mistake-Proofing (Shingo, Poka-Yoke)

Shigeo Shingo's poka-yoke starts from the claim that mistakes are inevitable but defects are not. A device that stops the work (a *control*) beats one that only signals (a *warning*), and a check at the source, when the mistake is made, beats inspection afterwards. Factories test their error-proofing devices with known-bad parts every shift; the review's challenge test is the same idea. Shingo first called these devices *baka-yoke* (fool-proofing) and renamed them because the name blamed the worker: the method assumes everyone makes mistakes.

Question to ask at each step of a flow: what is the strongest control that stops the mistake here, and has anything proven it works? The C0-C5 scale, the required strength, the control audit, and the agent rules are in the playbook under Control Strength.

Three findings from the evidence matter most for review:

- Strength beats count. At Facebook, the same static analysis got almost no fixes as a batch report and over 70% fixes when shown on each change. Prompts that told agents not to cheat on tests changed little; read-only tests stopped test edits.
- An unproven control is a guess. Several large outages (Cloudflare 2019, Facebook 2021, CrowdStrike 2024) came from safety controls that had broken or could never fire.
- Coding agents are actors with their own error profile: they act on every message, follow stale docs literally, game checks they can edit, route around blocks, and repeat the same mistake across runs. One design-level control protects every future run; instructions help some models and not others.

## Human Error (Reason, Norman)

Reason sorts errors into slips and lapses (the intention was right, the action went wrong), mistakes (the intention was wrong), and violations (a rule was knowingly broken). The control has to match the error: a slip wants a forcing function, a mistake wants a checkable standard before the action, a violation wants a visible, counted exception. His Swiss cheese model says harm needs several holes to line up, so count the layers between a mistake and the harm, and ask which of them have been tested.

Norman's forcing functions are the software designer's mistake-proofing devices: an interlock (the next step cannot start until the condition holds), a lock-in (the action cannot be abandoned half-done), and a lockout (the dangerous action cannot be reached from the normal path). A required argument, a typed ID, and a dry-run that must run first are all forcing functions.

## System Safety (Leveson, Hollnagel)

Leveson's view is that accidents come from missing or inadequate control, not only from component failure. For each control the review relies on, ask who enforces it, with what model of the system, and what happens when that model is stale (a kill switch whose name no longer matches the flag, a runbook for a service that was renamed). Hollnagel's Safety-II adds the complement: look at how the work succeeds every day and what people adjust by hand. Those adjustments mark where the next control belongs.

## Dependability (Avižienis, Laprie, Randell)

The chain is mistake (an actor's wrong action) -> fault (committed into code, config, or data) -> error (wrong run-time state) -> failure (harm) -> ruin (harm that cannot be reversed). The earlier a control acts, the cheaper the stop. Ruin is the one stage nothing can learn from, which is why irreversible harm sets the required control strength.

## Antifragility (Taleb)

Taleb's contribution to the review is the ranking and the posture, not a separate checklist. A fragile design is one where small stress produces accelerating harm; a design is safe to learn from only once its downside is bounded. From this come the exposure factors (blast radius, irreversibility, feedback delay, dependency concentration, ruin potential), the rule to cap compounding harm before adding anything else, and the idea that bounded stress is useful: fault injection, mutation tests, load tests, game days, and incident-derived regression tests make the next failure cheaper.

| Idea | Design question | Codebase signals |
| --- | --- | --- |
| Via negativa | What fragile mechanism can be removed? | Unused complexity, global mutable state, optional paths nobody owns, over-broad abstractions, brittle workflow steps |
| Bounded downside | Are losses capped while learning continues? | Rate limits, retry budgets, bulkheads, bounded queues, kill switches, dry-runs, rollbacks |
| Barbell | Is the core protected while experiments are isolated? | Boring core paths, feature flags, canaries, sandboxed experiments, separate blast radii |
| Optionality | Can the system change course cheaply? | Adapters where justified, migration reversibility, replaceable vendors, contract tests |
| Safe stress | Do bounded stressors make the system better? | Fault injection, chaos tests, mutation tests, load tests, game days, incident-derived tests |
| Redundancy and slack | Is there spare capacity before cascade failure? | Graceful degradation, alternate paths, backup restores, capacity headroom |
| Skin in the game | Do decision-makers feel consequences? | Clear owners, actionable alerts, dashboards, post-incident action items, release gates tied to SLOs |

Avoid treating more redundancy as a gain by itself. Redundancy without feedback is expensive robustness; redundancy with measured stress, ownership, and learning is what the review is after.

## Practical Analogues

- AWS Well-Architected chaos engineering guidance: run controlled fault experiments, preserve rollback mechanisms, capture results, and turn successful experiments into regression checks.
- Google SRE error budgets: a shared, measurable budget for unreliability that balances release velocity and reliability investment.
- Factory red rabbits: known-bad parts fed through a line to prove the inspection devices still catch them. The review's challenge tests and seeded-fault checks are the software form.

## Fragility Smells

- The code assumes the happy path and discards evidence when reality differs.
- The system is optimized for average load but has no explicit tail behavior.
- A single dependency, owner, region, queue, database, secret, or deploy tool can halt the whole product.
- Failure creates manual cleanup instead of telemetry, tests, and safer defaults.
- Releases are large, irreversible, and hard to observe.
- Tests confirm expected behavior but do not stress dependency failures, partial writes, retries, concurrency, or malformed inputs, or cannot fail at all.
- Abstractions hide blast radius instead of containing it.
- Operational decisions depend on forecasts instead of measured feedback loops.
- A mistake that people or agents keep making has a note about it instead of a control against it.

## Recommendation Order

1. Remove ruin exposure. Delete or simplify the thing that can cause irreversible damage.
2. Bound downside. Add limits, idempotency, backpressure, circuit breakers, dry-runs, and rollback paths.
3. Mistake-proof the action. Make the wrong action impossible or reject it at the source, and keep the stop visible.
4. Add feedback. Make failures observable, attributable, and turned into tests or runbooks.
5. Add safe stress. Use controlled experiments to expose hidden fragility before users do.
6. Preserve options. Keep replaceable boundaries and reversible choices around uncertain areas.

Name what each change buys: a stopped mistake, a smaller blast radius, a cheaper reversal, faster detection, or an incident turned into a test.

## Sources

- Shingo, *Zero Quality Control: Source Inspection and the Poka-Yoke System*, 1986.
- Reason, *Human Error*, 1990; Norman, *The Design of Everyday Things*, 1988 and 2013.
- Leveson, *Engineering a Safer World*, 2011; Hollnagel, *Safety-I and Safety-II*, 2014.
- Avižienis, Laprie, Randell and Landwehr, "Basic Concepts and Taxonomy of Dependable and Secure Computing", 2004.
- Taleb, *Antifragile*, 2012; Taleb, "Antifragility: a definition", *Nature* 494, 2013 (https://www.nature.com/articles/494430e); Taleb and Douady, "Mathematical definition, mapping, and detection of (anti)fragility", 2012 (https://ideas.repec.org/p/arx/papers/1208.1189.html).
- AWS Well-Architected, failure injection: https://docs.aws.amazon.com/wellarchitected/2023-04-10/framework/rel_testing_resiliency_failure_injection_resiliency.html
- Google SRE, embracing risk: https://sre.google/sre-book/embracing-risk/
