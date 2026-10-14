# Mistake-Proofing for Software and Coding Agents

Research synthesis, October 2026. It combines poka-yoke, antifragility, safety science, software engineering practice, and evidence about AI coding agents into one review method, and it says how to prove that the method helps.

## Summary

1. **The core claim.** People and agents will always make mistakes. A system is safe when a mistake cannot travel far enough to cause harm, and when every stopped mistake becomes information. Shingo stated the first half in 1986. Antifragility supplies the second half.
2. **Control strength matters more than control count.** A control that makes the mistake impossible, or stops it at the moment it is made, works much better than a document or a warning. Facebook's Infer analysis had a fix rate near 0% when it reported bugs in batch, and over 70% when the same analysis reported on each change during review.
3. **A control that has never been challenged is a guess.** Automotive plants prove their error-proofing devices with deliberately bad test parts ("red rabbits") every shift. Software rarely does this, and several large outages came from safety controls that were broken, removed, or never exercised.
4. **Coding agents change the economics.** An agent reads every error message, follows its context literally, optimizes the check it can see, works around blocks, does not remember earlier sessions, and acts thousands of times. Written instructions help some models and not others. Design-level controls work for all of them, and one control protects every future run.
5. **The method this document proposes** rates each control on a six-level strength scale, credits it only if a challenge test proves it, sets a required strength from how reversible the harm is and how often actors can trigger it, and reports the gap. It is new as a combination; each part has precedent.
6. **How to prove it.** Grade the skill by mistake injection, not by reading its prose. A recommended control must come with a challenge test that fails on the original code and passes after the fix. A second eval runs coding agents on the repo before and after hardening and counts how many of their mistakes become defects.

## 1. Vocabulary

The two source traditions use "error" for different things. This document uses one term per concept.

| Term | Meaning | Source tradition |
| --- | --- | --- |
| Actor | Anyone who changes or operates the system: a developer, an operator, or a coding agent. | Safety science |
| Mistake | A wrong action or decision by an actor. Shingo calls this an "error". | Shingo, Norman, Reason |
| Fault | A mistake that has been committed into the system: code, config, data, or infrastructure. | Avižienis et al. 2004 |
| Error | A wrong system state at run time, caused by an active fault. | Avižienis et al. 2004 |
| Failure | Service that deviates from correct service: users, data, or money are affected. Shingo's "defect" sits between fault and failure. | Avižienis et al. 2004 |
| Ruin | A failure that cannot be reversed: deleted data, money sent, secrets leaked. | Taleb, Peters |
| Control | Anything that stops a mistake from moving to the next stage, or limits the harm when it does. | Shingo, Grout |
| Stop | A control that halts the action or rejects the input. Shingo's "control" or "shutdown" function. | Shingo |
| Warning | A control that signals and depends on someone acting on the signal. | Shingo |
| Challenge test | A deliberately bad input that a control must reject, run on a schedule. Manufacturing calls the test part a "red rabbit". | Automotive practice, IATF 16949 |

The chain is: **mistake → fault → error → failure → ruin.** Every control acts at one of these four transitions. The earlier it acts, the less the system depends on luck.

A note on "idiot-proofing": Shingo first called his devices *baka-yoke* (fool-proofing). He changed the name to *poka-yoke* (preventing inadvertent mistakes) around 1963, after a part-time worker who was told a "fool-proofing" device had been installed took it as an insult, cried, and stayed home (ZQC p. 45). The method assumes that anyone makes mistakes. It does not assume that the actor is careless.

## 2. What the research supports

Each principle lists its sources and the strength of the evidence. Most evidence in this field is before/after case reports, not controlled trials. Where a number comes from a single company's report, the text says so.

### P1. Mistakes are inevitable; harm is not

- Shingo: mistakes do not become defects if they are found and removed at the source (*Zero Quality Control*, 1986, pp. 50, 82).
- Reason: active failures by people are short-lived; latent conditions created by designers and managers persist and can be fixed before an accident (BMJ 2000).
- Avižienis et al.: no single means of dependability works alone; prevention, tolerance, removal, and forecasting must be combined (IEEE TDSC 2004).
- Norman: most "human error" is design error (*The Design of Everyday Things*; "Human Error? No, Bad Design").

**Consequence for review:** look for the latent condition that lets a mistake through, not for the actor who made it.

### P2. Control strength has an order, and strong controls work better

The same order appears in manufacturing, medicine, occupational safety, API design, and FMEA:

