---
id: 457
title: Remove execute/* tools from reviewer agent
status: archived
priority: medium
created: 2026-03-30 23:47:55.003669+02:00
updated: 2026-04-06 06:33:09.258631+02:00
started: 2026-04-06 06:33:09.258631+02:00
completed: 2026-04-06 06:33:09.258631+02:00
tags:
- scope:agents
- phase-2
- agent
depends_on:
- 264
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-04-06]] Mon 03:10
## Test-Writer Notes

**Test file:** tests/test_reviewer_execute_tools_457.py

**Classes and test counts:**
| Class | Category | RED/GREEN | Tests |
|-------|---------|-----------|-------|
| `TestFromAC_ReviewerNoExecuteTools` | happy/boundary | change-detecting | 8 |
| `TestFromAC_ReviewerNoTerminalLastCommand` | change-detecting | RED (pre-impl) | 1 |
| `TestFromAC_ReviewerRetainsRequiredTools` | regression guard | GREEN | 9 |
| `TestFromAC_WCodeReviewSkillMcpKanbanTools` | regression guard | GREEN | 4 |
| `TestFromAC_SkillsNoKanbanMdExe` | regression guard | GREEN | 2 |
| `TestFromAC_WCodeReviewFallbackBlockInstruction` | change-detecting | RED (AC4) | 6 |
| `TestFromAC_CodeReviewFallbackBlockInstruction` | change-detecting | RED (AC5) | 2 |
| **Total** | | | **32** |

**pytest result:** 8 FAIL, 24 PASS (as designed)

**AC coverage:**
| AC | Tests | Status |
|----|-------|--------|
| AC1: no execute/* tools | `TestFromAC_ReviewerNoExecuteTools` x8 | PASS (already implemented) |
| AC2: no read/terminalLastCommand | `TestFromAC_ReviewerNoTerminalLastCommand` x1 | PASS (already implemented) |
| AC3: retains 8 required tools | `TestFromAC_ReviewerRetainsRequiredTools` x9 | PASS (regression guard) |
| AC4: w-code-review BLOCK fallback | `TestFromAC_WCodeReviewFallbackBlockInstruction` x6 | FAIL (RED — not yet implemented) |
| AC5: code-review BLOCK fallback | `TestFromAC_CodeReviewFallbackBlockInstruction` x2 | FAIL (RED — not yet implemented) |
| AC6: no kanban-md.exe | `TestFromAC_SkillsNoKanbanMdExe` x2 | PASS (regression guard) |

**Ruff:** clean

**Note for builder:** AC4/AC5 are the remaining work — rewrite the 3 fallback sections in w-code-review/SKILL.md (Steps 2, 3, 4) and the 1 fallback section in code-review/SKILL.md. Each must remove all `uv run` commands and add `end_work(outcome="block", block_reason="Quality-Runner unavailable")`.

**Agent tag override:** Task tagged `agent` (normally pass-through) but AC specifies verifiable SKILL.md content changes — tests written per user directive.

[[2026-04-06]] Mon 03:56
## Builder Notes

**Files changed:**
- `share/skills/w-code-review/SKILL.md` — replaced 3 fallback sections (Steps 2, 3, 4) with BLOCK instructions
- `share/skills/code-review/SKILL.md` — replaced 1 fallback section with BLOCK instruction

**Changes:** Removed all `uv run` terminal commands from every "Fallback: Quality-Runner Unavailable" section. Replaced with `end_work(outcome="block", block_reason="Quality-Runner unavailable — cannot run {tests/lint/coverage} independently")`.

**Note:** `reviewer.agent.md` was already clean — AC1, AC2, AC3 were pre-satisfied (execute/* and read/terminalLastCommand already absent from tools list).

**Test results:** 32 passed, 0 failed
**Lint:** ruff clean
**Coverage:** N/A (markdown files only — no Python coverage target)
**Evidence:** RED confirmed 8 FAIL before changes; GREEN confirmed 32 PASS after changes.

[[2026-04-06]] Mon 04:25
## Review Evidence

**Test Results:** 32 passed, 0 failed (quality-runner, independently run)
**Lint:** ruff clean
**Coverage:** N/A — markdown files only, no Python coverage target

### AC Compliance

| AC | Evidence | Status |
|---|---|---|
| AC1: No execute/* in reviewer.agent.md | reviewer.agent.md:8 — tools list confirmed, grep execute/ → 0 hits | PASS |
| AC2: No read/terminalLastCommand | reviewer.agent.md:8 — absent | PASS |
| AC3: Retains 8 required tools | reviewer.agent.md:8 — all 8 present, confirmed by TestFromAC_ReviewerRetainsRequiredTools ×9 | PASS |
| AC4: w-code-review Steps 2,3,4 fallbacks rewritten | w-code-review/SKILL.md:42–47, 92–97, 116–121 — end_work(outcome="block", ...) present, zero uv run in fallback sections | PASS |
| AC5: code-review fallback rewritten | code-review/SKILL.md:50–54 — end_work(outcome="block", ...) present, zero uv run | PASS |
| AC6: No kanban-md.exe | grep → 0 matches in both SKILL.md files | PASS |

### TestFromAC Coverage
All 7 TestFromAC_* classes map to AC lines. All assertions are change-detecting. No MISSING or LAX coverage. No TestFromAC_* modifications by builder detected (builder only touched the two SKILL.md files).

### Security
Markdown configuration files only. No OWASP concerns. Security surface reduced by removing 8 execute/terminal tools from reviewer's allowlist.

### Minor Note (non-deduction)
AC1/AC2 test docstrings say "FAIL before #457" but reviewer.agent.md was pre-satisfied — a docstring inconsistency, not a defect. Tests remain valid regression guards.

**Deductions: 0 | Confidence: .97 → PASS**

[[2026-04-06]] Mon 05:31
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A (files are the docs) | SKILL.md files were the task deliverable — already updated by builder. copilot-instructions.md has no reviewer/fallback sections (grep → 0 matches). No secondary docs capture these conventions. |
| 2 | Module docstrings | No | N/A | All changed files are Markdown (share/skills/). No Python modules created or modified. |
| 3 | External attribution | No | N/A | Sources covered by original research task #317. No new external patterns used in this task. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | .owlbear/research/reviewer-execute-tool-removal.md exists. Linked from task body under ## Research section. Follow-up task #458 created (test task). |

### Files Updated
- None — SKILL.md files updated by builder are the documentation target. No secondary docs require changes.

### Scratch Files Cleaned
- None — no .owlbear/scratch/457-* files found.

[[2026-04-06]] Mon 06:33
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: no execute/* in reviewer.agent.md | reviewer.agent.md:9 committed state, 0 execute/ entries | PASS |
| AC2: no read/terminalLastCommand | reviewer.agent.md:9 committed state, absent | PASS |
| AC3: retains 8 required tools | reviewer.agent.md:9 committed: vscode/memory, read/problems, read/readFile, read/viewImage, agent, search, owlbear-kanban/*, owlbear-memory/* | PASS |
| AC4: w-code-review Steps 2,3,4 BLOCK fallback | SKILL.md:42-47, 92-97, 116-121 end_work(outcome=block) present, 0 uv run in fallbacks | PASS |
| AC5: code-review fallback BLOCK | SKILL.md:50-54 end_work(outcome=block) present, 0 uv run | PASS |
| AC6: no kanban-md.exe | Select-String grep both SKILL.md files, 0 matches | PASS |

### Test Results
- pytest: 32 passed, 0 failed (committed state via git stash verification)
- ruff: All checks passed
- Note: 3 working-directory failures in test_reviewer_execute_tools_457.py caused by unstaged changes from task #575 (owlbear-kanban/* changed to specific tool names). Committed state at 80b05fc passes 32/32.

### Architect Quality: 5/5
AC specific, complete, refined during arch review. Exact file paths, step numbers, tool names, BLOCK behavior requirements. No builder improvisation needed.

### Deduction Breakdown
Starting: 1.00. All 6 AC lines have specific evidence, lint clean, reviewer evidence present and detailed, no task-scope test failures. 0 deductions.

### Confidence: .98
### Action: archive
