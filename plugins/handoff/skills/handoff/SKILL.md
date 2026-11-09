---
name: handoff
description: Compress a long session into a structured handoff note (markdown) and continue in a fresh session, and split work across sessions only when it pays off. Use when the user says /handoff, "hand this off", "start a fresh session", "compact and continue", "새 세션으로 넘겨", "정리하고 새로 열어", or when a titled piece of work is finished and the conversation has grown long.
---

# handoff — compact at task boundaries, continue fresh

Basis: Belcak et al., "You don't need long context" (NVIDIA, arXiv 2611.05306). Compacting at task boundaries into a structured *handoff brief* (not a narrative recap) keeps accuracy close to baseline while cutting context cost. Details and other sources: `reference.md` in this folder (read only when needed).

## Session scope (one session = one title)
1. Start: state the scope as a one-line title (rename the session to it if the client allows).
2. During: if a request falls outside the title, propose a new session instead of doing it here. Exception: tiny questions that take one or two tool calls.
3. Finish: when the titled work is done → write the handoff note → promote confirmed decisions (see check step) → check → close the session or open the next title in a new one.

## Splitting work (coordinator → worker sessions)
The coordinator reads context once and gives workers only a brief. Workers do not re-explore.
- Planning step (default for every task): while reading, split the work into independent bundles; note files, dependencies and expected size for each. Delegate only bundles that meet the criteria below; do the rest directly. Tell the user one line: "split into N (reason)".
- These records are the experiment: never run the same task twice just to compare.
- Split only when ALL hold: disjoint file sets / no bundle waits on another's result / each bundle is sizable on its own (hypothesis: 3+ files or ~20+ min).
- Don't split: 1–2 edit tasks, ordered dependencies (shared core → screens), several bundles touching the same file.
- If files may overlap, give each worker its own git worktree.
- Practical ceiling: 2–3 workers, at most 4 — beyond that review becomes the bottleneck.
- Brief must include: target file:line and the change / files not to touch / done criteria and verify command / "ask, don't guess" / report format (changed files, verification result, unverified items).
- The coordinator reviews worker diffs and re-runs verification once.
- Criteria are hypotheses: log elapsed time and tokens of delegated bundles in the handoff note and adjust.

## When to hand off
- At a task boundary only. Not mid-task — compacting too often breaks prompt caching and can raise real cost.

## Procedure
1. Write the handoff note in the format below. It is a brief for the next worker, not a retrospective.
   - Location: `~/.claude/handoffs/YYYY-MM-DD-<slug>.md`
   - **Never overwrite or delete an existing file.** If the name exists, append a `## Addendum — HH:MM` section at the end (append, not Write). Record changed facts as "Correction:" in the new section; leave the original text as is.
   - Same rule for any other markdown you update (CLAUDE.md, specs, memory): add or correct only; delete or rewrite only after the user confirms.
2. Note uncommitted changes and running processes (dev servers, emulators, ports).
3. Open the new session — only after step 4 passes.
   - Claude desktop app: start a fresh session with the brief "read `<note path>` and continue".
   - CLI: tell the user to run `claude "read <note path> and continue"`.
4. Check (before opening the new session):
   - Preservation: if you appended, the line count did not drop below the pre-write `wc -l`, and the original first line and last section heading are unchanged.
   - Format: all 7 headings exist (`grep -c`). Fill empty ones with "none".
   - Facts: commit hashes exist (`git log --oneline -1 <hash>`), paths exist (`ls`), push state matches (`git status -sb`).
   - Unverified: anything you did not check yourself is marked "unverified".
   - Conflicts: if an existing note, CLAUDE.md or memory contradicts this skill, do not edit it. List `file:line` with a "recommend changing to the skill's rule" suggestion and apply only after the user confirms.
   - Promotion: from this note, pick only decisions confirmed by execution or by the user, and propose them as candidates for durable memory (one fact per file, linked) or the project's spec docs. Exclude guesses and in-progress items. Apply only after confirmation; update existing entries by correction, never overwrite.
   - If anything fails, fix it (by appending) and check again.
5. Tell the user one line: note path, check result, new session.

## Handoff note format (based on the paper's App. G.1 prompt)
```
# Handoff — <title> (YYYY-MM-DD)
1. Objective: the user's request (near-verbatim) + preferences and corrections given during the session
2. Established facts: exact paths, symbols, commands, values, errors. Mark guesses "unverified"
3. Applied changes: per file/commit, what changed + verified? + pushed?
4. Verification: exact checks run and results
5. Dead ends: failed approaches not to repeat
6. Remaining plan: ordered subgoals, the immediate next command/edit, completion criteria
7. Environment: running servers, devices, ports, test accounts
```
- For truncated output, give a narrow command to retrieve it instead of the content. Never invent observations.
- Point to files by path and line instead of copying content.
- If the raw history is needed, grep the session transcript (`~/.claude/projects/**/*.jsonl`).
