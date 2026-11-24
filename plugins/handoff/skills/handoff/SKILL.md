---
name: handoff
description: Keep the main session small. The main session only talks with the user; by default one lead subagent (Opus) does the whole job itself — reads, implements, tests, commits — and splits it into worker briefs only when the delegation conditions hold; only short summaries plus markdown paths come back. At a task boundary, compress the work into a structured handoff note and continue in a fresh session. Use when the user says /handoff, "hand this off", "start a fresh session", "compact and continue", "새 세션으로 넘겨", "정리하고 새로 열어", when starting a multi-step task in a project that uses this setup, or when a titled piece of work is finished and the conversation has grown long.
---

# handoff — the main session talks, the lead works, notes carry the state

## Why
- Every call re-sends the whole conversation of that session. Whatever the session reads or runs stays in it and is paid for again on every later call.
- Measured on our own sessions (49 sessions, 2026-09 to 2026-11, `scripts/compare_sessions.py`):
  - A fresh start from a handoff note begins at ~100K tokens; right after auto-compaction it is ~125K. From there **both grow by 50–80K every 50 calls** if the session does the work itself.
  - About 80% of that growth was command output, screenshots and lookups; the assistant's own text was ~4%.
  - Output tokens per call were the same everywhere (~600). Cost differences come from input.
  - Subagent first turn (2026-11-12, one session, 28 subagents, n=1 for the allowlisted agent): ~10.8K input tokens with a `tools:` allowlist vs ~55K without; two delegated jobs of 3–4 tool calls cost ~64K new input each.
- So a handoff alone is not enough. The context stays small only if the work happens somewhere else: in subagents, whose reading never enters the main session.
- Why one lead working alone is the default (v0.3.3): on one 12-module task (T5, 332 hidden tests, estimated prices, 3 runs each) Sonnet main + Opus lead alone (D) scored 332×3 at $11.7 average; the delegated structure with worker tiers (C6) scored 332×3 at $12.6; Opus solo (A) $13.7; the earlier v0.3.2 structure (Sonnet main / Fable lead / Opus workers, B) $19.1. Splitting never clearly beat working alone at this size; coordination was the main extra cost. One task only — do not generalise far.
- Paper basis for the note format and for compacting at task boundaries: Belcak et al., "You don't need long context" (NVIDIA, arXiv 2611.05306). Sources and details: `reference.md` (read only when needed).

## Roles and models
| Role | Who | Model | Does |
|---|---|---|---|
| Main | the session the user talks to | Sonnet 5.5 (`claude-sonnet-5-5`) | Talks, relays paths, asks questions; does jobs inside the direct-handling threshold; hands everything else to the lead. No large file reads, long commands or big diffs |
| Lead | `handoff-lead` | Opus 5.5 (`claude-opus-5-5`) | Default: does the whole job alone — reads, implements, tests, commits (D1). Only when the delegation conditions hold (D2): splits into modules, writes interfaces, six-item briefs with a fixed worker tier, checks each worker's result and tests |
| Worker, Opus tier | `handoff-worker-opus` | Opus 5.5 | Delegated modules with many empty, boundary or undo branches |
| Worker, Sonnet tier | `handoff-worker` | Sonnet 5.5 | Delegated ordinary modules |
| Worker, Haiku tier | `handoff-worker-haiku` | Haiku 5.5 (`claude-haiku-5-5`) | Delegated trivial modules (one- or two-line edits) |
| Reviewer | `handoff-reviewer` | Opus 5.5 | Only before a high-risk merge or push: re-checks commits, diffs and the verify log. No code edits |
| Helper | `handoff-helper` | Haiku 5.5 | Chores that need a little thought — summarising/comparing results, checking screenshots, wording swaps inside the range a brief names, simple tidy-ups, finding cause candidates in logs, merging non-overlapping branches. No other edits |
| Runner | `handoff-runner` | Haiku 5.5 | Fixed commands that repeat — the same verbatim command set run several times or over several targets (more than 3 tool calls in total, or long output sent to a file), checkable by numbers/output; returns the numbers. No judgment, interpretation, summaries or code edits |

- The agents ship with this plugin with their models pinned. Set the main model per project: copy `examples/settings.json` to `<project>/.claude/settings.json`.
- All agents carry a `tools:` allowlist (base Read, Bash, Glob, Grep; lead and workers: + Edit, Write; helper: + Edit; runner and reviewer: base only). No MCP or browser tools. Reason: it cut the fixed first turn of a subagent from ~55K to ~11K input tokens in our logs (n=1 sample, direction only).
- A project may define its own agents with the same roles (project rules baked in); use those instead when they exist.

