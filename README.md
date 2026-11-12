# claude-handoff

**Stop paying for long context.** A Claude Code plugin that keeps the main session for conversation only, pushes all work to subagents (a lead, several workers with separate work areas, a reviewer, a helper, a runner), and carries state in markdown notes — handing off to a fresh session at task boundaries. Based on NVIDIA's *"You don't need long context"* (2026) and our own session measurements.

![license](https://img.shields.io/badge/license-MIT-blue) ![status](https://img.shields.io/badge/status-experimental%20v0.3.2-orange) ![claude code](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2)

> In the paper, frequent structured compaction kept Opus accuracy within **−3.7 to +5.6 pp** of baseline while estimated cost fell **2.2–8.8×**; selective reading of long inputs cut estimated cost **6.5–54×**. This skill turns those findings into a daily workflow.

**Install (one line, in your terminal):**
```
claude plugin marketplace add lumpen-mya/claude-handoff && claude plugin install handoff@claude-handoff
```
Or just tell Claude: *"install the lumpen-mya/claude-handoff plugin"*. Then type `/handoff`.

> **Status: experimental (v0.3.2).** Thresholds are hypotheses being measured in real work — please try it and leave feedback ([Feedback](#feedback)).

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

**Not yet evidenced (our hypotheses):** that the main-session-talks setup keeps context under ~300K for a whole task, and the worker limits (2–3 at once, worktree only when files could collide). Also unmeasured in v0.3.2: routing by job size and the reviewer only before high-risk merges; the assigned worker has only a small-sample first check (see below), and its effect on large jobs and real apps is unmeasured. We are measuring this.

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

**The main session talks, subagents work.** Only markdown paths and short summaries reach the main session (path + 3 lines from workers, helpers and runners; up to 10 lines from the lead).

| Role | Agent | Model |
|---|---|---|
| Main conversation | your session | Sonnet 5.5 — copy `examples/settings.json` to `<project>/.claude/settings.json` |
| Lead: reads context, splits work, writes briefs | `handoff-lead` | Fable 5.2 |
| Workers: several in parallel, each with its own `Owned files:` (git worktree when files could collide) | `handoff-worker` | Opus 5.5 |
| Reviewer: only before a high-risk merge or push — re-checks commits, diffs, verification | `handoff-reviewer` | Opus 5.5 |
| Helper: chores that need a little thought — summaries, screenshot checks, wording swaps inside a named range, merges | `handoff-helper` | Sonnet 5.5 |
| Runner: fixed commands only — git status/log, test runs → pass/fail counts, file checks; no judgment or edits | `handoff-runner` | Haiku 5.5 |

- **Task folder** `~/.claude/handoffs/tasks/YYYY-MM-DD-<slug>/` holds `plan.md`, `brief-N-*.md`, `result-N-*.md`, `review.md`, `handoff.md`.
- **Routes by job size** (v0.3.2, effect not measured): 3 tool calls or fewer → the main session does it; one track of small-to-medium work → straight to one worker with a one-page brief the main session writes from a checklist (no lead); 2 or more parallel tracks → the lead writes the briefs. The lead still writes every other brief: main writes one only when the job is a single track, every checklist item can be filled from what it already knows, and it fits 3,000 characters — otherwise, or if the worker comes back blocked, the job goes to the lead.
- **Three tiers** (v0.3): the brief's author — the lead, or the main session on the single track — sets `Model: runner | helper | worker` on each brief — runner (Haiku) for fixed commands checked by numbers, helper (Sonnet) for chores that need a little thought, worker (Opus) for everything else. When unsure, one tier up; on failure the same brief reruns one tier up.
- **Self-contained briefs** (v0.3): an agent reads its one brief and nothing else in the task folder — no "read X first"; the needed facts are excerpted (limit: 6,000 characters).
- **3-line hand-back** (v0.3): result notes start with `Done:` / `Next:` (3 lines each) / `Blocked:`; agents return the path + 3 lines.
- **Plan check** (v0.3): before returning briefs the lead checks owned-file overlap, duplicate work, unowned follow-up changes, one full test run after merging, no model names in commit trailers, tiers, and self-containment.
- **Tool allowlists** (v0.3.1): every agent has a `tools:` line (Read, Bash, Glob, Grep; Edit/Write only where the role needs them; no MCP or browser tools). In our logs this was roughly the difference between a ~11K and a ~55K first turn (n=1 sample, direction only).
- **Small jobs stay in main** (v0.3.1): a job expected to take 3 tool calls or fewer and return about 6,000 characters or less is done by the main session itself — every delegation pays a fixed first turn. The runner is for fixed commands that repeat.
- **Big results by excerpt** (v0.3.1): briefs and Agent prompts stay within 6,000 characters; logs, diffs and canvases are written to a file and only the needed lines are quoted.
- **Assigned worker** (v0.3.2, first check confirmed on a small sample; large jobs, real apps and the ~150K replacement point not measured): work that continues in one project goes to the same worker by SendMessage; parallel or unrelated work gets one-off workers. Near ~150K of context the worker writes a takeover note (done / next / blocked) and a new assigned worker starts from it.
- **Short relay** (v0.3.2): the main session passes a lead's or worker's report on as the path + 3 lines, and does not answer a completion notice that merely repeats.
- **Reviewer and tests** (v0.3.2): the reviewer runs only before a high-risk merge or push (2 or more branches, a shared or production branch, security, permissions, payments, data migrations). The full test runs once after merging; 2–3 workers run in parallel when their owned files do not overlap.
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

## Feedback

This is a work in progress. Please try it and tell us:
- Did the handoff note let the new session continue without re-exploring?
- Token/time before vs after (rough numbers are fine)
- When splitting into sessions helped or hurt (task size, number of files, number of workers)
- Anything that broke, or rules that felt wrong

Open an [issue](https://github.com/lumpen-mya/claude-handoff/issues) (reviews and short reports welcome).

---

## 한국어

> **지금 실험 중인 v0.3.2입니다.** 써 보시고 후기를 남겨 주세요. [Issues](https://github.com/lumpen-mya/claude-handoff/issues)에 짧게 적어 주셔도 됩니다.

**근거 요약**
- 작업 경계에서 압축하면 긴 작업에서도 정확도가 거의 그대로였습니다. Opus 4.5 기준 기준 대비 −3.7~+5.6pp입니다. (NVIDIA §3)
- 좋은 압축은 회고가 아니라 인수인계입니다. (NVIDIA 부록 A, G.1)
- 비용 절감은 대부분 압축이 아니라 필요한 부분만 골라 읽는 데서 나왔습니다. (NVIDIA §4)
- 너무 자주 압축하면 캐시가 깨져서 오히려 비싸질 수 있습니다. (NVIDIA 부록 C)
- 반복 작업을 절차나 스크립트로 고정하면 토큰이 79~90% 줄었습니다. (GenericAgent §4.4)
- **아직 근거가 없는 가설:** 메인이 대화만 하면 작업 내내 300K 아래로 유지된다는 것, 워커 수(동시 2~3개)입니다. v0.3.2의 일 크기별 경로·위험할 때만 검토도 아직 재지 않았습니다. 담당 워커는 소표본 첫 확인만 있고(아래), 큰 작업·실제 앱에서의 효과는 재지 않았습니다. 지금 실측하고 있습니다.

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

**주요 동작 (v0.3.2)**
- **메인은 대화만, 작업은 서브에이전트:** 메인에는 md 경로와 짧은 요약만 옵니다(워커·잡일·실행 담당은 경로+3줄, 팀장은 10줄 이내).
  - 메인 대화: Sonnet 5.5 (`examples/settings.json`을 프로젝트 `.claude/settings.json`으로 복사)
  - 팀장 `handoff-lead` (맥락 파악·분배·지시서): Fable 5.2
  - 워커 `handoff-worker` (여러 개 병렬, 지시서마다 담당 파일 분리, 겹칠 위험이 있으면 worktree): Opus 5.5
  - 검토 `handoff-reviewer` (위험이 큰 병합·푸시 전에만): Opus 5.5
  - 잡일 `handoff-helper` (요약·비교, 캡처 확인, 지정 범위의 문구 교체·간단한 정리, 병합): Sonnet 5.5
  - 실행 담당 `handoff-runner` (정해진 명령만 실행하고 숫자만 보고, 판단·수정 안 함): Haiku 5.5
- **일 크기별 경로 (v0.3.2, 효과 미측정):** 도구 호출 3회 이하는 메인이 직접 합니다. 한 갈래의 작은~중간 일은 팀장 없이 워커 하나에게 바로 맡기고, 이때만 메인이 점검표를 따라 한 장짜리 지시서를 씁니다. 일이 2개 이상 병렬 갈래로 나뉘면 팀장이 지시서를 씁니다. 메인이 쓰는 조건은 셋입니다: 한 갈래일 것, 이미 아는 내용만으로 점검표를 다 채울 수 있을 것, 3,000자 이내일 것. 하나라도 안 되거나 워커가 막혀 돌아오면 팀장에게 넘깁니다.
- **등급 3단 (v0.3):** 지시서를 쓰는 쪽(팀장, 한 갈래 경로에서는 메인)이 지시서마다 `Model: runner | helper | worker`를 정합니다. 애매하면 한 단계 위, 실패하면 같은 지시서를 한 단계 위로 다시 돌립니다.
- **자기완결 지시서 (v0.3):** 받은 지시서 하나만 읽고 끝낼 수 있게 필요한 사실을 발췌해 넣습니다. "다른 노트 먼저 읽기"는 쓰지 않습니다(6,000자 이내).
- **돌려주기는 3줄 (v0.3):** 결과 노트 맨 위에 `Done:`·`Next:`(각 3줄 이내)·`Blocked:`를 두고, 메인에는 경로+3줄만 돌려줍니다.
- **팀장 점검 (v0.3):** 지시서를 넘기기 전에 담당 파일 겹침, 같은 일 중복, 아무도 안 맡은 따름 변경, 병합 뒤 전체 시험 1회, 커밋 끝줄의 모델 이름, 등급, 자기완결 여부를 확인해 `plan.md`에 적습니다.
- **도구 허용 목록 (v0.3.1):** 모든 에이전트에 `tools:` 줄을 둡니다(Read·Bash·Glob·Grep, 역할에 필요할 때만 Edit·Write, MCP·브라우저 도구 없음). 우리 로그에서는 첫 턴이 약 55K에서 약 11K로 달라졌습니다(표본 1, 방향 확인용).
- **작은 일은 메인이 직접 (v0.3.1):** 도구 호출 3회 이하·출력 6,000자 이하로 예상되는 일은 맡기지 않고 메인이 합니다. 맡길 때마다 첫 턴 고정 비용이 들기 때문입니다. 실행 담당은 정해진 명령을 반복하는 일에만 씁니다.
- **큰 결과는 필요한 부분만 (v0.3.1):** 지시서와 Agent 프롬프트는 6,000자 이내로 쓰고, 로그·diff·캔버스는 파일로 보낸 뒤 필요한 줄만 인용합니다.
- **담당 워커 (v0.3.2, 소표본 첫 확인됨; 큰 작업·실제 앱·약 150K 교체 기준은 미측정):** 한 프로젝트에서 이어지는 일은 같은 워커에게 SendMessage로 계속 맡기고, 병렬이거나 무관한 일은 일회용 워커에게 맡깁니다. 컨텍스트가 약 150K에 가까워지면 인수 노트(한 일·다음 할 일·막힌 것)를 쓰게 하고 새 담당으로 바꿉니다.
- **짧은 중계 (v0.3.2):** 메인은 팀장·워커 보고를 경로+3줄로만 전하고, 같은 완료 알림이 되풀이되면 답하지 않습니다.
- **검토와 시험 (v0.3.2):** 검토는 위험이 큰 병합·푸시 전에만 합니다(브랜치 2개 이상 병합, 공유·운영 브랜치, 보안·권한·결제·데이터 이전). 전체 시험은 병합 뒤 한 번, 담당 파일이 안 겹치면 워커 2~3개를 병렬로 돌립니다.
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

## License
MIT