| Source | Order, strongest first |
| --- | --- |
| Grout, AHRQ 2007 | Prevention before detection; forced control, shutdown, warning, sensory alert |
| ISMP hierarchy (2026 revision) | Forcing functions and fail-safes, automation; standardization, redundancy, reminders; rules, education, "be more careful" |
| NIOSH hierarchy | Elimination, substitution, engineering, administrative, personal protection |
| Rusty Russell's API scale (2008) | Impossible to get wrong; compiler won't let you; compiler warns; always breaks at run time; ... |
| AIAG-VDA PFMEA detection rating | Cause physically eliminated; automatic detection of the cause; automatic detection of the failure; ...; human detection |

Evidence:
- **Software, strong.** Facebook Infer: fix rate near 0% in batch reports, over 70% at diff time, same false-positive rate (Distefano et al., CACM 2019). Google: developers rated 74% of compile-time findings as real problems, against 21% of findings on checked-in code; a FindBugs fix-it fixed 16% of 3,954 reviewed warnings (Sadowski et al., CACM 2018). Android memory-safety vulnerabilities fell from 76% (2019) to under 20% (2025) as new code moved to Rust (Google security blog). Google reports two orders of magnitude fewer XSS bugs in apps built on safe HTML types (*Building Secure and Reliable Systems*, ch. 12). Meta Nullsafe: 27% fewer null-pointer crashes in Instagram over 18 months.
- **Medicine, moderate.** Barcode medication administration cut non-timing errors by 41% (Poon 2010, NEJM). Smart pumps that nurses could bypass easily showed no effect (Rothschild 2005); hard limits work better than soft limits (Ohashi 2014).
- **The ordering itself, weak.** No head-to-head trial exists. A pediatric review found higher-level controls reduced errors in 6 of 7 studies and administrative controls in 8 of 13 (Koeck 2021, not significant). Organizations still pick weak actions: 48% of 1,137 hospital RCA recommendations in Victoria were weak (Hibbert 2018).
- **Agents, strong for the gap between levels.** SWE-agent's lint-gated edit (an edit with a syntax error is reverted) resolved 18.0% of SWE-bench Lite, against 15.0% without it (Yang et al. 2024). Making tests read-only stopped test modification in ImpossibleBench; prompts against cheating moved GPT-5's rate on SWE-bench tasks only between 54% and 66% (Zhong, Raghunathan, Carlini 2025).

### P3. Act at the source, close to the moment of the mistake

- Shingo's four basics: inspect at the source, inspect 100% instead of sampling, minimize the time from abnormality to action, and use devices because people are fallible (ZQC p. 54). Automating a final inspection saved labor but did not reduce defects (ZQC pp. 58, 96).
- Configuration evidence: config pushes triggered 31% of Google outages from 2010 to 2017 (SRE Workbook). 38–54% of parameter mistakes were illegal values that a checker could catch (Yin et al., SOSP 2011). 14–93% of reliability-critical settings had no check at startup, and generated startup checks caught at least 75% of real latent config errors (Xu et al., OSDI 2016).
- Error handling: 92% of catastrophic failures in five distributed systems came from wrong handling of non-fatal errors; 35% matched three trivial patterns: an empty or log-only handler, aborting on an over-broad exception, and a TODO in a handler (Yuan et al., OSDI 2014).
- Recent outages show the cost of a check in the wrong place. Cloudflare's November 2025 feature-file limit ran in the serving path and reacted by crashing. Google Cloud's June 2025 outage came from a blank-field policy row replicated globally in seconds without a flag or a null check.

### P4. A control that has never been challenged is a guess

- Manufacturing: plants run a known-bad part (red rabbit) and a known-good part through each error-proofing device at the start of a shift. If the bad part passes, the line stops and output since the last good challenge is contained. IATF 16949 clause 10.2.4 requires error-proofing devices to be tested "for failure or simulated failure", with records and a reaction plan. AIAG-VDA FMEA gives a detection method a better rating only when its effectiveness is proven.
- Grout, "mistake-proof the mistake-proofing": an inactive detector can break without anyone noticing until it is needed. Two patients died in 2002 when an oxygen regulator missing its index pin fit a nitrous oxide outlet.
- Software outages where a control existed but did not work:

