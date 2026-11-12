---
name: handoff
description: Keep the main session small. The main session only talks with the user; a lead subagent reads the context and writes briefs, several workers implement them in separate work areas, and only short summaries plus markdown paths come back. At a task boundary, compress the work into a structured handoff note and continue in a fresh session. Use when the user says /handoff, "hand this off", "start a fresh session", "compact and continue", "새 세션으로 넘겨", "정리하고 새로 열어", when starting a multi-step task in a project that uses this setup, or when a titled piece of work is finished and the conversation has grown long.
---

# handoff — the main session talks, subagents work, notes carry the state

## Why
- Every call re-sends the whole conversation of that session. Whatever the session reads or runs stays in it and is paid for again on every later call.
- Measured on our own sessions (49 sessions, 2026-09 to 2026-11, `scripts/compare_sessions.py`):
  - A fresh start from a handoff note begins at ~100K tokens; right after auto-compaction it is ~125K. From there **both grow by 50–80K every 50 calls** if the session does the work itself.
  - About 80% of that growth was command output, screenshots and lookups; the assistant's own text was ~4%.
  - Output tokens per call were the same everywhere (~600). Cost differences come from input.
  - Subagent first turn (2026-11-12, one session, 28 subagents, n=1 for the allowlisted agent): ~10.8K input tokens with a `tools:` allowlist vs ~55K without; two delegated jobs of 3–4 tool calls cost ~64K new input each.
- So a handoff alone is not enough. The context stays small only if the work happens somewhere else: in subagents, whose reading never enters the main session.
- Paper basis for the note format and for compacting at task boundaries: Belcak et al., "You don't need long context" (NVIDIA, arXiv 2611.05306). Sources and details: `reference.md` (read only when needed).

## Roles and models
| Role | Who | Model | Does |
|---|---|---|---|
| Main | the session the user talks to | Sonnet 5.5 (`claude-sonnet-5-5`) | Talks, relays paths, asks questions; does jobs inside the direct-handling threshold; writes the one-page brief on the single-track route. No large file reads, long commands or big diffs |
| Lead | `handoff-lead` | Fable 5.2 (`claude-fable-5-2`) | Reads the context once, splits the work, writes self-contained briefs and `plan.md`, sets each brief's tier, runs the plan check. No code edits |
| Worker ×N | `handoff-worker` | Opus 5.5 (`claude-opus-5-5`) | Tier `worker`: everything that needs judgment — implementation, logic, root cause, design. Reads only its brief, verifies narrowly, commits |
| Reviewer | `handoff-reviewer` | Opus 5.5 | Only before a high-risk merge or push: re-checks commits, diffs and the verify log. No code edits |
| Helper | `handoff-helper` | Sonnet 5.5 | Tier `helper`: chores that need a little thought — summarising/comparing results, checking screenshots, wording swaps inside the range a brief names, simple tidy-ups, finding cause candidates in logs, merging non-overlapping branches. No other edits |
| Runner | `handoff-runner` | Haiku 5.5 (`claude-haiku-5-5`) | Tier `runner`: fixed commands that repeat — the same verbatim command set run several times or over several targets (more than 3 tool calls in total, or long output sent to a file), checkable by numbers/output (git status/log, tests and builds → pass/fail counts, file existence/line counts, copying named files) and returns the numbers. No judgment, interpretation, summaries or code edits |

- The agents ship with this plugin with their models pinned. Set the main model per project: copy `examples/settings.json` to `<project>/.claude/settings.json`.
- All five agents carry a `tools:` allowlist (base Read, Bash, Glob, Grep; lead: + Write; worker: + Edit, Write; helper: + Edit; runner and reviewer: base only). No MCP or browser tools. Reason: it cut the fixed first turn of a subagent from ~55K to ~11K input tokens in our logs (n=1 sample, direction only).
- A project may define its own agents with the same roles (project rules baked in); use those instead when they exist.

