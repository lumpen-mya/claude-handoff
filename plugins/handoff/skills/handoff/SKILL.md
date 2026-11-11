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
- So a handoff alone is not enough. The context stays small only if the work happens somewhere else: in subagents, whose reading never enters the main session.
- Paper basis for the note format and for compacting at task boundaries: Belcak et al., "You don't need long context" (NVIDIA, arXiv 2611.05306). Sources and details: `reference.md` (read only when needed).

## Roles and models
| Role | Who | Model | Does |
|---|---|---|---|
| Main | the session the user talks to | Sonnet 5.5 (`claude-sonnet-5-5`) | Talks, relays paths, asks questions. No file reads, commands or diffs |
| Lead | `handoff-lead` | Fable 5.2 (`claude-fable-5-2`) | Reads the context once, splits the work, writes briefs. No code edits |
| Worker ×N | `handoff-worker` | Opus 5.5 (`claude-opus-5-5`) | Implements one brief in its own work area, verifies, commits |
| Reviewer | `handoff-reviewer` | Opus 5.5 | Re-checks commits, diffs and verification. No code edits |
| Helper | `handoff-helper` | Sonnet 5.5 | Chores: git status, builds, lookups, screenshots. No code edits |

- The agents ship with this plugin with their models pinned. Set the main model per project: copy `examples/settings.json` to `<project>/.claude/settings.json`.
- A project may define its own agents with the same roles (project rules baked in); use those instead when they exist.

## Rules for the main session
1. **Mostly talk.** Do not read large files, run long commands or review big diffs. Allowed directly: answering from what is already known, relaying a path, asking the user a question.
   - **Direct-handling threshold**: a short file read or one or two commands whose output must be passed on as-is (about 3K tokens or less) — the main session does it itself.
   - **Delegation threshold**: anything larger, multi-step, parallel or with big output goes to a subagent. With the same model, delegating a simple read does not shrink the context and only adds call and summary cost.
   - This threshold (3K) is a hypothesis; adjust after measuring.
2. **Pass paths, not content.** Give subagents the task folder and brief paths; receive result paths and a few lines.
3. **Answer concisely.** Conclusion and key points only. Tables and background only when the user asks. Never re-paste what was already shown.
4. **One task = one title.** Name the task in one line. A request outside it becomes a new task folder (and, when the conversation is long, a new session).
5. Subagents cannot start subagents: the main session relays the lead's brief paths to the workers.

## Workflow
1. **Open a task folder**: `~/.claude/handoffs/tasks/YYYY-MM-DD-<slug>/`. Everything below is written there.
2. **Lead**: pass the user's request (near-verbatim) and the folder. The lead writes `brief-<N>-<slug>.md` per bundle and returns paths, one-line summaries, which briefs can run in parallel, and questions for the user.
3. **Questions**: ask the user what the lead could not resolve. Do not let workers guess.
4. **Workers**: start one worker per brief — in parallel when the lead marked them independent, in order otherwise. Each returns its `result-<N>-<slug>.md` path, commit hashes, pass/fail and unverified items.
5. **Report as each finishes**: tell the user what landed and what is unverified as soon as a worker returns. Never hold results until all are done.
6. **Reviewer**: pass the result paths. It writes `review.md` and returns pass or the list of problems. Problems go back to a worker as a new brief.
7. **Close the task**: write the handoff note (below) into the folder as `handoff.md`. The next task starts from that note only.

Things the user must see (screenshots, a rendered page) are saved in the task folder by the subagent; the main session only gives the path.

## Briefs and results
`brief-<N>-<slug>.md` (written by the lead):
```
Goal: one line
Owned files: the only files this worker may edit — disjoint from every other brief
Isolation: none | worktree
Changes: file:line and what to change
Do not touch: files or areas
Done when: criteria + the exact verify command
Questions: anything unknown — ask, do not guess
```
`result-<N>-<slug>.md` (written by the worker): changed files / commit hashes / verify command and its result / unverified items / out-of-scope findings / saved screenshot paths.

## Several workers, separate work areas
- The lead splits by **file ownership**: every brief lists `Owned files:` and the lists never overlap. Changes that are ordered (shared core → screens) or touch the same file stay in one brief.
- A worker edits and stages only its owned files (`git add <paths>`, never `git add -A`), and never reverts or reformats files it does not own.
- `Isolation: worktree` when owned files could still collide — lockfiles, generated files, a shared build output. Start that worker with `isolation: "worktree"`; it commits to its own branch, and afterwards the helper merges the branches one at a time.
- Practical ceiling: 2–3 workers at once, 4 at most — beyond that review becomes the bottleneck.
- Do not split 1–2 edit tasks: one brief, one worker.

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
- The thresholds here (300K, 2–3 workers, when to use a worktree) are hypotheses: log what happened in the handoff note and adjust.
