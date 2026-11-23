# Experiment: worker tiers and self-check rules (2026-11-22)

Question: can a lead + workers setup cut cost versus a single Opus agent without losing quality, and which rules matter?
Scope: **one task, 3 runs per condition.** Treat every number as a direction, not a proof.

## Task and grading
- One 12-module Swift feature set (profile store, patch, merge, lint, script, bundle, report, tool, ...) built from a written spec.
- 332 hidden tests, run after each run. A run counts as a success if every test file compiles and at least 327 tests pass.
- Cost uses estimated per-token prices back-computed from result events, not an official price list.
- Runs were headless (`claude -p`), one at a time, same prompt for every condition, CLI version pinned.

## Conditions (T5, large task)

| Condition | Main / lead / worker | Successes | Hidden tests | Avg cost (successes) |
|---|---|---|---|---|
| A: Opus alone | Opus | 3/3 | 332 x3 | $13.7 |
| B: handoff v0.3.2 | Sonnet / Fable / Opus | 6/6 | 331-332 | $19.1 |
| B3 | Haiku / Fable / Opus | 2/3 | 332 x2 (one stopped at 67) | $17.0 |
| B3o | Haiku / Opus / Sonnet | 2/3 | 330, 331 (one stopped at 115) | $10.6 |
| C (questions allowed, max 6) | Haiku / Opus / Sonnet | 3/3 | 330, 331, 330 | $9.0 |
| C2 (+ read-range rules) | Sonnet / Opus / Sonnet | 3/3 | 331, 330, 330 | $7.8 |
| C3 (+ spec checklist) | Haiku / Opus / Sonnet | 3/3 | 330, 327, 329 | $8.7 |
| **C6 (worker tiers)** | Sonnet / Opus / Opus+Sonnet | **3/3** | **332 x3** | **$12.6** |
| C7 (C6 with Haiku main) | Haiku / Opus / Opus+Sonnet | 3/3 | 331, 332, 332 | $16.9 |
| **D (Opus lead works alone, never delegated)** | Sonnet / Opus / - | **3/3** | **332 x3** | **$11.7** |

## What we saw
1. **Worker tier mattered for quality.** One hidden test (an empty-input edge case in bundle import) failed in almost every run whose worker was Sonnet, and passed in every run whose worker was Opus. C6 assigns Opus to branchy-logic modules and Sonnet to plain ones; it passed all 332 tests in all 3 runs.
2. **The cheapest setup (C2, all-Sonnet workers) lost about two tests**; C6 recovers them for about 60% more cost than C2, still below condition B.
3. **A Haiku main did not save money.** C7 cost more and ran longer than C6 at the same quality.
4. **Stops were mostly permission denials, not model weakness.** Two Haiku-main runs stopped after a command shape was auto-denied (compound `cd ... &&`, multi-line scripts, absolute-path `git -C`). Denials happened in every model. Keeping commands to simple single lines removed most of them.
5. **Polling is expensive.** One Sonnet-main run polled agent status hundreds of times and cost about three times the others, because every poll re-reads the whole conversation as cache read.
6. **Where cost goes:** cache reads dominate token volume; cache writes and output dominate price. Splitting work cut cache reads but raised cache writes and tool calls versus Opus alone.

## Isolated single-variable checks (Opus alone, 1 run each, base A = $13.7)
| Change | Cost | Cache read | Verdict |
|---|---|---|---|
| 5-minute cache writes forced | $16.3 | 25.2M | rejected (cache expiry, 2.5x writes) |
| read/command rules only (A2) | $13.3 | 23.8M | small effect |
| shorter output only (A4) | $12.1 | 19.3M | helps (-12% cost, -21% cache read) |
| batched calls only (A5) | $13.3 | 23.4M | small effect |
| Sonnet worker effort high | $12.5 | 35.0M | rejected (+60% cost, same quality) |
| Haiku main effort high | $14.5 | 21.9M | no gain |

Each is a single run; A4 should be repeated before relying on it.

## Operating plans (candidates)
1. **One lead is enough:** Opus lead works alone (D). Single-line commands, no status polling, short output, big output to files.
2. **Work must be split:** C6-style. Lead assigns tier per module, workers self-check with a table, lead re-runs, interfaces state side effects, single-line commands. Workers + helpers <= 4 (effect untested).
3. **Several tasks from one main:** main -> leads (<= 4) -> workers/helpers (<= 4 each). **Untested.**
Delegation did not clearly beat a single agent at this task size (C6 $12.6, A $13.7, D $11.7).

## Corrections to earlier claims
- "5-minute cache saves ~$1.3": wrong, it cost more.
- "15x tokens for multi-agent": that is Anthropic's research system; our coding runs were 1-1.4x.
- "Read rules explain D's savings": overstated; read rules alone had a small effect.
- Permission-denial counts were first mis-tallied and recounted.

## Rules added to the agents (this change)
- Lead sets a worker tier per module before writing briefs: `handoff-worker-opus` for branchy logic and cross-file contracts, `handoff-worker` (Sonnet) for ordinary implementation, `handoff-worker-haiku` for trivial edits.
- Workers run their module tests and report a pass/fail table per checklist item; the lead re-runs and sends back only failing items.
- Interface docs state side effects, not just signatures.

## Limits
- Cited papers: five read in full, one body-only, one abstract-only (ICML orchestrator-bottleneck figures such as ~15% are unverified and not used as rules). No paper states a "compact at task boundaries" or "short always-on rules" rule.
- One task, 3 runs per condition; differences of a few dollars or one or two tests are within noise.
- The Haiku worker tier was never exercised (the task had no trivial modules).
- Rule changes were made between rounds; later conditions are not strictly the same protocol as earlier ones.
- Prices are estimates; absolute dollar figures are not reliable, relative ones are more so.