## Rules for the main session
1. **Mostly talk.** Do not read large files, run long commands or review big diffs. Allowed directly: answering from what is already known, relaying a path, asking the user a question, a job inside the direct-handling threshold, and writing the one-page brief on the single-track route (rule 2).
   - **Direct-handling threshold**: a job expected to take 3 tool calls or fewer and return about 6,000 characters or less (a short file read, one to three commands whose output is passed on as-is) — the main session does it itself; no subagent of any tier.
   - **Delegation threshold**: anything larger, multi-step, parallel or with big output goes to a subagent. Every subagent start pays a fixed first turn (observed, n=1 sample, direction only: ~11K input tokens with a `tools:` allowlist, ~55K without), so small delegations lose: two delegated jobs of 3–4 tool calls cost ~64K new input each.
   - If a direct job grows (a 4th call is needed, or output passes 6,000 characters), stop and delegate the rest. These thresholds (3 calls, 6,000 characters) are hypotheses; adjust after measuring.
2. **Pick the route by job size; the lead writes briefs, with one exception.** (v0.3.2 — hypothesis, effect not measured yet)
   - **Direct**: inside the direct-handling threshold (rule 1) — the main session does it.
   - **Single-track**: one track of small-to-medium work — one agent can do it in order, nothing to run in parallel — goes straight to one `handoff-worker` (`handoff-helper` only for a wording swap inside a named range) with a one-page brief written by the main session. No lead, no `plan.md`.
   - **Lead**: the work splits into 2 or more parallel tracks, or the one-page brief cannot be filled — pass "the user's request (near-verbatim) + task folder" to the lead. If the same lead is still available, continue it instead of starting a new one.
   - **Runner, direct**: read-only fixed commands that repeat — the same verbatim command set run several times or over several targets (more than 3 tool calls in total, or long output sent to a file), checkable by numbers/output — may go straight to `handoff-runner` with an instruction of 3 lines or less (no brief, no file edits).
   - **The one exception to "main never writes briefs" (v0.3)** is the single-track route, and only while all three hold: (a) one track; (b) every required item of the one-page brief can be filled from the user's words and earlier hand-backs, without reading files or running commands beyond the direct-handling threshold; (c) it fits 3,000 characters. If any fails, or the worker returns "Blocked:" for missing facts, the job goes to the lead. The main session never writes `plan.md`, never splits work into several briefs, and never rewrites a brief that came back blocked.
