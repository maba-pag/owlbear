---
id: 457
title: Remove execute/* tools from reviewer agent
status: todo
priority: nice-to-have
created: 2026-03-30T23:47:55.0036687+02:00
updated: 2026-04-06T01:10:43.1508611+02:00
tags:
    - scope:agents
    - phase-2
    - agent
depends_on:
    - 264
class: standard
---

Remove all 7 execute/* tools and read/terminalLastCommand from reviewer.agent.md. Replace terminal fallback sections in code-review skills with BLOCK instructions. See .owlbear/research/reviewer-execute-tool-removal.md for full analysis.

AC:
- [ ] reviewer.agent.md tools list contains no execute/* entries
- [ ] reviewer.agent.md tools list does not contain read/terminalLastCommand
- [ ] reviewer.agent.md tools list retains exactly: vscode/memory, read/problems, read/readFile, read/viewImage, agent, search, owlbear-kanban/*, owlbear-memory/*
- [ ] w-code-review/SKILL.md: "Fallback: Quality-Runner Unavailable" sections in Steps 2, 3, 4 rewritten — remove uv run terminal commands, replace with BLOCK instruction using end_work(outcome="block", block_reason="Quality-Runner unavailable")
- [ ] code-review/SKILL.md: "Fallback: Quality-Runner Unavailable" section rewritten — remove uv run terminal commands, replace with BLOCK instruction matching AC4
- [ ] No kanban-md.exe references in code-review/SKILL.md or w-code-review/SKILL.md (regression guard, currently clean)

Depends on: #264 (Quality-Runner wired in)

Files to modify:
- share/agents/reviewer.agent.md (tools list only)
- share/skills/w-code-review/SKILL.md (3 fallback sections: Steps 2, 3, 4)
- share/skills/code-review/SKILL.md (1 fallback section)

Note: Test task #458 AC3 needs alignment — update "7 tool entries" to 8 (owlbear-memory/* added to retain list).

## Research
- Research doc: .owlbear/research/reviewer-execute-tool-removal.md (task #317, validated)
- Sources: 7 studied (from #317 research), 5 high-relevance
- Validation pass: existing research confirmed current, all findings hold
- Recommendation: Option A (remove all execute/* + terminalLastCommand), confidence: .85
- Follow-up tasks: #458 (test task) already exists at ideation
- Decision requests: none (T1 autonomous)

### Validation Findings
1. No kanban-md.exe refs exist in code-review skills. #264 migrated kanban ops to MCP.
2. Step 2.5 dead-code risk: w-code-review sequential fallback impossible without execute/* tools. Builder must rewrite to BLOCK (end_work outcome=block) when QR unavailable.
3. 4 fallback removal locations: code-review/SKILL.md (1), w-code-review/SKILL.md (3 in Steps 2, 3, 4).
4. Test task #458 AC4/AC5 kanban-md absence checks will trivially RED. Test-writer should verify MCP tools ARE referenced for meaningful RED-GREEN.
5. Subagent tool independence confirmed: parent does not need execute/* for QR dispatch.
6. No terminal assumptions found outside fallback sections in reviewer-relevant files.

[[2026-04-06]] Mon 01:10
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: enforce reviewer read-only boundary structurally |
| Interface clarity | PASS | AC rewritten with exact file paths, step numbers, and BLOCK behavior |
| Dependency correctness | PASS | #264 (Quality-Runner wired in) archived/done |
| Module layering | PASS | Agent.md and SKILL.md are config, no module imports |
| TDD compliance | PASS | Test task #458 exists at ideation, depends on #457 |
| KISS/YAGNI | PASS | Minimal scope: remove tools + update 4 fallback sections |
| Premise challenge | PASS | Research validates: reviewer never needs terminal, QR handles all execution |
| Pattern consistency | PASS | BLOCK pattern follows h-mcp-kanban end_work conventions |
| Security surface | PASS | Reduces attack surface by removing 8 execute/read tools |
| Single domain | PASS | scope:agents — agent configuration only |

### AC Refinement Summary
Original AC had 6 lines; 4 needed correction:
- AC3: Added owlbear-memory/* to retain list (reviewer has it at line 9, omission would cause inadvertent removal breaking post-task reflection)
- AC4 (old): Removed — kanban-md.exe migration already complete per #264, confirmed by grep (0 matches). Step references "1, 8, 9" were incorrect (Step 9 nonexistent)
- AC5 (old): Merged into new AC4/AC5 — handoff pattern is end_work(outcome=block), documented via BLOCK fallback replacement
- AC6 (old): Fixed step numbers from "Steps 3-5" to "Steps 2, 3, 4" (Step 5 has no fallback). Added code-review/SKILL.md scope (was missing)
- Added: explicit file list, BLOCK behavior requirement (research finding #2), regression guard AC

### Codebase Evidence
- share/agents/reviewer.agent.md:9 — current tools include owlbear-memory/* (not in original AC3 retain list)
- share/skills/w-code-review/SKILL.md:42 — Step 2 fallback (uv run pytest)
- share/skills/w-code-review/SKILL.md:94 — Step 3 fallback (uv run ruff)
- share/skills/w-code-review/SKILL.md:120 — Step 4 fallback (uv run pytest cov)
- share/skills/code-review/SKILL.md:50 — single fallback section (all 3 uv run commands)
- grep "kanban-md.exe" in both skills: 0 matches (AC4 old confirmed pre-satisfied)

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in agents list
- Architect response: proceeded without challenge; all 10 criteria PASS, codebase evidence confirms design

### Verdict: APPROVE (after refinement)
### Action Taken: Rewrote AC body with corrected step numbers, added owlbear-memory/* to retain list, replaced stale kanban-md.exe AC with BLOCK behavior requirements, added regression guard. Added agent pass-through tag. Moving to todo.
