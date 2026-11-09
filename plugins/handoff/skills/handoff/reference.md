# Token-saving principles and sources

Always-on rules belong in your CLAUDE.md (keep them to ~15 lines). This file holds the reasoning and sources; read it only when needed.

## Keep long material out of the context
Sources: Belcak et al. "You don't need long context" (NVIDIA, arXiv 2611.05306) §4 & App. E; Liang et al. "GenericAgent" (arXiv 2604.17091) §2.3.4.
- Keep large tool results (MCP/JSON dumps, logs) in files and extract only needed fields with a script. Never read them whole.
- Locate with `grep -n`, then read only that range (offset/limit, `sed -n 'a,bp'`). Keep each read under ~6,000 characters (NVIDIA App. E.1).
- Count/filter/sort with a script and read only the result.
- For long output look at head AND tail (or `grep -nE "FAIL|error"`), not tail alone (GenericAgent truncates keeping both ends).
- CJK text costs ~1–2 tokens per character; route large CJK output to files.
- Crop screenshots to the region you need.
- Store in memory only facts verified by execution ("No Execution, No Memory", GenericAgent §2.3.3).

Note: Cao et al. "Coding Agents are Effective Long-Context Processors" (arXiv 2603.20432) shows file-based navigation improves *accuracy* (+17.3% avg), but per-query cost was higher than RAG in their setup (Table 5). Cite it for accuracy, not savings.

## Compaction
- A good compaction is a handoff brief for the remaining work, not a recap (NVIDIA App. A; prompt in App. G.1).
- Long-horizon tasks: Opus 4.5 accuracy stayed within −3.7 to +5.6 pp of baseline (§3, Fig. 5).
- Most long-input savings came from selective reading, not compaction; median compactions ≈ 0 (§4, App. F).
- Large savings multiples assume context-length-dependent pricing (App. B). Under flat retail pricing, frequent compaction can cost MORE because cached tokens become fresh input (App. C, Tables 3 & 5). Compact at task boundaries.
- Weaker models degrade under tight compaction budgets (App. D, Table 9).

## Freeze repeated work
- Turning repeated tasks into SOPs/scripts cut tokens by −79% to −90% on reruns, mainly by fewer calls (GenericAgent §4.4, Table 8).

## Minimise always-on context
- A rules-only memory (165 tokens) outperformed the full SOP (575 tokens); adding background (288 tokens) did not help (GenericAgent §4.3.2, Table 5).
- Keep CLAUDE.md/memory to rules and pointers; disable unused MCP servers and plugins.

## Avoid failure loops
- Escalate: after 2 failed attempts at the same fix, change approach or gather info; on the 3rd, ask the user (GenericAgent §2.3.3).

## Weak evidence (do not treat as rules)
- "<30k tokens is the hallucination-free limit" — no experiment (GenericAgent §2.1.4).
- "Fewer tokens = better performance" — authors call it an observation, not a controlled result (GenericAgent §5).
- Output caps (6k–10k chars) are design choices, not ablated.
