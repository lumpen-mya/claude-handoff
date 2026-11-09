# claude-handoff

**Stop paying for long context.** A Claude Code skill that compacts at task boundaries into a structured handoff note and continues in a fresh session — based on NVIDIA's *"You don't need long context"* (2026).

![license](https://img.shields.io/badge/license-MIT-blue) ![status](https://img.shields.io/badge/status-experimental%20v0.1-orange) ![claude code](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2)

> In the paper, frequent structured compaction kept Opus accuracy within **−3.7 to +5.6 pp** of baseline while estimated cost fell **2.2–8.8×**; selective reading of long inputs cut estimated cost **6.5–54×**. This skill turns those findings into a daily workflow.

**Install (one line, in your terminal):**
```
claude plugin marketplace add lumpen-mya/claude-handoff && claude plugin install handoff@claude-handoff
```
Or just tell Claude: *"install the lumpen-mya/claude-handoff plugin"*. Then type `/handoff`.

> **Status: experimental (v0.1).** Thresholds are hypotheses being measured in real work — please try it and leave feedback ([Feedback](#feedback)).

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

**Not yet measured for this plugin:** the numbers above are from the papers. Per-session token metrics are now logged with `scripts/session_tokens.py` during the test period.

**Not yet evidenced (our hypotheses):** when splitting into parallel sessions pays off (3+ files or ~20+ min per bundle, 2–3 workers). We are measuring this.

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

- **One session = one title.** Out-of-scope requests get proposed as a new session.
- **Handoff note** (`~/.claude/handoffs/YYYY-MM-DD-<slug>.md`) in 7 parts: objective, established facts, applied changes, verification, dead ends, remaining plan, environment.
- **Never overwrites** existing notes — appends and records corrections.
- **Check step** before continuing: preservation, format, facts (commits/paths/push), unverified marks, conflicts with existing docs (suggested, not applied), and promotion of confirmed decisions to memory/specs (with user confirmation).
- **Split work** only for independent, sizable bundles (2–3 workers, max 4); the coordinator writes the briefs and reviews the diffs.

Use: type `/handoff`, or say "hand this off" / "start a fresh session".

## Feedback

This is a work in progress. Please try it and tell us:
- Did the handoff note let the new session continue without re-exploring?
- Token/time before vs after (rough numbers are fine)
- When splitting into sessions helped or hurt (task size, number of files, number of workers)
- Anything that broke, or rules that felt wrong

Open an [issue](https://github.com/lumpen-mya/claude-handoff/issues) (reviews and short reports welcome).

---

## 한국어

> **지금 실험 중인 v0.1입니다.** 써 보시고 후기를 남겨 주세요. [Issues](https://github.com/lumpen-mya/claude-handoff/issues)에 짧게 적어 주셔도 됩니다.

**근거 요약**
- 작업 경계에서 압축하면 긴 작업에서도 정확도가 거의 그대로였습니다. Opus 4.5 기준 기준 대비 −3.7~+5.6pp입니다. (NVIDIA §3)
- 좋은 압축은 회고가 아니라 인수인계입니다. (NVIDIA 부록 A, G.1)
- 비용 절감은 대부분 압축이 아니라 필요한 부분만 골라 읽는 데서 나왔습니다. (NVIDIA §4)
- 너무 자주 압축하면 캐시가 깨져서 오히려 비싸질 수 있습니다. (NVIDIA 부록 C)
- 반복 작업을 절차나 스크립트로 고정하면 토큰이 79~90% 줄었습니다. (GenericAgent §4.4)
- **아직 근거가 없는 가설:** 세션을 나누는 기준(묶음당 파일 3개 이상 또는 20분 이상, 작업 세션 2~3개)입니다. 지금 실측하고 있습니다.

**후기로 알려 주시면 좋은 것**
- 새 세션이 다시 탐색하지 않고 바로 이어갔는지
- 쓰기 전과 후의 토큰·시간 (대략적인 숫자도 괜찮습니다)
- 세션을 나눠서 이득이었던 경우와 손해였던 경우
- 고장 난 부분이나 어색한 규칙

**짧은 컨텍스트로 일하기 위한** Claude Code 스킬입니다. 작업이 끝나는 시점에 구조화된 인수인계 노트로 압축하고, 새 세션에서 이어갑니다. 세션을 여러 개로 나누는 건 그쪽이 이득일 때만 합니다.

근거는 NVIDIA 논문 ["You don't need long context"](https://arxiv.org/abs/2611.05306)입니다. 작업 경계에서 인수인계 형식으로 압축하면 정확도는 거의 그대로이고 비용은 줄어듭니다.

**설치 (터미널 한 줄)**
```
claude plugin marketplace add lumpen-mya/claude-handoff && claude plugin install handoff@claude-handoff
```
또는 Claude에게 "lumpen-mya/claude-handoff 플러그인 설치해줘"라고 말하면 됩니다.

**주요 동작**
- **한 세션에 한 타이틀:** 세션 범위를 타이틀 하나로 정합니다. 범위 밖 요청은 새 세션으로 나누자고 제안합니다.
- **인수인계 노트 7항목:** 목표, 확인된 사실, 적용한 변경, 검증, 막다른 길, 남은 계획, 환경을 적습니다.
- **기존 파일은 덮어쓰지 않음:** 덧붙이기와 정정만 합니다.
- **새 세션을 열기 전 점검:**
  - 기존 내용이 그대로 남아 있는지
  - 형식이 맞는지
  - 커밋·경로가 실제로 있는지
  - 확인 못 한 내용에 '미확인' 표시가 있는지
  - 기존 문서와 충돌하는 내용이 있는지 (고치지 않고 권장안만 제안)
  - 확정된 결정을 메모리나 스펙으로 올릴 후보 (확인 후에만 반영)
- **작업 나누기:** 서로 독립적이고 큰 묶음일 때만 나눕니다. 보통 2~3개, 최대 4개입니다.

## License
MIT
