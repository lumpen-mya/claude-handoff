# claude-handoff

**Stop paying for long context.** A Claude Code plugin that keeps the main session for conversation only, pushes all work to subagents (a lead, several workers with separate work areas, a reviewer, a helper), and carries state in markdown notes — handing off to a fresh session at task boundaries. Based on NVIDIA's *"You don't need long context"* (2026) and our own session measurements.

![license](https://img.shields.io/badge/license-MIT-blue) ![status](https://img.shields.io/badge/status-experimental%20v0.2-orange) ![claude code](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2)

> In the paper, frequent structured compaction kept Opus accuracy within **−3.7 to +5.6 pp** of baseline while estimated cost fell **2.2–8.8×**; selective reading of long inputs cut estimated cost **6.5–54×**. This skill turns those findings into a daily workflow.

**Install (one line, in your terminal):**
```
claude plugin marketplace add lumpen-mya/claude-handoff && claude plugin install handoff@claude-handoff
```
Or just tell Claude: *"install the lumpen-mya/claude-handoff plugin"*. Then type `/handoff`.

> **Status: experimental (v0.2).** Thresholds are hypotheses being measured in real work — please try it and leave feedback ([Feedback](#feedback)).

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

**Not yet evidenced (our hypotheses):** that the main-session-talks setup keeps context under ~150K for a whole task, and the worker limits (2–3 at once, worktree only when files could collide). We are measuring this.

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

**The main session talks, subagents work.** Only markdown paths and 5–10 line summaries reach the main session.

| Role | Agent | Model |
|---|---|---|
| Main conversation | your session | Sonnet 5.5 — copy `examples/settings.json` to `<project>/.claude/settings.json` |
| Lead: reads context, splits work, writes briefs | `handoff-lead` | Fable 5.2 |
| Workers: several in parallel, each with its own `Owned files:` (git worktree when files could collide) | `handoff-worker` | Opus 5.5 |
| Reviewer: re-checks commits, diffs, verification | `handoff-reviewer` | Opus 5.5 |
| Helper: git status, builds, lookups, screenshots | `handoff-helper` | Sonnet 5.5 |

- **Task folder** `~/.claude/handoffs/tasks/YYYY-MM-DD-<slug>/` holds `brief-N-*.md`, `result-N-*.md`, `review.md`, `handoff.md`.
- **Concise answers**: conclusion and key points only; subagents return 5–10 lines.
- **Handoff note** at a task boundary, in 7 parts: objective, established facts, applied changes, verification, dead ends, remaining plan, environment. Never overwrites existing notes — appends and records corrections.
- **Check step** before continuing: preservation, format, facts (commits/paths/push), unverified marks, conflicts with existing docs (suggested, not applied), promotion of confirmed decisions (with user confirmation).

Use: type `/handoff`, or say "hand this off" / "start a fresh session".

## Our measurements (49 sessions, not a controlled study)
- A fresh start from a handoff note begins at ~100K tokens, right after auto-compaction ~125K — then **both grow 50–80K every 50 calls** when the session does the work itself. A handoff alone does not keep context small.
- ~80% of the growth was command output, screenshots and lookups; assistant text ~4%.
- Output tokens per call were flat (~600) regardless of session length; cost differences come from input.
- Sessions started from a brief or handoff cost about half per user request compared with long sessions (weighted tokens), with zero auto-compactions — small sample, selection bias likely.
- Reproduce on your own history: `python3 -I plugins/handoff/skills/handoff/scripts/compare_sessions.py out.json`.

## Feedback

This is a work in progress. Please try it and tell us:
- Did the handoff note let the new session continue without re-exploring?
- Token/time before vs after (rough numbers are fine)
- When splitting into sessions helped or hurt (task size, number of files, number of workers)
- Anything that broke, or rules that felt wrong

Open an [issue](https://github.com/lumpen-mya/claude-handoff/issues) (reviews and short reports welcome).

---

## 한국어

> **지금 실험 중인 v0.2입니다.** 써 보시고 후기를 남겨 주세요. [Issues](https://github.com/lumpen-mya/claude-handoff/issues)에 짧게 적어 주셔도 됩니다.

**근거 요약**
- 작업 경계에서 압축하면 긴 작업에서도 정확도가 거의 그대로였습니다. Opus 4.5 기준 기준 대비 −3.7~+5.6pp입니다. (NVIDIA §3)
- 좋은 압축은 회고가 아니라 인수인계입니다. (NVIDIA 부록 A, G.1)
- 비용 절감은 대부분 압축이 아니라 필요한 부분만 골라 읽는 데서 나왔습니다. (NVIDIA §4)
- 너무 자주 압축하면 캐시가 깨져서 오히려 비싸질 수 있습니다. (NVIDIA 부록 C)
- 반복 작업을 절차나 스크립트로 고정하면 토큰이 79~90% 줄었습니다. (GenericAgent §4.4)
- **아직 근거가 없는 가설:** 메인이 대화만 하면 작업 내내 150K 아래로 유지된다는 것, 워커 수(동시 2~3개)입니다. 지금 실측하고 있습니다.

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

**주요 동작 (v0.2)**
- **메인은 대화만, 작업은 서브에이전트:** 메인에는 md 경로와 5~10줄 요약만 옵니다.
  - 메인 대화: Sonnet 5.5 (`examples/settings.json`을 프로젝트 `.claude/settings.json`으로 복사)
  - 팀장 `handoff-lead` (맥락 파악·분배·지시서): Fable 5.2
  - 워커 `handoff-worker` (여러 개 병렬, 지시서마다 담당 파일 분리, 겹칠 위험이 있으면 worktree): Opus 5.5
  - 검토 `handoff-reviewer`: Opus 5.5 · 잡일 `handoff-helper`: Sonnet 5.5
- **작업 폴더:** `~/.claude/handoffs/tasks/날짜-작업명/`에 지시서·결과·검토·인수인계 md를 둡니다.
- **답변은 간결하게:** 결론과 핵심만 답합니다.
- **인수인계 노트 7항목:** 목표, 확인된 사실, 적용한 변경, 검증, 막다른 길, 남은 계획, 환경. 기존 파일은 덮어쓰지 않고 덧붙이기와 정정만 합니다.
- **이어가기 전 점검:** 기존 내용 보존, 형식, 커밋·경로 사실 확인, '미확인' 표시, 기존 문서와의 충돌(권장안만 제안), 확정된 결정의 메모리·스펙 승격 후보(확인 후 반영).

**직접 잰 수치 (49세션)**
- 핸드오프로 새로 시작하면 약 100K, 자동 압축 직후는 약 125K입니다. 그 뒤 세션이 직접 작업하면 둘 다 50호출마다 50~80K씩 커집니다.
- 커진 양의 약 80%는 명령 출력·스크린샷·조회 결과였습니다.
- 출력 토큰은 호출당 약 600으로 세션 길이와 무관했습니다.

## License
MIT
