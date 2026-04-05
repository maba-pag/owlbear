# Agent-Common + Research-Docs MCP Alternatives Gap Analysis

> **Owning task:** #574 — P2-03: Update agent-common + research-docs instructions with MCP alternatives
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #574 requires that all ~16 kanban-md CLI references in `agent-common.instructions.md`
(across 6 sections) and `research-docs.instructions.md` gain MCP tool equivalents or
pointers to the `mcp-kanban` SKILL.md. The #572 builder added MCP notes at 2 locations
(Task coordination L28, Channel B L285) and 1 in research-docs (L16), passing #572's
tests. This research audits the remaining gap against #574's AC.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | agent-common.instructions.md (HEAD) | Codebase | .95 — target file, 15 CLI refs found |
| 2 | research-docs.instructions.md (HEAD) | Codebase | .90 — target file, 1 CLI ref + 1 MCP note |
| 3 | mcp-kanban SKILL.md (expanded #563) | Codebase | .95 — canonical MCP tool reference |
| 4 | docs/research/mcp-tool-references-alongside-cli.md | Research | .85 — parent CLI-to-MCP mapping |
| 5 | test_mcp_tool_references_483.py | Codebase | .90 — defines test coverage scope |

## 3. Analysis

### 3a. CLI Reference Inventory — agent-common.instructions.md

| Line | Section | CLI Reference | MCP Equivalent | Status |
|------|---------|--------------|----------------|--------|
| 26 | Task coordination | `kanban-md skill` ref | N/A (skill pointer) | OK |
| 28 | Task coordination | (MCP note) | `start_work`, `end_work` | ✅ Done |
| 35 | Handoff/blocked | `kanban-md.exe handoff` | `end_work(outcome="block")` + `edit_task(append_body=...)` | ❌ Gap |
| 87-96 | Blocking convention | `--block` references | `edit_task(block="reason")` or `end_work(outcome="block")` | ❌ Gap |
| 125 | Decision pre-flight | `kanban-md show` | `show-task` | ❌ Gap |
| 172 | Subtask creation | `kanban-md create` | `create_task` | ❌ Gap |
| 176 | Subtask creation table | `kanban-md create` | `create_task` | ❌ Gap |
| 187 | Placeholder rejection | `kanban-md create` | `create_task` | ❌ Gap |
| 205 | Tool discipline | `kanban-md` terminal ref | N/A (contextual) | OK |
| 209 | Tool discipline | `kanban-md show` | `show-task` | ❌ Gap |
| 226 | Loop detection | `kanban-md.exe handoff` | `end_work(outcome="block")` | ❌ Gap |
| 280 | Channel B | `kanban-md.exe edit -a -t` | (covered by L285 note) | ✅ Done |
| 283 | Reading rules | `kanban-md.exe show` | `show-task` | ❌ Gap |
| 313 | PS escaping | `kanban-md.exe edit` | MCP avoids PS pitfalls | ❌ Gap* |
| 318 | PS escaping | `kanban-md.exe edit` | (same section) | ❌ Gap* |
| 324 | PS gotchas | kanban-md parsing note | N/A (contextual) | OK |
| 331 | Reading rules | `kanban-md.exe show` | `show-task` | ❌ Gap |

*PS escaping section: a single note that MCP tools avoid these pitfalls is sufficient.

**Summary:** 3 done/OK, 3 contextual (N/A), 11 gaps needing MCP notes.

### 3b. CLI Reference Inventory — research-docs.instructions.md

| Line | CLI Reference | MCP Equivalent | Status |
|------|--------------|----------------|--------|
| 14 | `kanban-md create` | `create_task` | ❌ Gap (nearby note at L16 covers `create_task` but L14 itself has no inline pointer) |
| 16 | MCP note | `create_task`, `start_work`, `end_work` | ✅ Done |

**Summary:** L16 exists but L14 could benefit from an inline MCP hint. Minor gap.

### 3c. AC Coverage vs Test Coverage

| AC Item | Tests Cover? | Gap |
|---------|-------------|-----|
| AC1: Channel B MCP edit_task | ✅ TestFromAC_AgentCommonMcpSyntax | None |
| AC2: ~16 CLI refs have MCP equiv | ❌ Tests only check 2 sections | 11 CLI refs uncovered |
| AC3: 6 sections updated | ❌ Tests check 2 of 6 sections | 4 sections uncovered |
| AC4: research-docs MCP create_task | ✅ TestFromAC_ResearchDocsMcpSyntax | None |
| AC5: No CLI refs removed | Manual check needed | Verifiable at review |
| AC6: Pass #572 tests | ✅ All 73 pass | None |

### 3d. Implementation Pattern

The existing MCP notes at L28 and L285 use a consistent pattern:

```markdown
> **MCP tools (owlbear-kanban):** `tool_name` (description).
```

or

```markdown
> **MCP equivalents:** `tool_name` (description).
```

Both styles are in use. Standardize on `> **MCP tools (owlbear-kanban):**` for
section-level notes and `> **MCP equivalent:**` for inline notes near specific
CLI commands. This matches the pattern established by the #572 builder.

## 4. Recommendation (.90 confidence)

**T1 classification** — documentation for existing capabilities, no design decisions.
1:1 CLI-to-MCP mapping confirmed by parent research and server.py.

The builder should add MCP equivalent notes at 11 locations in agent-common.instructions.md
using the same `> **MCP equivalent:**` pattern. Group nearby refs where possible
(e.g., one note for the 3 `kanban-md create` refs in the subtask creation section).
Add a single note in the PS escaping section that MCP tools avoid these pitfalls.

**Challenge:** Skipped — T1 documentation, no trade-offs, established pattern.

**Risks:**
- Low: instruction file becoming too noisy with MCP notes. Mitigation: use
  pointer-style notes ("See mcp-kanban SKILL.md") for sections with multiple
  CLI refs rather than duplicating tool descriptions.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #574 itself IS the implementation task.
This research validates the scope and provides the gap inventory for the
builder. The task advances to `backlog` for architect review.