## Rules for the main session
1. **Mostly talk.** Do not read large files, run long commands or review big diffs. Allowed directly: answering from what is already known, relaying a path, asking the user a question, and a job inside the direct-handling threshold.
   - **Direct-handling threshold**: a job expected to take 3 tool calls or fewer and return about 6,000 characters or less (a short file read, one to three commands whose output is passed on as-is) — the main session does it itself; no subagent.
   - If a direct job grows (a 4th call is needed, or output passes 6,000 characters), stop and hand the rest to the lead. These thresholds (3 calls, 6,000 characters) are hypotheses.
2. **Everything larger goes to one lead (D1).** Pass "the user's request (near-verbatim) + task folder" to `handoff-lead`. The lead works alone by default and decides itself whether to delegate (D2), recording the decision in `delegation.md` (D4). The main session never writes briefs, never splits work and never picks worker tiers.
   - **Runner, direct**: read-only fixed commands that repeat (as in the Runner row) may go straight to `handoff-runner` with an instruction of 3 lines or less (no brief, no file edits).
   - (v0.3.2's single-track route — the main session writing a one-page brief straight to a worker — is removed in v0.3.3: D1 sends all non-direct work to the lead, and that route's cost effect was never measured.)
3. **Pass paths, not content (C7).** Read only the lead's result path and its 3 lines. Relay a lead's or worker's report to the user as the path + 3 lines at most — never re-paste or re-summarise the note. If the same completion notice arrives again (same agent, same result path, nothing new), do not answer it.
4. **Wait without polling (C1).** 대기: 에이전트를 띄운 뒤 상태를 반복 조회(ListAgents, ls 반복)하지 않는다. 한 번 기다리고(sleep 300 같은 명령 1회, 최대 5분) 끝났는지 한 번 확인, 아니면 다시 같은 방식으로 기다린다. 5분마다 한 줄로만 보고한다. (In the app, background completion notices make waiting unnecessary; this matters most in headless runs.)
5. **Answer concisely.** Conclusion and key points only. Tables and background only when the user asks. Never re-paste what was already shown.
6. **One task = one title.** Name the task in one line. A request outside it becomes a new task folder (and, when the conversation is long, a new session).
7. Subagents cannot start subagents: when the lead delegates, the main session starts each worker named in the lead's briefs, in the briefs' order (C2 "언제"), and carries messages between the lead and the workers by SendMessage (worker questions under C6, the lead's answers and re-briefs under C14/C16). It does not read briefs, interfaces, sources or logs itself.

## Workflow
1. **Open a task folder**: `~/.claude/handoffs/tasks/YYYY-MM-DD-<slug>/`. Everything below is written there.
2. **Lead**: pass the user's request (near-verbatim) and the folder. Follow-up work in the same project goes to the same lead by SendMessage while it is available.
3. **Lead works alone (default, D1)**: implements, tests, commits, writes `result-<N>-<slug>.md` and returns the path + 3 lines. Rules it follows while working: one-line simple commands, narrow reading, big output to a file (C8–C12), short output (D5).
4. **Lead delegates (only when D2 holds)**: it writes `delegation.md`, `plan.md`, one interface per module (C3) and one six-item brief per bundle (C2, with a spec checklist C13 and a worker tier C18), then returns the brief paths in order. The main session starts each worker at its tier; each returns its result path + 3 lines. The lead checks each result's checklist table and runs that module's tests before the next bundle (C14, C16); missing items go back to the same worker. Workers + helpers: 4 at most.
5. **Questions**: ask the user what the lead could not resolve. Do not let agents guess.
6. **Report as each finishes**: tell the user what landed and what is unverified as soon as an agent returns. Once per completion, as the path + 3 lines; a repeated notice gets no answer.
7. **Verify once**: when the lead worked alone, its own test run is the check. When it delegated, the full build and test suite run once after all bundles report done; failures go to the lead, which sends each to the owning worker.
8. **Reviewer** (only before a high-risk merge or push — merging 2 or more branches, pushing or deploying to a shared or production branch, or changes to security, permissions, payments or data migrations): pass the result paths and the verify log. It writes `review.md` and returns pass or the list of problems. Problems go back to the lead.
9. **Close the task**: write the handoff note (below) into the folder as `handoff.md`. The next task starts from that note only.

Things the user must see (screenshots, a rendered page) are saved in the task folder by the subagent; the main session only gives the path.

## Delegation rules (lead → workers)
The full rule text (D2–D4, C2, C3, C5, C6, C8–C18) lives in `agents/handoff-lead.md` and, for the worker side, in the three worker agents. Summary:
- **When**: D2 — at least two of: 3 or more independent tracks, each large / the lead's context likely to pass ~300K tokens / parallel work would save a lot of time. Only one → no delegation. (Estimate, not tested.)
- **Record**: D4 — one line in `delegation.md`: delegated or not, why, the context size at that moment.
- **Brief** (C2, 2,500 characters or less): 누가 (worker name) / 무엇을 (module and done criteria) / 언제 (order 1→2→3, one after another) / 어디서 (files to edit, interface paths to read) / 왜 (its role in the whole) / 어떻게 (method and verify command), plus the spec checklist copied sentence by sentence (C13), with empty and boundary inputs in it (C15). The exact brief path goes in the message (C17).
- **Interface** (C3, 800 characters or less): only the external contract — names, input/output types, up to three failure conditions, and side effects (what a call writes or changes).
- **Worker tier** (C18, generalised; fixed by the lead before the briefs): many empty/boundary/undo branches → `handoff-worker-opus`; ordinary → `handoff-worker` (Sonnet); trivial → `handoff-worker-haiku`. Caution: the experiment's full marks used a fixed per-module list; in the one run where the lead picked tiers from this general rule (C6T) it chose Opus for all 4 workers and cost about 27% more — the general version can cost more.
- **Worker side**: reads only its brief and the interfaces it names (C5, C10), one-line simple commands (C8, C9), big output to a file (C11), lists a path once (C12); asks the lead at most 6 times, one question at a time with what / why / fallback, then reports 「누락」 (C6); runs its module tests and writes a pass/fail table per checklist item, committing only when all pass (C15).
- **Lead side**: checks the table and the test file compiles (C14), re-sends only the failed items to the same worker, runs the module tests once itself before the next bundle (C16).
- **Limit**: workers + helpers together 4 or fewer (effect not verified).
- Each worker edits and stages only its own files (`git add <paths>`, never `git add -A`) and never reverts or reformats files it does not own.

## Results
`result-<N>-<slug>.md` (written by the agent) starts with this fixed block — the main session and later agents read only this block:
```
Done: (3 lines max — include commit hashes)
Next: (3 lines max — hand-offs, unverified items)
Blocked: (or "none")
```
A `## Details` section below is optional (verify numbers, the C15 checklist table for workers, out-of-scope findings, log and screenshot paths).

Large results (logs, diffs, canvases, earlier notes): never paste or read them whole — keep them in a file and read only the tail or the error lines (C11).

## Continuing and replacing an agent
- Work that continues in the same project goes to the same lead by SendMessage, so what it already read is reused. A delegated bundle's follow-up goes to the worker that owns it.
- Takeover note `takeover-<N>.md` in the task folder (written by the agent being replaced, 40 lines or less): `Done:` what was done, with commit hashes / `Next:` what to do next, starting with the immediate command or edit / `Blocked:` what is stuck, or "none" / `Pointers:` up to 10 `file:line` places worth re-opening. Ask for it at a session handoff or when an agent has failed; it is the one extra file a new agent reads besides its request or brief.
- Basis (v0.3.2 first check, small fixture, 2 runs per arm): continuing one agent by SendMessage used 0.88× the weighted input of a new agent per job, 12/12 correct. Not measured: large jobs, real apps, a replacement point.

## Escalation
- Outside its conditions or on failure, a runner or helper changes nothing, writes it under "Blocked:" and returns; the main session reruns the job one tier up (runner → helper → lead).
- A delegated worker that runs out of questions reports 「누락」; the lead fills the interface or answers and re-briefs the same bundle, and carries the missing items into the next brief (C6).

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
- Hypotheses still to check: 300K main target, 3 tool calls / 6,000 characters, the D2 delegation conditions (~300K lead context), the 4-agent limit, the generalised worker tiers (C18), the 2,500-character brief and 800-character interface, the reviewer only before high-risk merges. Log what happened in the handoff note and adjust.
- **Comparing rule versions**: run the same fixed task from the same commit, each in a new worktree and new session with the same request text; 3 runs per condition where possible (one run is mostly noise). Collect with `scripts/session_tokens.py --json`: main peak context; per-model requests, input (incl. cache reads) and output; cost at model prices; hidden-test score; permission denials; status polling calls; whether and why the lead delegated (`delegation.md`); wrong results (reported ≠ re-run); rework briefs; wall time.
- Adopt a change only if weighted cost (model price × tokens) and rework both go down at equal quality.