3. **Pass paths, not content.** Give subagents the task folder and brief paths; receive result paths and a few lines. Relay a lead's or worker's report to the user as the path + 3 lines at most — never re-paste or re-summarise the note. If the same completion notice arrives again (same agent, same result path, nothing new), do not answer it.
4. **Answer concisely.** Conclusion and key points only. Tables and background only when the user asks. Never re-paste what was already shown.
5. **One task = one title.** Name the task in one line. A request outside it becomes a new task folder (and, when the conversation is long, a new session).
6. Subagents cannot start subagents: the main session relays brief paths (the lead's, or its own one-page brief on the single-track route) to the agent named by each brief's `Model:` tier.

## Workflow
1. **Open a task folder**: `~/.claude/handoffs/tasks/YYYY-MM-DD-<slug>/`. Everything below is written there.
2. **Lead** (lead route only): pass the user's request (near-verbatim) and the folder. The lead writes `plan.md` (brief list, owned-files table, tiers, the verify step, items with no owner, the plan check) and one self-contained `brief-<N>-<slug>.md` per bundle, then returns paths, one-line summaries, which briefs can run in parallel, and questions for the user. On a follow-up request the lead reads only `plan.md` and appends briefs.
   - **Single-track route**: the main session writes `brief-<N>-<slug>.md` itself from the one-page checklist (Briefs and results) and passes its path to the project's assigned worker. No `plan.md`.
3. **Questions**: ask the user what the lead could not resolve. Do not let workers guess.
4. **Run each brief at its tier**: `Model: runner` → `handoff-runner`, `helper` → `handoff-helper`, `worker` → `handoff-worker` — in parallel when the lead marked them independent, in order otherwise. Each returns its result path + 3 lines (one more line only if something is blocked).
   - **Escalation**: if a brief comes back with "Blocked:" (outside its conditions, or failed), it changed nothing; run the same brief one tier up (runner → helper → worker). If a worker is blocked, it goes back to the lead. Escalations are counted in the result note.
   - **Which worker**: work that continues in the same project goes to the assigned worker by SendMessage; parallel or unrelated briefs go to one-off workers (see Assigned worker).
5. **Report as each finishes**: tell the user what landed and what is unverified as soon as an agent returns. Never hold results until all are done. Once per completion, as the path + 3 lines; a repeated notice gets no answer.
6. **Verify once**: after merging, one `brief-verify` runs the full build and full test suite once — runner when the commands and expected counts are fixed, helper when the failure log must be read for cause candidates. Fixes become new worker briefs from the lead. On the single-track route there is no merge: the one brief's Verify names the full build/test and it runs once, at the end.
7. **Reviewer** (only before a high-risk merge or push — merging 2 or more worker branches, pushing or deploying to a shared or production branch, or changes to security, permissions, payments or data migrations; otherwise the verify step is the check): pass the result paths and the verify log. It writes `review.md` and returns pass or the list of problems. Problems go back to the lead for a new brief.
8. **Close the task**: write the handoff note (below) into the folder as `handoff.md`. The next task starts from that note only.

Things the user must see (screenshots, a rendered page) are saved in the task folder by the subagent; the main session only gives the path.

## Briefs and results
`brief-<N>-<slug>.md` (written by the lead; by the main session only on the single-track route) must be **self-contained**: the agent reads this one file and nothing else in the task folder. No "read <other note> first"; shared rules are not split into a separate file — the lines that apply are excerpted into each brief. Limit: 6,000 characters (characters, not bytes) for a brief and for any Agent prompt; split or trim Context if larger. Exploratory work (audits, investigations) that cannot be excerpted states a "search scope" in Context instead.
```
# brief-<N>-<slug>
Goal: one line
Model: runner | helper | worker — one-line reason (which row of the tier table)
Context: only the facts this job needs, 15 lines or less. Sources as (file:line) — a citation, not an instruction to open it.
  - findings/decisions quoted as one original line
  - only the project rules that apply here (commit style, forbidden commands, tone)
  - base HEAD hash, files other sessions are using
Owned files: the only files this agent edits — disjoint from every other brief
Isolation: none | worktree (+ branch, port, persist path)
Changes: file:line — what it is now → what it becomes. Wording exactly as it should read.
Do not touch: files or areas
Verify: a narrow check for this brief only + expected result. Full build/test: "done by the verify step in plan.md" (single-track route: the full build/test command itself, run once at the end).
  (runner briefs: the exact commands and the expected output/counts)
Commit: message style. Last line: "the Co-Authored-By line the system assigns to the running model" — never a model name.
Questions: anything unknown. If any, the agent does not start and returns it.
```
**One-page brief (single-track route, written by the main session)** — same file name and headings, 3,000 characters or less. Every item is filled, or the job goes to the lead:
- [ ] Goal — one line
- [ ] Model — `worker`; `helper` only for a wording swap inside a named range
- [ ] Context — the user's request near-verbatim, facts from earlier hand-backs, the project rules that apply, and a search scope (folders or files to look in) where exact lines are not known
- [ ] Owned files — files or one folder; nothing another running agent owns
- [ ] Changes — the outcome wanted, in the user's terms; the worker locates the lines
- [ ] Do not touch
- [ ] Verify — the narrow check, plus the full build/test command if known (else "per the project's CLAUDE.md"); it runs once, at the end
- [ ] Commit — style; trailer = the line the system assigns
- [ ] Questions — "none"; otherwise ask the user before starting the worker
- [ ] Result note path
`result-<N>-<slug>.md` (written by the agent) starts with this fixed block — the main session and later agents read only this block:
```
Done: (3 lines max — include commit hashes)
Next: (3 lines max — hand-offs, unverified items)
Blocked: (or "none")
```
A `## Details` section below is optional (verify numbers, out-of-scope findings, log and screenshot paths, escalation count).

Large results (logs, diffs, canvases, earlier notes): never paste or read them whole — write to a file, `grep -n`, then quote or read only the needed lines.

## Several workers, separate work areas
- The lead splits by **file ownership**: every brief lists `Owned files:` and the lists never overlap. Changes that are ordered (shared core → screens) or touch the same file stay in one brief.
- A worker edits and stages only its owned files (`git add <paths>`, never `git add -A`), and never reverts or reformats files it does not own.
- `Isolation: worktree` when owned files could still collide — lockfiles, generated files, a shared build output. Start that worker with `isolation: "worktree"`; it commits to its own branch, and afterwards the helper merges the branches one at a time.
- When owned files do not overlap, run 2–3 workers at once (4 at most — beyond that review becomes the bottleneck).
- Do not split 1–2 edit tasks: one brief, one worker.
- Each worker runs only its brief's narrow Verify (`node --check`, its own unit tests, one screenshot of its screen). The full build and full test run happen once, in the verify step after merging.

## Assigned worker (per project) — hypothesis, effect not measured yet
- Work that continues in the same project goes to the same `handoff-worker`: the main session keeps its agent id and sends the next brief path with SendMessage instead of starting a new worker, so what it already read is reused.
- Parallel briefs and unrelated work get one-off workers (a new `handoff-worker` each). One assigned worker per project at most; it owns files like any other worker.
- **Replace at about 150K**: when the assigned worker's context nears ~150K tokens (the usage shown with its hand-back; if none is shown, after 4 continued briefs), ask it for a takeover note, then start a new assigned worker from that note plus the next brief. Replace it at a session handoff too.
- Takeover note `takeover-<N>.md` in the task folder (written by the worker, 40 lines or less): `Done:` what was done, with commit hashes / `Next:` what to do next, starting with the immediate command or edit / `Blocked:` what is stuck, or "none" / `Pointers:` up to 10 `file:line` places worth re-opening. It is the one extra file a new assigned worker reads besides its brief.
- Basis (one session, n=1): a lead continued twice by SendMessage started its turns at 55K → 112K → 117K input, of which 103K and 112K were cache reads. Not measured: whether that beats a new allowlisted worker (~11K first turn) that re-reads what it needs; a continuation after the prompt cache has expired pays the whole context again as new input. See Measure.

## Tiers — who runs a brief
The lead sets `Model:` on every brief. **When unsure, go one tier up.**

| Tier | Agent (model) | Takes | Never |
|---|---|---|---|
| runner | `handoff-runner` (Haiku 5.5) | **Repeated fixed commands only**: fixed commands that repeat — the same verbatim command set run several times or over several targets (more than 3 tool calls in total, or long output sent to a file), checkable by numbers/output; the commands are written verbatim in the brief — git status·log, running tests/builds and reporting pass/fail counts, file existence and line counts, copying named files | judgment, interpretation, summaries, code edits |
| helper | `handoff-helper` (Sonnet 5.5) | **Chores that need a little thought**: summarising/comparing results, checking screenshots against wording in the brief, wording swaps and simple tidy-ups inside the range the brief names, finding cause candidates in logs, merging branches already confirmed not to overlap (stop on conflict) | edits outside the named range, logic changes, settling a root cause, design |
| worker | `handoff-worker` (Opus 5.5) | **Everything else**: implementation, fixes, root-cause analysis, design decisions; security, permissions and data migrations regardless of size | — |

- Outside its conditions or on failure, an agent changes nothing, writes it under "Blocked:" and returns; the main session reruns the same brief one tier up (runner → helper → worker → lead).

## Plan check (lead, before returning briefs)
At the end of `plan.md`, mark each item "checked" or "n/a":
1. **No owned-file overlap**: the `Owned files` of all briefs are disjoint, and do not touch files other sessions have uncommitted.
2. **No duplicate work**: every request/finding item maps to exactly one brief (item → brief table).
3. **No unowned follow-ups**: a change that requires a change elsewhere (a server that now returns 400 → the screen's message) has an owner. If none fits, add a brief or list it under "ask the user".
4. **Full tests once**: the full build/test is gathered into one verify step after merging; each brief's Verify covers only its own files.
5. **Commit trailer**: no brief hard-codes a model name (the system-assigned trailer of the running model is used).
6. **Tiers**: every brief has `Model:` and a reason; nothing that fits a lower tier was left higher; every runner brief has the exact commands and expected output (numbers); no brief of any tier for a job inside the direct-handling threshold.
7. **Self-contained**: no "read first"; each brief can be started from itself alone.

## Handoff note (at a task boundary)
Only at a boundary — compacting mid-task breaks prompt caching and can raise real cost.

1. Write the note in the format below. It is a brief for whoever continues, not a retrospective.
   - Location: `handoff.md` in the task folder, or `~/.claude/handoffs/YYYY-MM-DD-<slug>.md` when there is no task folder.
   - **Never overwrite or delete an existing note.** If it exists, append `## Addendum — HH:MM`. Record changed facts as "Correction:" and leave the original text.
   - Same rule for other markdown you update (CLAUDE.md, specs, memory): add or correct only; delete or rewrite only after the user confirms.
2. Include uncommitted changes and running processes (dev servers, emulators, ports).
3. Metrics: `python3 <this skill folder>/scripts/session_tokens.py <session id> --json`, pasted as the last line. Subagent usage is summed automatically.
4. Check before continuing (the helper can run these):
   - Preservation: after an append, the line count did not drop and the first line is unchanged.
   - Format: all 7 headings exist; empty ones say "none".
   - Facts: commit hashes exist (`git log --oneline -1 <hash>`), paths exist, push state matches `git status -sb`.
   - Unverified: anything not checked by execution is marked "unverified".
   - Conflicts: if an existing note, CLAUDE.md or memory contradicts this skill, do not edit it — list `file:line` with a suggested change and apply only after the user confirms.
   - Promotion: propose only decisions confirmed by execution or by the user as candidates for durable memory or the project's spec docs. Apply after confirmation.
5. Continue: start a fresh session with "read `<note path>` and continue" (desktop app: start a new session with that brief; CLI: `claude "read <note path> and continue"`). Tell the user one line: note path, check result, new session.

```
# Handoff — <title> (YYYY-MM-DD)
1. Objective: the user's request (near-verbatim) + preferences and corrections given during the session
2. Established facts: exact paths, symbols, commands, values, errors. Mark guesses "unverified"
3. Applied changes: per file/commit, what changed + verified? + pushed?
4. Verification: exact checks run and results
5. Dead ends: failed approaches not to repeat
6. Remaining plan: ordered subgoals, the immediate next command/edit, completion criteria
7. Environment: running servers, devices, ports, test accounts
Metrics: session_tokens.py --json output
```
- For truncated output, give a narrow command to retrieve it instead of the content. Never invent observations.
- Point to files by path and line instead of copying content.
- If the raw history is needed, grep the session transcript (`~/.claude/projects/**/*.jsonl`).

## Measure
- Target: the main session's context stays under ~300K for the whole task. Check with `scripts/session_tokens.py`.
- Compare groups of sessions (context, weighted cost per user request, compactions) with `python3 -I scripts/compare_sessions.py out.json`.
- The thresholds here (300K, 3 tool calls / 6,000 characters, 2–3 workers, when to use a worktree, the 6,000-character brief, the 3-line hand-back, the tier table, the single-track route and its 3,000-character one-page brief, the assigned worker and its ~150K replacement point, the reviewer only before high-risk merges) are hypotheses: log what happened in the handoff note and adjust.
- **Comparing rule versions** (e.g. v0.2 vs v0.3, or runner used vs not used): run the same small fixed task — 2 wording swaps + 1 logic fix (2 files) + a merge + a full test run — from the same commit, each in a new worktree and new session with the same request text; at least 2 tasks × 2 runs each (one run is mostly noise). Collect with `scripts/session_tokens.py --json`:
  - main session peak context and request count
  - per-model subagent requests, input (incl. cache reads) and output
  - tokens a worker read before its first edit
  - runner : helper : worker call ratio, escalations (runner → helper, helper → worker)
  - wrong results (reported count ≠ re-run count)
  - number of full build/test runs
  - problems the reviewer found (duplicates, unowned follow-ups, trailer), rework briefs
  - wall time (active minutes), user corrections
- **Assigned worker vs new worker** (v0.3.2, not measured yet): take 2–3 jobs that continue one another in one project and run them from the same commit with the same briefs — once with one assigned worker continued by SendMessage, once with a new worker per job. Compare per job and in total: first-turn input (new + cache write + cache read), total input (also weighted: new 1, cache write 1.25, cache read 0.1), request and tool-call counts, accuracy (each job's Verify passes; reported numbers match a re-run). Keep the assigned worker only if weighted input drops 10% or more with equal accuracy; otherwise use new workers and say so in the README.
- Adopt a change only if weighted cost (model price × tokens) and rework both go down. If cost drops but rework rises, loosen the "read only the brief" rule and the tier table first. If a runner ever reports "pass" for a run that actually failed, move test runs back to helper.