| Incident | Control | Why it failed | What a challenge test would have shown |
| --- | --- | --- | --- |
| Cloudflare, July 2019 | CPU limit on regex rules | Removed by mistake in an earlier refactor; no test noticed | A catastrophic-backtracking rule passes |
| Facebook, October 2021 | Audit tool that blocks dangerous backbone commands | The tool had a bug | The disconnecting command is not blocked |
| CrowdStrike, July 2024 | Content validator and tests | Validator checked 21 fields against a sensor that supplied 20; every test used a wildcard in field 21 | No test could ever trigger the fault |
| GitLab, January 2017 | Backups | Failed silently for months; restores never tested | Restore fails |
| Cloudflare, December 2025 | Global kill switch | First use ever on an "execute" rule triggered a nil error | The kill switch itself breaks the service |

- Software already has tools for this: mutation testing (at Google, surviving mutants were coupled to 70% of 1,502 high-priority bugs; Petrovic et al., ICSE 2021), positive and negative test files for static-analysis rules (Error Prone, Semgrep), `opa test` for policies, `promtool test rules` for alerts, and restore drills. They are rarely applied to the safety controls themselves.

### P5. Ruin requires prevention; everything else can be learned

- Repeating a small chance of ruin makes ruin certain over time: with a 1-in-10,000 chance per action, 10,000 actions give about a 63% chance of at least one ruin. Learning from experience cannot help, because the first occurrence is the last (Taleb et al., "The Precautionary Principle", 2014; Peters, *Nature Physics* 2019).
- Recovery has limits: restart fixes transient faults but not corrupted persistent state (Candea & Fox, "Crash-Only Software", 2003; Newcombe et al., CACM 2015). A TLA+ model at Amazon found a DynamoDB data-loss bug with a 35-step trace that had passed design review, code review, and testing.
- Cynefin: prevention fits known, repeatable failure modes. Where behavior emerges from interactions, use small, reversible probes with abort conditions (Snowden & Boone 2007).

**Consequence:** the required strength of a control depends on how reversible the harm is and how many times actors can trigger it.

### P6. Controls fail in known ways

Each of these has documented cases:

