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
| **C6 (worker tiers, adopted)** | Sonnet / Opus / Opus+Sonnet | **3/3** | **332 x3** | **$12.6** |
| C7 (C6 with Haiku main) | Haiku / Opus / Opus+Sonnet | 3/3 | 331, 332, 332 | $16.9 |

## What we saw
1. **Worker tier mattered for quality.** One hidden test (an empty-input edge case in bundle import) failed in almost every run whose worker was Sonnet, and passed in every run whose worker was Opus. C6 assigns Opus to branchy-logic modules and Sonnet to plain ones; it passed all 332 tests in all 3 runs.
2. **The cheapest setup (C2, all-Sonnet workers) lost about two tests**; C6 recovers them for about 60% more cost than C2, still below condition B.
3. **A Haiku main did not save money.** C7 cost more and ran longer than C6 at the same quality.
4. **Stops were mostly permission denials, not model weakness.** Two Haiku-main runs stopped after a command shape was auto-denied (compound `cd ... &&`, multi-line scripts, absolute-path `git -C`). Denials happened in every model. Keeping commands to simple single lines removed most of them.
5. **Polling is expensive.** One Sonnet-main run polled agent status hundreds of times and cost about three times the others, because every poll re-reads the whole conversation as cache read.
6. **Where cost goes:** cache reads dominate token volume; cache writes and output dominate price. Splitting work cut cache reads but raised cache writes and tool calls versus Opus alone.

## Rules added to the agents (this change)
- Lead sets a worker tier per module before writing briefs: `handoff-worker-opus` for branchy logic and cross-file contracts, `handoff-worker` (Sonnet) for ordinary implementation, `handoff-worker-haiku` for trivial edits.
- Workers run their module tests and report a pass/fail table per checklist item; the lead re-runs and sends back only failing items.
- Interface docs state side effects, not just signatures.

## Limits
- One task, 3 runs per condition; differences of a few dollars or one or two tests are within noise.
- The Haiku worker tier was never exercised (the task had no trivial modules).
- Rule changes were made between rounds; later conditions are not strictly the same protocol as earlier ones.
- Prices are estimates; absolute dollar figures are not reliable, relative ones are more so.
