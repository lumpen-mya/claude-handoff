# claude-handoff

**Stop paying for long context.** A Claude Code plugin that keeps the main session for conversation only, pushes all work to subagents (one Opus lead that works alone by default, tiered workers only when the work must be split, a reviewer, a helper, a runner), and carries state in markdown notes — handing off to a fresh session at task boundaries. Based on NVIDIA's *"You don't need long context"* (2026) and our own session measurements.

![license](https://img.shields.io/badge/license-MIT-blue) ![status](https://img.shields.io/badge/status-experimental%20v0.3.3-orange) ![claude code](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2)

> In the paper, frequent structured compaction kept Opus accuracy within **−3.7 to +5.6 pp** of baseline while estimated cost fell **2.2–8.8×**; selective reading of long inputs cut estimated cost **6.5–54×**. This skill turns those findings into a daily workflow.

**Install (one line, in your terminal):**
```
claude plugin marketplace add lumpen-mya/claude-handoff && claude plugin install handoff@claude-handoff
```
Or just tell Claude: *"install the lumpen-mya/claude-handoff plugin"*. Then type `/handoff`.

> **Status: experimental (v0.3.3).** Thresholds are hypotheses being measured in real work — please try it and leave feedback ([Feedback](#feedback)).

## Evidence

| Claim used in this skill | Source |
|---|---|
| Frequent compaction keeps accuracy near baseline on long-horizon tasks (Opus 4.5: −3.7 to +5.6 pp) | NVIDIA §3, Fig. 5 |
| A good compaction is a handoff brief (objective, facts, changes, verification, dead ends, plan), not a recap | NVIDIA App. A, prompt App. G.1 |
| Most long-input savings come from selective reading (grep → read a range), not compaction | NVIDIA §4, App. F |
| Under flat retail pricing, compacting too often can cost more (cache loss) → compact at task boundaries | NVIDIA App. C, Tables 3 & 5 |
| Turning repeated work into SOPs/scripts cuts tokens −79% to −90% on reruns | GenericAgent §4.4, Table 8 |
| Rules-only memory beats full SOP text (66.5% vs 52.4%) | GenericAgent §4.3.2, Table 5 |
| File-based navigation improves accuracy (+17.3% avg), but is not cheaper than RAG | Coding Agents…, Table 1, Table 5 |

The numbers above are from the papers; our own measurements are below.

**Not yet evidenced (our hypotheses):** that the main-session-talks setup keeps context under ~300K for a whole task, and the worker limits (2–3 at once, worktree only when files could collide). Also unmeasured: the v0.3.3 delegation conditions (when the lead should split, e.g. ~300K lead context), the 4-agent limit, the generalised worker tiers, and the reviewer only before high-risk merges; continuing one agent by SendMessage has only a small-sample first check (see below). The lead-alone default rests on one task (3 runs). We are measuring this.

## Install

Terminal:
```
claude plugin marketplace add lumpen-mya/claude-handoff && claude plugin install handoff@claude-handoff
```
Inside Claude Code:
```
/plugin marketplace add lumpen-mya/claude-handoff
/plugin install handoff@claude-handoff
```
Or copy `plugins/handoff/skills/handoff/` to `~/.claude/skills/handoff/`.

## What it does

**The main session talks, the lead works.** Only markdown paths and short summaries reach the main session (path + 3 lines from the lead, workers, helpers and runners; up to 10 lines from a lead that delegated).

| Role | Agent | Model |
|---|---|---|
| Main conversation | your session | Sonnet 5.5 — copy `examples/settings.json` to `<project>/.claude/settings.json` |
| Lead: does the whole job alone by default (reads, implements, tests, commits); splits it only when the delegation conditions hold | `handoff-lead` | Opus 5.5 |
| Worker, Opus tier: delegated modules with many empty/boundary/undo branches | `handoff-worker-opus` | Opus 5.5 |
| Worker, Sonnet tier: delegated ordinary modules | `handoff-worker` | Sonnet 5.5 |
| Worker, Haiku tier: delegated trivial modules | `handoff-worker-haiku` | Haiku 5.5 |
| Reviewer: only before a high-risk merge or push — re-checks commits, diffs, verification | `handoff-reviewer` | Opus 5.5 |
| Helper: chores that need a little thought — summaries, screenshot checks, wording swaps inside a named range, merges | `handoff-helper` | Haiku 5.5 |
| Runner: fixed commands only — git status/log, test runs → pass/fail counts, file checks; no judgment or edits | `handoff-runner` | Haiku 5.5 |

- **Task folder** `~/.claude/handoffs/tasks/YYYY-MM-DD-<slug>/` holds `result-N-*.md`, `delegation.md`, `handoff.md`, and when the lead delegates `plan.md`, `brief-N-*.md`, `modules/<module>/interface.md`, `review.md`.
- **Lead works alone by default** (v0.3.3, D1): 3 tool calls or fewer → the main session does it; everything else → one Opus lead, which implements, tests and commits itself. v0.3.2's single-track route (main writes a one-page brief straight to a worker) is removed: its cost effect was never measured and D1 covers that work.
- **Delegation only when needed** (v0.3.3, D2/D4, thresholds are an untested estimate): the lead splits only when at least two hold — 3 or more independent tracks, each large / its context likely to pass ~300K tokens / parallel work would save a lot of time — and records the decision in `delegation.md` (delegated or not, why, context size).
- **When it delegates** (v0.3.3, C rules from the experiment): six-item briefs (who / what / when / where / why / how, 2,500 characters or less) with the module's spec sentences as a checklist; interfaces of 800 characters or less stating side effects; workers read only their brief and interfaces, ask the lead at most 6 times, run their module tests and report a pass/fail table; the lead re-checks the table and re-runs the tests before the next bundle. Worker tier per module, fixed by the lead: many empty/boundary/undo branches → Opus, ordinary → Sonnet, trivial → Haiku (generalised from a fixed per-module list; in one run the general version cost ~27% more). Workers + helpers: 4 at most.
- **One-line commands** (v0.3.3, lead and workers): no `&&`, `;`, pipes, redirects, heredoc scripts or `git -C <absolute path>`; read big output with `tail` / `grep -n`; read ranges, not whole files. In the experiment, compound commands were the main source of automatic permission denials.
- **Short output** (v0.3.3, lead): edit only what changed, never re-paste, no progress narration, final report 5 lines or less. Experiment A4 (3 runs, one task): cost about −12%, cache reads −21%.
- **3-line hand-back** (v0.3): result notes start with `Done:` / `Next:` (3 lines each) / `Blocked:`; agents return the path + 3 lines.
- **Tool allowlists** (v0.3.1): every agent has a `tools:` line (Read, Bash, Glob, Grep; Edit/Write only where the role needs them; no MCP or browser tools). In our logs this was roughly the difference between a ~11K and a ~55K first turn (n=1 sample, direction only).
- **Small jobs stay in main** (v0.3.1): a job expected to take 3 tool calls or fewer and return about 6,000 characters or less is done by the main session itself — every delegation pays a fixed first turn. The runner is for fixed commands that repeat.
- **Big results by excerpt** (v0.3.1): logs, diffs and canvases stay in a file and only the needed lines are read.
- **Continue, don't respawn** (v0.3.2, first check on a small sample): follow-up work in one project goes to the same lead by SendMessage (a delegated bundle's follow-up to its worker). An agent being replaced writes a takeover note (done / next / blocked / pointers).
- **Short relay and no polling** (v0.3.2/v0.3.3): the main session passes reports on as the path + 3 lines, does not answer a repeated completion notice, and never polls agent status in a loop (one wait of at most 5 minutes, then one check).
- **Reviewer and tests** (v0.3.2): the reviewer runs only before a high-risk merge or push (2 or more branches, a shared or production branch, security, permissions, payments, data migrations). When the lead delegated, the full test runs once after all bundles are done.
- **Concise answers**: conclusion and key points only.
- **Handoff note** at a task boundary, in 7 parts: objective, established facts, applied changes, verification, dead ends, remaining plan, environment. Never overwrites existing notes — appends and records corrections.
- **Check step** before continuing: preservation, format, facts (commits/paths/push), unverified marks, conflicts with existing docs (suggested, not applied), promotion of confirmed decisions (with user confirmation).

Use: type `/handoff`, or say "hand this off" / "start a fresh session".

## Our measurements (49 sessions, not a controlled study)
- A fresh start from a handoff note begins at ~100K tokens, right after auto-compaction ~125K — then **both grow 50–80K every 50 calls** when the session does the work itself. A handoff alone does not keep context small.
- ~80% of the growth was command output, screenshots and lookups; assistant text ~4%.
- Output tokens per call were flat (~600) regardless of session length; cost differences come from input.
- Sessions started from a brief or handoff cost about half per user request compared with long sessions (weighted tokens), with zero auto-compactions — small sample, selection bias likely.
- Reproduce on your own history: `python3 -I plugins/handoff/skills/handoff/scripts/compare_sessions.py out.json`.
- **v0.3 effects are estimates, not measured yet.** Expected: less reading per worker (self-contained briefs), a smaller main session (3-line hand-backs), fewer Opus calls (runner/helper tiers), fewer full test runs. Planned check: the same small fixed task under v0.2 and v0.3 rules (and with/without the runner), at least 2 tasks × 2 runs, comparing main peak context, per-model tokens, escalations, wrong results, rework briefs and time — see "Measure" in `SKILL.md`.
- **Subagent first turn** (one session, 28 subagents, 2026-11-12, read from logs): ~10.8K input tokens for the one agent with a `tools:` allowlist (n=1) vs ~55K for agents with every tool. Two delegated jobs of 3–4 tool calls cost ~64K new input each.
- Counting new input only, delegation cost more in every case we logged; the gain is the reading that never enters the main session's cache.
- A break-even analysis measured on another project (delegation paying off after roughly 21 / 8 / 6 tool calls at 100K / 200K / 300K of main context) uses different assumptions and **did not reproduce on our logs**; we do not rely on those numbers.
- **v0.3.1 A/B** (same read-only task, old vs new agent definitions, headless CLI, 1–2 runs each per cell, hv030 vs hv031 only): first-turn input worker 22K → 7K, lead 22K → 8K, helper 23K → 7K; answers identical (4/4), no escalations. *Confirmed* in this setup: lower first-turn input and same answers. *Estimated*: the benefit in real sessions, since headless first-turn values are lower than the app's (~55K) and absolute numbers differ by environment. *Unconfirmed*: the runner old/new comparison (n=1; no old-runner baseline in the rerun, and in the first test Haiku added options to a command on its own). Direction check, not statistics.
- **v0.3.2 basis before the first check (estimate).** Basis then: in one session a lead continued twice by SendMessage began its turns at 55K → 112K → 117K input (103K and 112K of it cache reads), while a new allowlisted agent starts at ~11K — so the assigned worker pays off only if it saves more re-reading than its larger cached context costs, and a continuation after the cache expires pays that context again as new input. Planned check: 2–3 jobs that continue one another, run once with an assigned worker and once with a new worker per job, comparing first-turn input, total input (weighted), call counts and accuracy — see "Measure" in `SKILL.md`; results in the next item.
- **v0.3.2 first check** (3 jobs that continue one another on a small fixture, headless CLI, 2 runs per arm): weighted subagent input 38K with one assigned worker vs 43K with a new worker per job (ratio 0.88) — the assigned worker used less; tool calls 18.5 vs 21.5; all jobs correct (12/12); first turn of the assigned worker grew ~8.0K → 11.7K → 14.9K across jobs. Route questions scored 10/12 with the first wording (below the 11 bar; items 2 and 5 wrongly went to lead), stayed 10/12 after the first fix, and reached 12/12 after the second wording fix — so that figure was tuned to the test and may be optimistic. Direction check only (small sample, 2 runs per arm; effect of the assigned worker: confirmed, small sample): the fixture is small, so re-reading costs less than in real projects, and headless numbers differ from the app. Still not measured: large jobs, real apps, the ~150K replacement point, and cost in dollars; the route-question score comes from 2 runs per wording after fixes, so it may be optimistic.
- **v0.3.3 basis** (one 12-module task with 332 hidden tests, headless CLI, estimated prices, 3 runs per condition unless noted; see `docs/experiments/`): Sonnet main + Opus lead working alone (D) 332×3, $11.7 average — the lead never delegated; delegated structure with fixed per-module worker tiers (C6) 332×3, $12.6; Opus solo $13.7; v0.3.2 structure (Sonnet main / Fable lead / Opus workers) $19.1. Single-variable checks: short output (A4) about −12% cost in 3 runs; letting the lead pick tiers from the general rule (C6T, 1 run) put all 4 workers on Opus, +27% over the C6 average at the same score. Failures were mostly operational (permission denials on compound commands, status polling, missing brief items). One task only; $1–2 differences may be noise.

## Feedback

This is a work in progress. Please try it and tell us:
- Did the handoff note let the new session continue without re-exploring?
- Token/time before vs after (rough numbers are fine)
- When splitting into sessions helped or hurt (task size, number of files, number of workers)
- Anything that broke, or rules that felt wrong

Open an [issue](https://github.com/lumpen-mya/claude-handoff/issues) (reviews and short reports welcome).

---

## 한국어

> **지금 실험 중인 v0.3.3입니다.** 써 보시고 후기를 남겨 주세요. [Issues](https://github.com/lumpen-mya/claude-handoff/issues)에 짧게 적어 주셔도 됩니다.

**근거 요약**
- 작업 경계에서 압축하면 긴 작업에서도 정확도가 거의 그대로였습니다. Opus 4.5 기준 기준 대비 −3.7~+5.6pp입니다. (NVIDIA §3)
- 좋은 압축은 회고가 아니라 인수인계입니다. (NVIDIA 부록 A, G.1)
- 비용 절감은 대부분 압축이 아니라 필요한 부분만 골라 읽는 데서 나왔습니다. (NVIDIA §4)
- 너무 자주 압축하면 캐시가 깨져서 오히려 비싸질 수 있습니다. (NVIDIA 부록 C)
- 반복 작업을 절차나 스크립트로 고정하면 토큰이 79~90% 줄었습니다. (GenericAgent §4.4)
- **아직 근거가 없는 가설:** 메인이 대화만 하면 작업 내내 300K 아래로 유지된다는 것, v0.3.3의 위임 조건(리드 컨텍스트 약 30만 토큰 등), 에이전트 4개 제한, 일반화한 워커 등급, 위험할 때만 검토도 아직 재지 않았습니다. SendMessage로 같은 에이전트를 이어 쓰는 것은 소표본 첫 확인만 있습니다(아래). 리드 혼자 작업 기본값은 한 과제(3회) 결과에 기댑니다. 지금 실측하고 있습니다.

**후기로 알려 주시면 좋은 것**
- 새 세션이 다시 탐색하지 않고 바로 이어갔는지
- 쓰기 전과 후의 토큰·시간 (대략적인 숫자도 괜찮습니다)
- 세션을 나눠서 이득이었던 경우와 손해였던 경우
- 고장 난 부분이나 어색한 규칙

**짧은 컨텍스트로 일하기 위한** Claude Code 플러그인입니다. 메인 세션은 대화만 하고 작업은 서브에이전트가 맡으며, 작업이 끝나는 시점에 구조화된 인수인계 노트로 압축해 새 세션에서 이어갑니다.

근거는 NVIDIA 논문 ["You don't need long context"](https://arxiv.org/abs/2611.05306)입니다. 작업 경계에서 인수인계 형식으로 압축하면 정확도는 거의 그대로이고 비용은 줄어듭니다.

**설치 (터미널 한 줄)**
```
claude plugin marketplace add lumpen-mya/claude-handoff && claude plugin install handoff@claude-handoff
```
또는 Claude에게 "lumpen-mya/claude-handoff 플러그인 설치해줘"라고 말하면 됩니다.

**주요 동작 (v0.3.3)**
- **메인은 대화만, 일은 리드가:** 메인에는 md 경로와 짧은 요약만 옵니다(리드·워커·잡일·실행 담당은 경로+3줄, 위임한 리드는 10줄 이내).
  - 메인 대화: Sonnet 5.5 (`examples/settings.json`을 프로젝트 `.claude/settings.json`으로 복사)
  - 리드 `handoff-lead` (기본은 혼자 구현·테스트·커밋, 위임 조건이 맞을 때만 나눔): Opus 5.5
  - 워커 Opus 등급 `handoff-worker-opus` (빈·경계·되돌리기 분기가 많은 모듈): Opus 5.5
  - 워커 Sonnet 등급 `handoff-worker` (일반 모듈): Sonnet 5.5
  - 워커 Haiku 등급 `handoff-worker-haiku` (사소한 모듈): Haiku 5.5
  - 검토 `handoff-reviewer` (위험이 큰 병합·푸시 전에만): Opus 5.5
  - 잡일 `handoff-helper` (요약·비교, 캡처 확인, 지정 범위의 문구 교체·간단한 정리, 병합): Haiku 5.5
  - 실행 담당 `handoff-runner` (정해진 명령만 실행하고 숫자만 보고, 판단·수정 안 함): Haiku 5.5
- **기본은 리드 혼자 (v0.3.3, D1):** 도구 호출 3회 이하는 메인이 직접 하고, 나머지는 전부 Opus 리드 한 명에게 넘겨 리드가 혼자 구현·테스트·커밋합니다. v0.3.2의 한 갈래 경로(메인이 한 장짜리 지시서를 써서 워커에게 바로)는 뺐습니다. 비용 효과를 잰 적이 없고 D1이 그 일을 맡기 때문입니다.
- **필요할 때만 위임 (v0.3.3, D2·D4, 문턱은 미시험 추정):** 서로 독립인 큰 갈래 3개 이상 / 리드 컨텍스트 약 30만 토큰 초과 예상 / 병렬로 시간을 크게 줄임 — 이 중 둘 이상일 때만 나누고, 판단은 `delegation.md`에 한 줄(위임함/안 함, 이유, 컨텍스트 크기)로 남깁니다.
- **위임할 때 (v0.3.3, 실험의 C 규칙):** 육하원칙 지시서(2,500자 이하)에 담당 모듈 spec 문장을 체크리스트로 그대로 옮기고, 인터페이스(800자 이하)에 부수효과를 적습니다. 워커는 지시서와 인터페이스만 읽고, 리드에게 최대 6번 묻고, 모듈 테스트를 돌려 통과/실패 표를 냅니다. 리드는 표를 확인하고 테스트를 한 번 돌린 뒤에만 다음 묶음으로 갑니다. 워커 등급은 리드가 고정: 빈·경계·되돌리기 분기가 많으면 Opus, 일반은 Sonnet, 사소하면 Haiku(모듈별 고정 목록을 일반 규칙으로 바꾼 것, 1회 시험에서 일반 규칙 쪽이 약 27% 더 비쌌음). 워커·헬퍼 합계 4 이하.
- **한 줄 명령 (v0.3.3, 리드·워커):** `&&`·`;`·파이프·리다이렉트·여러 줄 스크립트·`git -C 절대경로`를 쓰지 않고, 큰 출력은 `tail`·`grep -n`으로, 파일은 필요한 구간만 읽습니다. 실험에서 자동 권한 거부는 주로 이어 붙인 명령에서 났습니다.
- **출력 줄이기 (v0.3.3, 리드):** 바뀐 부분만 고치고, 보여 준 내용을 다시 붙이지 않고, 중간 보고 없이 마지막 보고만 5줄 이내로 씁니다. 실험 A4(한 과제 3회): 비용 약 −12%, 캐시 읽기 −21%.
- **돌려주기는 3줄 (v0.3):** 결과 노트 맨 위에 `Done:`·`Next:`(각 3줄 이내)·`Blocked:`를 두고, 메인에는 경로+3줄만 돌려줍니다.
- **도구 허용 목록 (v0.3.1):** 모든 에이전트에 `tools:` 줄을 둡니다(Read·Bash·Glob·Grep, 역할에 필요할 때만 Edit·Write, MCP·브라우저 도구 없음). 우리 로그에서는 첫 턴이 약 55K에서 약 11K로 달라졌습니다(표본 1, 방향 확인용).
- **작은 일은 메인이 직접 (v0.3.1):** 도구 호출 3회 이하·출력 6,000자 이하로 예상되는 일은 맡기지 않고 메인이 합니다. 맡길 때마다 첫 턴 고정 비용이 들기 때문입니다. 실행 담당은 정해진 명령을 반복하는 일에만 씁니다.
- **큰 결과는 필요한 부분만 (v0.3.1):** 로그·diff·캔버스는 파일에 두고 필요한 줄만 읽습니다.
- **새로 띄우지 말고 이어 쓰기 (v0.3.2, 소표본 첫 확인):** 한 프로젝트에서 이어지는 일은 같은 리드에게 SendMessage로(위임한 묶음의 후속은 그 워커에게) 맡깁니다. 바꿀 때는 인수 노트(한 일·다음 할 일·막힌 것·위치)를 받습니다.
- **짧은 중계·조회 금지 (v0.3.2·v0.3.3):** 메인은 보고를 경로+3줄로만 전하고, 되풀이되는 완료 알림엔 답하지 않으며, 에이전트 상태를 반복 조회하지 않습니다(최대 5분 한 번 기다리고 한 번 확인).
- **검토와 시험 (v0.3.2):** 검토는 위험이 큰 병합·푸시 전에만 합니다(브랜치 2개 이상 병합, 공유·운영 브랜치, 보안·권한·결제·데이터 이전). 리드가 위임했으면 전체 시험은 모든 묶음이 끝난 뒤 한 번 돌립니다.
- **작업 폴더:** `~/.claude/handoffs/tasks/날짜-작업명/`에 지시서·결과·검토·인수인계 md를 둡니다.
- **답변은 간결하게:** 결론과 핵심만 답합니다.
- **인수인계 노트 7항목:** 목표, 확인된 사실, 적용한 변경, 검증, 막다른 길, 남은 계획, 환경. 기존 파일은 덮어쓰지 않고 덧붙이기와 정정만 합니다.
- **이어가기 전 점검:** 기존 내용 보존, 형식, 커밋·경로 사실 확인, '미확인' 표시, 기존 문서와의 충돌(권장안만 제안), 확정된 결정의 메모리·스펙 승격 후보(확인 후 반영).

**직접 잰 수치 (49세션)**
- 핸드오프로 새로 시작하면 약 100K, 자동 압축 직후는 약 125K입니다. 그 뒤 세션이 직접 작업하면 둘 다 50호출마다 50~80K씩 커집니다.
- 커진 양의 약 80%는 명령 출력·스크린샷·조회 결과였습니다.
- 출력 토큰은 호출당 약 600으로 세션 길이와 무관했습니다.
- **v0.3의 효과는 아직 추정입니다(측정 전).** 같은 작은 과제를 v0.2·v0.3 규칙으로(실행 담당 사용·미사용도) 최소 2과제×각 2회 돌려, 메인 최고 컨텍스트·모델별 토큰·승급 횟수·틀린 결과·재작업 수·시간을 비교할 계획입니다. 방법은 `SKILL.md`의 Measure에 있습니다.
- **서브에이전트 첫 턴 (한 세션·28개, 2026-11-12, 로그 기준):** `tools:` 허용 목록이 있는 에이전트는 약 10.8K(표본 1), 모든 도구를 가진 에이전트는 약 55K였습니다. 도구 3~4회짜리 위임 2건은 신규 입력이 각각 약 64K였습니다.
- 신규 입력만 보면 위임은 기록된 모든 경우에 더 비쌌습니다. 이득은 메인 세션 캐시에 쌓이지 않는 읽기에서 나옵니다.
- 다른 프로젝트에서 잰 손익분기(메인 100K·200K·300K에서 약 21·8·6회부터 위임이 이득)는 계산 가정이 달라 **우리 로그로는 재현되지 않았습니다.** 이 수치에는 기대지 않습니다.
- **v0.3.1 구/신 비교** (같은 읽기 전용 과제, 헤드리스 CLI, 칸마다 1~2회, hv030 대 hv031 비교뿐): 첫 턴 입력이 워커 22K → 7K, 팀장 22K → 8K, 잡일 23K → 7K였고 답은 같았으며(4/4) 승급은 없었습니다. **확인됨**: 이 환경에서 첫 턴 입력 감소와 같은 답. **추정**: 실제 세션에서의 이득(헤드리스 첫 턴 값은 앱(~55K)보다 낮고 절대값은 환경마다 다름). **미확정**: runner 구/신 비교(n=1, 재시험에는 구 runner 기준값 없음, 첫 시험에서 Haiku가 명령에 옵션을 임의로 붙인 사례 있음). 통계가 아니라 방향 확인용입니다.
- **첫 확인 전 v0.3.2의 근거(추정).** 당시 근거는 한 세션에서 팀장 하나를 SendMessage로 두 번 이어 쓴 기록뿐입니다(첫 턴 입력 55K → 112K → 117K, 그중 103K·112K는 캐시 읽기). 새 에이전트는 약 11K에서 시작하므로, 담당 워커는 다시 읽기를 그보다 많이 아낄 때만 이득이고 캐시가 만료된 뒤 이어 쓰면 그 컨텍스트를 새 입력으로 다시 냅니다. 이어지는 일 2~3건을 담당 워커 방식과 새 워커 방식으로 돌려 첫 턴 입력·총 입력(가중)·호출 수·정확도를 비교할 계획입니다. 방법은 `SKILL.md`의 Measure에 있고, 결과는 다음 항목입니다.
- **v0.3.2 첫 확인** (작은 시험용 저장소에서 이어지는 일 3건, 헤드리스 CLI, 방식마다 2회): 서브에이전트 가중 입력은 담당 워커 38K, 일마다 새 워커 43K(비 0.88)로 담당 워커 쪽이 적었습니다. 도구 호출 18.5 대 21.5, 정답 12/12, 담당 워커의 첫 턴은 일마다 약 8.0K → 11.7K → 14.9K로 늘었습니다. 경로 문답은 첫 문구로 10/12(합격선 11 미달, 문항 2·5가 lead로 오답), 1차 수정 후에도 10/12, 2차 문구 수정 후 12/12였으므로 시험 결과에 맞춰 문구를 고친 수치라 낙관적일 수 있습니다. 방향 확인용입니다(담당 워커 효과: 확인됨(소표본), 방식마다 2회): 시험용 저장소가 작아 다시 읽는 비용이 실제보다 작고, 헤드리스 수치는 앱과 다릅니다. 아직 재지 않은 것: 큰 작업·실제 앱에서의 효과, 약 150K 교체 기준, 비용(달러). 경로 문답 점수는 문구 수정 후 문구마다 2회뿐이라 낙관적일 수 있습니다.
- **v0.3.3 근거** (12모듈·숨긴 테스트 332개 과제 하나, 헤드리스 CLI, 추정 단가, 따로 적지 않으면 조건마다 3회, `docs/experiments/` 참고): Sonnet 메인 + Opus 리드 혼자(D) 332×3·평균 $11.7(리드는 한 번도 위임하지 않음), 모듈별 고정 등급 위임(C6) 332×3·$12.6, Opus 단독 $13.7, v0.3.2 구조(Sonnet 메인/Fable 리드/Opus 워커) $19.1. 단독 변수 시험: 출력 줄이기(A4) 3회 약 −12%, 리드가 일반 규칙으로 등급을 고르게 한 1회(C6T)는 워커 4개 모두 Opus로 C6 평균보다 +27%, 점수는 같음. 실패는 대부분 운영 문제(이어 붙인 명령의 권한 거부, 상태 반복 조회, 지시서 누락)였습니다. 한 과제뿐이라 $1~2 차이는 노이즈일 수 있습니다.

## License
MIT