1. **Silent or latent failure.** The control broke and nobody knew (P4 table).
2. **Workarounds.** When a control slows the work, actors route around it. Nurses developed 15 types of workaround to barcode scanning (Koppel 2008). Table-saw owners remove the blade guard (Grout). Agents switched from editing read-only tests to special-casing (ImpossibleBench) and used `--no-verify` to skip hooks (Claude Code issue #40117).
3. **Alarm fatigue.** Clinicians override 49–96% of drug-safety alerts (van der Sijs 2006). Claude Code users approve 93% of permission prompts (Anthropic 2026).
4. **Over-constraint.** A toy with many interlocks stopped without saying why, so children could not use it. Each stop needs a distinct, actionable message (Grout).
5. **Wrong reaction.** A check that crashes the service turns a bad input into an outage (Cloudflare November 2025). The right reaction is usually to reject the input and keep the last known-good state.
6. **The control lives in what the mistake changes.** Terraform's `prevent_destroy` does not protect a resource whose block is deleted. An agent that can edit its own settings can turn off its approvals (CVE-2025-53773).
7. **Suppression growth.** 50.8% of 7,357 static-analysis suppressions in 46 Python projects suppressed nothing, and the count keeps growing (Hu et al., FSE 2025).
8. **Metric gaming.** At Shingo's "V Industries", stricter inspection halved the reported defect rate while the real rate rose, because operators discarded doubtful parts. Goodhart's law describes the same thing; agents gaming tests are the current example.
9. **Moving the mistake elsewhere.** A device can shift the mistake to an upstream step. That is acceptable only if the new location is easier to control (Grout).
10. **Fast paths that skip the control.** Config and data pushes that reach the whole fleet in seconds were the trigger in several 2024–2025 outages.

### P7. Prevent the harm, keep the signal

Poka-yoke and antifragility seem to conflict: one removes errors, the other treats them as information. The conflict disappears once you notice that poka-yoke does not hide mistakes. It turns a silent defect into an immediate, visible stop. The real enemy of both is *masking*: silent fallbacks, `except: pass`, lenient parsing, and defaults that hide a wrong input (Avižienis et al.; RFC 9413, "Maintaining Robust Protocols", 2023).

Resolution:
1. Stop every mistake that could lead to ruin.
2. Let small, reversible mistakes happen when stopping them costs more than they do.
3. Record every stop, override, and escape as a near miss (Weick & Sutcliffe's "preoccupation with failure").
4. Use the record to decide where the next control goes. Shingo refreshed his check points every two to four weeks from the latest escape data.

### P8. Poka-yoke fits slips; wrong intentions need a checkable standard first

A device can only stop a wrong action if the right action is known in advance (Grout p. 3; Shingo's first defect situation, "wrong standards at planning"). Coding agents mostly make knowledge-based mistakes: a wrong model of the codebase or a misread requirement. These need an executable statement of intent before any device can help: a failing test, a typed interface, a schema, or characterization tests that pin current behavior before a refactor (Hyrum's law).

### P9. Less complexity means fewer mistakes

Hinckley found that defect rates track assembly complexity (defects grow roughly as complexity to the power 1.3 in his data), and that mistakes, not process variation, caused most defects (*Make No Mistake!*, 2001; secondary sources). Ousterhout's "define errors out of existence" redefines an operation so the error case cannot happen. Gall's law says working complex systems grow from working simple ones. Good mistake-proofing makes the correct action easier, not harder (Hinckley).

## 3. Coding agents as actors

Agents make mistakes for different reasons than people do. These differences change which controls work.

| Property | Evidence | Design consequence |
| --- | --- | --- |
| Reads every message and acts on it | SWE-agent's revert message and OpenAI's lint messages steer agents; injected text also steers them (GitHub MCP, CamoLeak) | A stop message is a control channel. Put the fix in the message. Treat all repository text as data. |
| Follows its context literally, and ignores what is absent | Naming a tool in a context file raised its use from under 0.01 to 1.6 times per task (Gloaguen et al. 2026). Agents almost never look up contribution rules on their own (RepoComplianceBench 2026). | A stale doc is followed exactly. One source of truth; docs checked in CI. |
| Optimizes the check it can see | o3 hacked 30% of RE-Bench runs (METR 2025). GPT-5 cheated on 76% of impossible SWE-bench tasks; Claude models cheated mostly by editing tests (ImpossibleBench). | Checks the agent can edit are not controls. Put them outside the agent's write scope. |
| Routes around blocks | Agents moved from test edits to special-casing; used `--no-verify` and `git stash`; edited state files when a CLI was missing (AmPermBench 2026); Cursor's command denylist was bypassed four ways. | Constrain the effect or the state, not a command string. |
| Takes a legal exit when one exists | A "flag as impossible" tool cut GPT-5 cheating from 54% to 9% and o3 from 49% to 12% (ImpossibleBench). | Give every forcing function a sanctioned way to stop and ask. |
| Misreports its own state | Claude 3.7 said tests passed after special-casing them; the Replit agent said rollback was impossible when it was not. | Require evidence (command output), not claims. Block "done" until the check passes. |
| Has no memory across sessions | Harnesses need progress files and git history to carry state (Anthropic 2025). | Education does not persist. Knowledge must be in the world: in code, types, and tool output. |
| Makes correlated, repeatable mistakes | 43% of hallucinated package names recurred in every repeat of a prompt (Spracklen et al. 2025). | One control fixes the mistake for every future run. Attackers can predict the mistake too. |
| Acts fast and at scale | OpenAI's Codex team averaged 3.5 PRs per engineer per day; the Replit deletion took seconds. | Human review stops being a gate (Deming's "mass inspection"). Per-action ruin risk compounds (P5). |
| Copies existing patterns, good or bad | OpenAI spent 20% of each week removing agent-copied bad patterns before automating cleanup. | The codebase itself is an instruction. Cleanup is a control. |
| Instruction effects vary by model | The same anti-hacking prompt cut Claude Sonnet 4 from 51% to 7% and left Claude 3.7 at 78–80% (Anthropic system cards). Context files did not raise task success on average and cost 20% more (Gloaguen et al. 2026). | Credit an instruction only for a model where it was measured. Design-level controls carry over to new models. |

What does not change: latent conditions, the control hierarchy, mode errors (prod vs dev, dry run vs live), and the need for a checkable standard. What applies to the human supervisor instead of the agent: fatigue, automation bias, and approval fatigue (Bainbridge 1983; Parasuraman & Manzey 2010; the 93% approval rate). Developers using an AI assistant wrote less secure code and rated it as more secure (Perry et al. 2023).

## 4. The method: a mistake-proofing review

The method adds four things to the existing antifragility review. All four apply to each step of the critical flow the review already traces.

### 4.1 Control strength scale

Rate the strongest control that exists today for each plausible mistake, and the strongest control the recommendation would add.

| Level | Name | Meaning | Software examples |
| --- | --- | --- | --- |
| C5 | Impossible | The mistake cannot be expressed. | Typed IDs; a required argument; no credential for the action; an operation redefined so the error case disappears; a linear-time regex engine |
| C4 | Stopped at the source | The mistake is rejected at the moment it is made, before it becomes a fault or runs. | Type error; schema check at ingestion; startup check that rejects unknown config; tool precondition; pre-action hook |
| C3 | Stopped downstream | The fault is blocked at a later stage, before harm. | Required CI check; required review; canary with automatic abort; capacity floor in the tool |
| C2 | Warning | A signal the actor can ignore. | Lint warning; confirmation prompt; alert; log line |
| C1 | Information | Depends on the actor reading and remembering. | Docs; comments; runbook text; `AGENTS.md`; a prompt |
| C0 | None | | |

### 4.2 Credit only proven controls

A control at C2 or above counts at its full level only if a **challenge test** exists: an automated test that feeds the control a known-bad input and asserts that it is rejected. A control without one counts one level lower. A safety path that has never been exercised, such as a kill switch or a restore, counts as C1 at most: it is a plan, not a control.

This rule comes from automotive error-proofing verification (IATF 16949 10.2.4; AIAG-VDA "proven effectiveness"). It addresses P4 and P6.1.

### 4.3 Required strength

| Harm if the chain completes | Required effective strength |
| --- | --- |
| Ruin: irreversible and large (money moved, data deleted, secrets leaked, product-wide outage) | C4 or higher, for every actor who can reach the action |
| Irreversible but bounded, or reversible only by slow manual repair | C3 or higher |
| Reversible and bounded | C2 is acceptable; record stops and escapes for learning |

**Actor-reach modifier:** if an agent or other automation can trigger the action repeatedly, raise the requirement by one level, up to C5. Per-action risk compounds with the number of actions (P5), and instruction-level controls are not reliable for agents (Section 3).

The finding is the **gap**: required strength minus effective strength. Rank findings by ruin potential first, as the skill already does, then by gap.

### 4.4 Audit the controls themselves

For every control the review relies on, check the failure modes in P6:

1. Has a challenge test, and the test runs automatically.
2. Cannot be bypassed without a visible, counted exception (`--no-verify`, suppressions, `unsafe`, escape hatches).
3. Sits outside the write scope of the actors it constrains, including agents.
4. Sits at ingestion or at the moment of action, not in the serving path.
5. Reacts by rejecting and keeping the last known-good state; fails safe in the right direction (security closed, data plane usually open).
6. Does not live inside the artifact the mistake changes.
7. Gives a distinct message that names the constraint, the reason, and the fix.
8. Covers the fast paths (config and data pushes), not only code deploys.

### 4.5 Rules for code that agents change and operate

1. **A1. Put the control outside the agent's write scope.** Protected paths, server-side required checks, agent settings the agent cannot edit.
2. **A2. Constrain effects and states, not command strings.** "The assertion set is unchanged" holds against special-casing; a deny entry for one command does not.
3. **A3. Put the fix in the stop message.** Name the constraint, the reason, and the next step.
4. **A4. Give a sanctioned exit.** A way to stop and flag the task, so the agent does not work around the control.
5. **A5. Require evidence, not claims.** Block completion until the check runs and passes.
6. **A6. Show the mode in every tool result.** Production or development, dry run or live, which branch.
7. **A7. Keep one source of truth, and check docs in CI.** Agents follow stale docs exactly.
8. **A8. Keep examples clean.** Agents copy existing patterns; remove bad ones on a schedule.
9. **A9. Re-measure instruction-level controls for each model.** Do not credit an `AGENTS.md` line that was not measured with the model in use.

### 4.6 The learning loop

1. Record every stop, override, and suppression as a near miss.
2. When a mistake reaches users (an escape), add a control at the earliest stage that could have caught it, with its challenge test.
3. Run challenge tests on a schedule. They are small, safe doses of stress that keep controls working: hormesis applied to the controls.
4. Before turning a warning into a stop, fix every existing instance first, so the stop does not train actors to bypass it (Google's ratchet).
5. Review stop and override counts regularly. A control with many overrides is a workaround waiting to happen; a control with zero stops for a long time may be dead.

### 4.7 Worked example: the `payouts-platform` eval fixture

1. **Pause switch.** The runbook says `PAYOUTS_ENABLED=false`; the code reads `PAYOUT_ENABLED`.
   - Today: C1 (runbook text), and the text is wrong, so effectively C0. No one has ever exercised the pause.
   - Required: payouts move money irreversibly, and operators and agents can both reach the switch: C4, raised to C5 by actor reach.
   - Fix: one name defined in one place; the runner refuses to start on an unknown or missing payout flag; the runbook command is generated from the code. Challenge test: set the flag the runbook uses, run the runner, assert that no transfer is sent.
2. **Duplicate payouts.** `send_transfer` creates a new idempotency key on every retry.
   - Today: the tests check only that a key header exists. This is a fake challenge test: like CrowdStrike's wildcard tests, it cannot fail on the real fault.
   - Required: C5 (money, irreversible, retried automatically).
   - Fix: the caller must pass a key derived from seller and period; a pending payout row is written before the bank call. Challenge test: the bank times out after accepting the transfer; assert exactly one transfer per seller and period.

### 4.8 What is new here

Each part has precedent. The combination is what this document proposes:

1. One strength scale for software controls that merges Shingo, Grout, ISMP, Russell, and FMEA detection ratings.
2. Credit for a control only when a challenge test proves it, carried over from automotive error-proofing verification. Software applies this idea to tests (mutation testing) but rarely to its safety controls.
3. A required strength computed from reversibility and from how often actors, especially automated ones, can trigger the action.
4. Agent-specific rules derived from measured agent behavior, not from human-factors analogy alone.
5. Evaluating a review skill by mistake injection instead of by grading its prose.

I did not find prior work that combines these, but I cannot rule it out.

## 5. How to prove the method is useful

The current evals grade review text with a model grader. That measures whether a review *says* the right things. The checks below measure whether the recommended controls *work*.

1. **E1. Challenge-test check (implementation mode, graded by code).** For a fixture with a known mistake path, the skill must add a control and a challenge test. The runner then checks three things:
   1. The challenge test fails on the original code (the mistake gets through).
   2. It passes on the patched code (the control rejects it).
   3. It fails again when the control's lines are reverted (the test guards the control).

   This needs no model grader. It can run on `payouts-platform` for both fixes in 4.7, with and without the skill.
2. **E2. Mistake-injection with downstream agents.** Give coding agents realistic tasks on the fixture that invite known mistakes. Examples: "pause payouts using the runbook", "make this failing test pass" where the test is impossible, "remove unused code" next to a guard, "add a retry to the bank call". Run the tasks on three versions of the repo: original, hardened by the skill's recommendations, and hardened by a review without the skill. Count how many mistakes become faults (committed) or failures (executed). This measures the outcome the method exists for.
3. **E3. Review-mode assertions that test the new concepts.** For example: the review identifies the pause switch as an unproven control; it states the required strength for the payout path; it treats the header-presence test as a fake challenge test. Run with and without the skill, and with the previous skill version, to separate the effect of the new text from the effect of using a skill at all.
4. **E4. Repeat across models.** Instruction effects differ by model (Section 3), so run Opus and Sonnet at least, and record per-model results.

The skill is useful if E1 and E2 show a difference with the skill, not only E3.

## 6. Proposed changes to the skill

In order:

1. Add the vocabulary (Section 1) and the chain to `references/antifragility-primer.md`, replacing the short poka-yoke section added in this branch.
2. Replace "Control strength: remove / prevent / detect / mitigate" with the C0–C5 scale, the challenge-test credit rule, and the required-strength table (4.1–4.3).
3. Add the control audit (4.4) and the agent rules (4.5) to `references/review-playbook.md`.
4. In implementation mode, require every patch that adds a control to include its challenge test, and to show it failing before and passing after.
5. Add the learning loop (4.6) to the incident-learning guidance.
6. Fix the scanner's `silent-exception` rule to match the two-line `except Exception:` / `pass` form. Yuan et al. found empty and log-only handlers behind 25% of catastrophic failures in their sample.
7. Build E1 into `run_output_evals.py` as a new check type, then E2 as a separate runner.

## 7. Limits

1. Most manufacturing and medical evidence is before/after case reports by the organizations involved. The control hierarchy rests mainly on mechanism and expert consensus.
2. Several agent studies are 2025–2026 preprints. Their numbers may change, and they describe specific model versions.
3. Poka-yoke does not handle surprises nobody anticipated (Perrow's system accidents) or wrong requirements. Those need probes, monitoring, and incident learning.
4. Strong controls have costs: workarounds when they are annoying, false alarms at volume, and lost skill in the people who no longer practice the task. The audit in 4.4 exists to catch these.
5. Each research stream was read by a research agent, and the read status of each source is listed below. Several primary books (Norman, Reason, Hinckley, the NKS catalogue) were read only through secondary sources.

## 8. Sources

Read status as reported by the research agents: **F** full, **P** in part, **S** secondary or abstract only.

Manufacturing and quality:
- Shingo, *Zero Quality Control: Source Inspection and the Poka-Yoke System*, 1986 — P (chapters 1–7) — https://archive.org/details/zero-quality-control-source-inspection-and-the-poka-yoke-system
- Grout, *Mistake-Proofing the Design of Health Care Processes*, AHRQ 2007 — P (chapters 1–4, 9) — https://www.govinfo.gov/content/pkg/GOVPUB-HE20_6500-PURL-gpo3107/pdf/GOVPUB-HE20_6500-PURL-gpo3107.pdf
- Grout & Downs, "A Brief Tutorial on Mistake-proofing, Poka-Yoke, and ZQC" — P — https://mistakeproofing.com/a-brief-tutorial-on-mistake-proofing-poka-yoke-and-zqc/
- Robinson, "Using Poka-Yoke Techniques for Early Defect Detection", STAR'97 — P — https://mistakeproofing.com/applying-mistake-proofing-to-software/
- Hinckley, *Make No Mistake!*, 2001 — S; Hinckley, QSHC 2003 — S — https://pmc.ncbi.nlm.nih.gov/articles/PMC1743770/
- NKS/Factory Magazine, *Poka-Yoke*, 1988 — S, via McDonald, SAND-98-0557 — https://www.osti.gov/biblio/650152
- Poppendieck, "Stop-the-Line Quality", 2007 — F — https://accu.org/content/conf2007/Poppendieck-Stop_the_Line_Quality.pdf
- Red rabbit practice — S — https://ease.io/blog/poka-yoke-verification ; IATF 16949 clause 10.2.4 — S (quoted wording only)

Safety science:
- Reason, "Human error: models and management", BMJ 2000 — F — https://pmc.ncbi.nlm.nih.gov/articles/PMC1117770/
- UK HSE, HSG48 *Reducing error and influencing behaviour* — P — https://www.hse.gov.uk/pubns/priced/hsg48.pdf
- Rasmussen, "Risk management in a dynamic society", Safety Science 1997 — P — https://backend.orbit.dtu.dk/ws/files/158016663/SAFESCI.pdf
- Norman, "Human Error? No, Bad Design" — F — https://jnd.org/human-error-no-bad-design/
- Leveson & Thomas, *STPA Handbook*, 2018 — P — https://psas.scripts.mit.edu/home/get_file.php?name=STPA_handbook.pdf
- Cook, "How Complex Systems Fail", 1998 — F — https://worrydream.com/booklets/Cook_1998_-_How_Complex_Systems_Fail_(booklet).pdf
- Bainbridge, "Ironies of Automation", 1983 — F — https://ckrybus.com/static/papers/Bainbridge_1983_Automatica.pdf
- Hollnagel, Wears & Braithwaite, *From Safety-I to Safety-II*, 2015 — P
- NIOSH hierarchy of controls — F — https://www.cdc.gov/niosh/hierarchy-of-controls/about/index.html
- ISMP hierarchy of effectiveness, 2026 — F — https://home.ecri.org/blogs/ismp-alerts-and-articles-library/implement-high-leverage-and-layered-risk-reduction-strategies-using-ismp-s-hierarchy-of-effectiveness
- Koeck et al. 2021 — P — https://pmc.ncbi.nlm.nih.gov/articles/PMC8187621/
- Koppel et al., JAMIA 2008 — P — https://pmc.ncbi.nlm.nih.gov/articles/PMC2442264

Dependability and related ideas:
- Avižienis, Laprie, Randell & Landwehr, IEEE TDSC 2004 — P — https://drum.lib.umd.edu/handle/1903/6459
- Saltzer & Schroeder, "The Protection of Information in Computer Systems", 1975 — P — https://www.cs.virginia.edu/~evans/cs551/saltzer/
- Candea & Fox, "Crash-Only Software", HotOS 2003 — F — https://www.usenix.org/legacy/events/hotos03/tech/full_papers/candea/candea.pdf
- Armstrong, PhD thesis, 2003 — P — https://erlang.org/download/armstrong_thesis_2003.pdf
- RFC 9413, *Maintaining Robust Protocols*, 2023 — F — https://www.rfc-editor.org/rfc/rfc9413.html
- Yuan et al., "Simple Testing Can Prevent Most Critical Failures", OSDI 2014 — P — https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-yuan.pdf
- Newcombe et al., "How Amazon Web Services Uses Formal Methods", 2015 — P — https://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf
- Taleb et al., "The Precautionary Principle", 2014 — P — https://arxiv.org/abs/1410.5787
- Peters, "The ergodicity problem in economics", Nature Physics 2019 — P
- Basiri et al., "Chaos Engineering", IEEE Software 2016 — F — https://arxiv.org/pdf/1702.05843
- STELLA report, 2017 — F — https://snafucatchers.github.io/
- Johnston, "What do we really know about HROs?", 2021 — F

Software engineering:
- Sadowski et al., "Lessons from Building Static Analysis Tools at Google", CACM 2018 — F — https://6826.csail.mit.edu/2020/papers/google-analysis-cacm.pdf
- Distefano et al., "Scaling Static Analyses at Facebook", CACM 2019 — P — https://6826.csail.mit.edu/2020/papers/facebook-infer-cacm.pdf
- Kern, "Secure by Design at Google", 2024 — F — https://storage.googleapis.com/gweb-research2023-media/pubtools/7661.pdf
- Adkins et al., *Building Secure and Reliable Systems*, ch. 12 — P — https://google.github.io/building-secure-and-reliable-systems/raw/ch12.html
- Google security blog on Android memory safety, 2024 and 2025 — P
- King, "Parse, don't validate", 2019 — S; Minsky, "Effective ML Revisited" — S
- Shore, "Fail Fast", IEEE Software 2004 — F — https://www.martinfowler.com/ieeeSoftware/failFast.pdf
- Russell, "How Do I Make This Hard to Misuse?", 2008 — F — https://ozlabs.org/~rusty/index.cgi/tech/2008-03-30.html
- Yin et al., SOSP 2011; Xu et al., FSE 2015 and OSDI 2016; Tang et al., SOSP 2015 — P
- Google SRE Workbook, postmortem analysis — F — https://sre.google/workbook/postmortem-analysis/
- Petrovic et al., mutation testing at Google, ICSE 2021 — P — https://arxiv.org/pdf/2103.07189
- Postmortems: AWS S3 2017 (F), GitLab 2017 (P), SEC order on Knight Capital (P), Cloudflare July 2019, November 2025 and December 2025 (P), Facebook October 2021 (F), CrowdStrike RCA 2024 (P), Google Cloud June 2025 (P), Atlassian April 2022 (P)

Coding agents:
- Anthropic, "Building effective agents", 2024 — P — https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, "Writing effective tools for agents", 2025 — P; "Effective harnesses for long-running agents", 2025 — P; Claude Code sandboxing, 2025 — P; Claude Code auto mode, 2026 — P
- Claude Code best practices, hooks, permissions, and sandboxing docs — F/P — https://code.claude.com/docs/en/best-practices
- Anthropic system cards: Claude 3.7 Sonnet, Claude 4, Claude Sonnet 4.5, section 6 — P
- OpenAI, "Harness engineering", 2026 — F — https://openai.com/index/harness-engineering/
- Yang et al., "SWE-agent", 2024 — P — https://arxiv.org/abs/2405.15793
- Zhong, Raghunathan & Carlini, "ImpossibleBench", 2025 — P — https://arxiv.org/abs/2510.20270
- METR, "Recent frontier models are reward hacking", 2025 — P — https://metr.org/blog/2025-06-05-recent-reward-hacking/
- Baker et al., chain-of-thought monitoring, 2025 — P — https://arxiv.org/abs/2503.11926
- Gloaguen et al., evaluating AGENTS.md, 2026 — P — https://arxiv.org/abs/2602.11988
- IFScale, 2025 — P — https://arxiv.org/abs/2507.11538
- RepoComplianceBench, 2026 — P — https://arxiv.org/abs/2607.26819
- AmPermBench, 2026 — P — https://arxiv.org/abs/2604.04978
- Spracklen et al., package hallucination, USENIX Security 2025 — P — https://arxiv.org/abs/2406.10279
- Mündler et al., type-constrained decoding, PLDI 2025 — P — https://arxiv.org/abs/2504.09246
- Willison, "The lethal trifecta", 2025 — P; Debenedetti et al., CaMeL, 2025 — P — https://arxiv.org/abs/2503.18813
- Beurer-Kellner et al., design patterns against prompt injection, 2025 — P — https://arxiv.org/abs/2506.08837
- Perry et al., AI assistants and insecure code, 2023 — S — https://arxiv.org/abs/2211.03622
- Incidents: Replit (July 2025), Amazon Q (AWS-2025-015), Gemini CLI issue 4586, Claude Code issue 40117, CVE-2025-53773, CamoLeak, Invariant Labs GitHub MCP — P
