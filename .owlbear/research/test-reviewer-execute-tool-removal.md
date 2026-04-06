# Test: Reviewer execute/* Tool Removal

> **Owning task:** #458 — Test: Remove execute/* tools from reviewer agent
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Task #458 is the TDD-paired test task for #457 (remove execute/* tools from reviewer agent). This research validates the test surface, identifies RED/GREEN split, and resolves specification gaps before the test-writer begins.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| S1 | reviewer.agent.md | share/agents/reviewer.agent.md:9 | .95 — current tool inventory |
| S2 | test_disable_model_invocation.py | tests/test_disable_model_invocation.py | .95 — reference test pattern |
| S3 | #317 research doc | .owlbear/research/reviewer-execute-tool-removal.md | .90 — prior art analysis |
| S4 | code-review/SKILL.md | share/skills/code-review/SKILL.md:54-57 | .85 — terminal fallback commands |
| S5 | w-code-review/SKILL.md | share/skills/w-code-review/SKILL.md:42-126 | .90 — MCP refs + fallback sections |
| S6 | test_agent_port_v2.py | tests/test_agent_port_v2.py | .80 — alt pattern for tool parsing |

## 3. Analysis

### 3a. Current Reviewer Tools (S1)

16 tool entries: 7 execute/*, read/terminalLastCommand, and 8 non-execute tools.

Non-execute tools: vscode/memory, read/problems, read/readFile, read/viewImage, agent, search, owlbear-kanban/*, owlbear-memory/*.

### 3b. RED/GREEN Split for TDD Pairing

| AC | Pre-#457 state | Post-#457 | RED? |
|----|----------------|-----------|------|
| AC1: no execute/* | 7 execute/* present | Removed | RED |
| AC2: no terminalLastCommand | Present | Removed | RED |
| AC3: retains required tools | All present | Still present | GREEN (regression) |
| AC4: MCP kanban in skill | w-code-review already has refs | Unchanged | GREEN (regression) |
| AC5: no kanban-md.exe in skill | None exist currently | Unchanged | GREEN (regression) |

Only AC1 and AC2 produce RED tests. AC3-AC5 are regression guards.

### 3c. Specification Defects Found

**Defect 1 — owlbear-memory/* omitted from AC3.** Both #457 and #458 AC3 list 7 required tools but the reviewer currently has 8 non-execute tools (owlbear-memory/* is the 8th). Tests asserting "exactly 7 tools" would fail for the wrong reason. Fix: test "at least these 7 present" or amend AC to list 8.

**Defect 2 — AC6 structurally impossible.** "All tests fail before #457 implementation" cannot hold for 3 of 5 ACs. Fix: reword to "AC1/AC2 tests fail before implementation (RED). AC3-AC5 are regression guards (GREEN from start)."

**Defect 3 — Partial coverage of #457's ACs.** #458 tests cover #457 AC1-AC3 but not: AC4 (specific skill steps), AC5 (MCP handoff documentation), AC6 (fallback removal from skills). Terminal fallback sections at w-code-review lines 42-48, 94-100, 120-126 and code-review lines 54-57 have no test coverage.

### 3d. Test Pattern Analysis (S2, S6)

| Aspect | Pattern from S2 | Applicable to #458 |
|--------|-----------------|---------------------|
| File location | pathlib ROOT/AGENTS_DIR | Same |
| Frontmatter extraction | regex `\\A---\\n(.*?)\\n---` | Same |
| Class structure | TestFromAC_* per AC group | Same |
| Assertions | String presence/absence in frontmatter | String presence/absence in tools/content |
| Constants | Named agent lists | Named tool lists |

### 3e. Test Implementation Approach

```
TestFromAC_NoExecuteTools (AC1)          — 2 tests: no execute/* prefix, count=0
TestFromAC_NoTerminalLastCommand (AC2)   — 1 test: read/terminalLastCommand absent
TestFromAC_RetainsRequiredTools (AC3)    — 7+ tests: each required tool present
TestFromAC_SkillReferencesMCPKanban (AC4)— 1+ tests: MCP tool names in w-code-review
TestFromAC_SkillNoKanbanMdExe (AC5)      — 2 tests: kanban-md.exe absent from both skills
```

## 4. Recommendation (confidence: .75)

Proceed to test-writing with AC amendments. Before writing tests:

1. Amend #458 AC3 to include owlbear-memory/* (8 tools, not 7)
2. Rewrite AC6 to acknowledge RED/GREEN split honestly
3. Optionally expand AC to cover fallback removal (w-code-review terminal sections)

Challenge: reconsider — confidence in original: .70. Key challenges: owlbear-memory/* count defect (accepted), AC6 impossibility (accepted), partial coverage gap (partially accepted — #458 has its own scope). Revised to .75 after accepting amendments.

## 5. Follow-up Tasks

No new follow-up tasks needed — #458 is itself the test task. AC amendments applied via task body edit (see below). Builder for #457 should update #457 AC3 to match (8 tools).
