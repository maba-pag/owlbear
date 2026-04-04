# Expand mcp-kanban SKILL.md with Agent Workflow and Per-Tool Reference

> **Owning task:** #563 — Expand mcp-kanban SKILL.md with agent workflow pattern and per-tool reference
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #563 adds new sections to `skills/mcp-kanban/SKILL.md`: agent workflow
pattern (3-step MCP lifecycle), per-tool parameter reference, Channel B protocol,
compound vs single tool guidance, error handling differences, and claim/release
pitfalls. Must pass validation tests in `tests/test_mcp_tool_references_483.py`.

Prior research: `docs/research/mcp-tool-references-alongside-cli.md` (sections
3a-3d) already maps CLI-to-MCP and documents the compound workflow. This is a
validation pass confirming the approach and documenting exact content requirements.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `docs/research/mcp-tool-references-alongside-cli.md` | Research | .95 — CLI-to-MCP mapping, compound workflow, pitfalls |
| 2 | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` | Codebase | .95 — actual tool signatures, params, error handling |
| 3 | `packages/mcp-kanban/src/owlbear_mcp_kanban/models.py` | Codebase | .90 — KanbanTask model (return type) |
| 4 | `tests/test_mcp_tool_references_483.py` | Codebase | .90 — exact validation patterns to pass |
| 5 | `skills/mcp-kanban/SKILL.md` (current) | Codebase | .85 — existing content to preserve/extend |

## 3. Analysis

### 3a. Test Requirements (from test_mcp_tool_references_483.py)

The validation test checks four things in the mcp-kanban SKILL.md body:

1. A heading matching `## Agent Workflow` (case-insensitive regex `agent\s+workflow`)
2. `start_work` mentioned in that section
3. `end_work` mentioned in that section
4. `edit_task` mentioned in that section (Channel B step)

### 3b. Content Gap Analysis

| AC Item | Current SKILL.md | Needed |
|---------|-----------------|--------|
| Agent Workflow Pattern section | Missing | 3-step lifecycle: start_work, edit_task, end_work |
| Per-tool parameter reference | Partial (summary table exists) | Full table with types and defaults per tool |
| Channel B protocol section | Missing | edit_task(append_body=..., timestamp=true) |
| Compound vs single guidance | Partial (start_work/end_work details exist) | When to use each, side-by-side comparison |
| Error handling differences | Exists (§ Error handling) | Already adequate — ToolError vs `error:` documented |
| Claim/release pitfall | Missing | Same-call forbidden, prefer compounds |

### 3c. Parameter Verification (from server.py)

All 8 tools verified against actual source. Key findings:

- `edit_task` has 17 parameters (most complex tool), all verified
- `end_work` outcome is `Literal["success", "fail", "block", "reject"]`
- `start_work` auto-generates claim via `kanban-md agent-name` when omitted
- `create_task.parent` is `int` (0=none), not `str`
- `pick_task` has 4 optional params (status, claim, move, tags)
- `list_tasks.blocked` is `bool | None` (tri-state: True=blocked, False=not-blocked, None=all)

### 3d. Error Handling Correction

Current SKILL.md lists `edit_task` under ToolError tools. Server source confirms
`edit_task` **does** raise ToolError (rc != 0 path). Current doc is accurate.
The prior research doc (section 3d) listed edit_task under `error:` string tools —
that was incorrect. Server lines 348-353 show `raise ToolError(msg)`.

## 4. Recommendation (.90 confidence)

T1 — Autonomous. This is documentation for existing capabilities, no design decisions.
All content derives from verified source code. Existing sections preserved, new sections
are additive.

Challenge: FALLBACK — research is validation-only with direct source verification.

Implementation is straightforward: add 3 new sections (~60-80 lines) to the
existing SKILL.md while preserving all current content. The builder should:

1. Add `## Agent Workflow Pattern` with 3-step lifecycle
2. Add `## Per-Tool Parameter Reference` with full parameter tables
3. Add `## Channel B Protocol` with MCP equivalent
4. Add `## Compound vs Single Tool Guidance` section
5. Add `## Pitfalls` section for claim/release same-call issue

## 5. Follow-up Tasks

No new tasks needed. Task #563 already has complete AC and is scoped to a single
file. Implementation proceeds directly to builder after architect review.
