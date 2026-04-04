# MCP Tool Reference Validation Test Design

> **Owning task:** #562 — Test: Validate MCP tool references in agents, skills, and instructions
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #562 creates a RED-phase test file (`tests/test_mcp_tool_references_483.py`) that
validates MCP tool references will be added alongside CLI in agents, skills, and
instructions by sibling tasks #563–#566 (children of parent #483). The test must fail
on current HEAD and pass after all siblings complete.

Key design questions: target file enumeration, false-positive avoidance for MCP tool
names that collide with non-kanban identifiers, and section-aware vs whole-file scanning.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `test_argument_hint_skills.py` | Codebase | .80 — structural validation prior art (frontmatter-only) |
| 2 | `docs/research/mcp-tool-references-alongside-cli.md` | Research | .95 — full CLI-to-MCP mapping and scope corrections |
| 3 | `skills/mcp-kanban/SKILL.md` | Codebase | .95 — current MCP tool reference (8 tools) |
| 4 | 11 agent `.agent.md` files | Codebase | .90 — verified zero MCP refs in body text |
| 5 | 8 skill SKILL.md cheatsheets | Codebase | .90 — verified zero MCP refs in tables |
| 6 | `agent-common.instructions.md` | Codebase | .85 — 16+ CLI refs across 6 sections |

## 3. Analysis

### 3a. Agent count: 10 vs 11

The AC says "10 pipeline agents." Actual count: **11 agents** have `owlbear-kanban/*`
tools (architect, auditor, builder, curator, kanban-planner, planner, researcher,
reviewer, scribe, test-writer, writer). The gate-owning lifecycle has 7. No definition
in the codebase yields exactly 10. **Recommendation:** test all 11 agents with
`owlbear-kanban/*` tools. The AC count is a minor error; the architect should correct
during backlog review.

### 3b. False-positive mitigation

`create_task` collides with `asyncio.create_task` in curator.agent.md. Strategy:

| Approach | Precision | Complexity |
|----------|-----------|------------|
| Check for `start_work`/`end_work` only (unique to kanban MCP) | High | Low |
| Require `mcp` or `owlbear-kanban` near tool names | Medium | Medium |
| Section-aware parsing (split on headers, scan kanban sections) | High | High |

**Recommendation (.85):** Use `start_work` and `end_work` as primary markers — they
are unique to kanban MCP with zero collision risk. For broader coverage, also check
`edit_task` in kanban-context sections (after a kanban-related heading). Avoid
bare `create_task` patterns altogether.

### 3c. Scanning approach: frontmatter vs body text

Prior art (`test_argument_hint_skills.py`) scans YAML frontmatter — a bounded,
delimited space. Task #562 must scan free-form markdown body text — a fundamentally
different problem. Two-tier approach:

1. **Body extraction:** Strip YAML frontmatter, scan remaining body text
2. **Pattern matching:** Use regex for MCP tool names in body. For cheatsheet
   tables, check for MCP tool names within `## kanban-md Commands` sections

### 3d. Target file enumeration

| Category | Files | Pattern to validate |
|----------|-------|---------------------|
| Agents (11) | All `.agent.md` with `owlbear-kanban/*` | Body text contains `start_work` or `end_work` |
| Skill cheatsheets (8) | Skills with `## kanban-md Commands` | Table contains MCP tool name (e.g., `start_work`) |
| mcp-kanban SKILL.md (1) | `skills/mcp-kanban/SKILL.md` | Contains agent workflow section heading |
| agent-common (1) | `instructions/agent-common.instructions.md` | Contains `edit_task`/`start_work`/`end_work` |

### 3e. RED-phase verification

Current HEAD confirmed: zero MCP tool names (`start_work`, `end_work`, `edit_task`,
`show-task`) in any agent body text, skill cheatsheet table, or agent-common.
One false positive: `asyncio.create_task` in curator — mitigated by not checking
bare `create_task`. All test assertions will fail as required.

### 3f. Test structure recommendation

```
class TestMcpKanbanSkillWorkflowPattern    # AC item 2
class TestAgentCommonMcpSyntax             # AC item 3
class TestAgentMcpBodyReferences           # AC item 4 (parametrized over 11 agents)
class TestSkillCheatsheetMcpReferences     # AC item 5 (parametrized over 8 skills)
```

Parametrize agent and skill tests using `pytest.mark.parametrize` for clean
failure reporting per file.

## 4. Recommendation (.80 confidence)

Proceed with structural validation test. Key design decisions:

1. Use `start_work`/`end_work` as collision-free primary markers
2. Parametrize over discovered files (glob `agents/*.agent.md`, scan for
   `owlbear-kanban/*` in tools) rather than hard-coding a count
3. Strip frontmatter before body-text scanning to avoid YAML-section noise
4. The AC count "10" should be corrected to "11" or the test should dynamically
   discover agents with `owlbear-kanban/*` tools (preferred — no hard-coded count)

Challenge: reconsider — confidence in original: .60. Challenger raised valid
concerns on count mismatch (accepted — use dynamic discovery), false-positive
strategy (accepted — use collision-free markers), prior art mismatch (accepted —
body text scanning differs from frontmatter), scope gap in inline-ref skills
(noted — AC says "with kanban cheatsheets," inline-ref skills are #566 scope).
Revised confidence from .85 to .80 after incorporating feedback.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #562 already has well-scoped AC and
is part of the #483 decomposition (#562–#566). The AC count correction
(10 → 11 or dynamic) should be noted in the architecture review of #562.
