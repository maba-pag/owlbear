# Standardize MCP Tool Error Signaling

> **Owning task:** #680 — Standardize MCP tool error signaling (ToolError vs error strings)
> **Date:** 2026-04-08 **Status:** Complete

## 1. Context and Question

Should OwlBear unify all MCP tool error signaling to `ToolError` (`isError: true`), or keep the current return-type-driven dual pattern? The task body flagged inconsistencies; this audit quantifies them.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|-----------|-----------|
| S1 | MCP Spec §6 (2025-11-25) | modelcontextprotocol.io/specification/2025-11-25/server/tools | 1.0 |
| S2 | MCP Spec §6 (2025-06-18) | modelcontextprotocol.io/specification/2025-06-18/server/tools | 0.9 |
| S3 | FastMCP SDK lowlevel/server.py | `.venv/.../mcp/server/lowlevel/server.py` L467–584 | 1.0 |
| S4 | Prior research #540 | `.owlbear/research/dual-error-pattern-mcp-conventions.md` | 0.9 |
| S5 | Prior research #496 | `.owlbear/research/mcp-server-error-return-standardization.md` | 0.9 |
| S6 | r-architecture-standards | `share/skills/r-architecture-standards/SKILL.md` | 1.0 |

## 3. Analysis

### 3a. Full Audit — 28 Tools Across 4 Servers

| Server | Tool | Return type | Error pattern | isError | Bug? |
|--------|------|------------|---------------|---------|------|
| **kanban** | list_tasks | `list[dict]` | ToolError | true | — |
| | show_task | KanbanTask | ToolError | true | — |
| | create_task | KanbanTask | ToolError | true | — |
| | move_task | KanbanTask | ToolError | true | — |
| | edit_task | KanbanTask | ToolError | true | — |
| | start_work | KanbanTask | ToolError | true | — |
| | end_work | KanbanTask | ToolError | true | — |
| | pick_tasks | `dict` | ToolError | true | — |
| **knowledge** | search_knowledge | `list \| str` | `"error: ..."` | false | — |
| | list_sources | `list` | ToolError(`"error: ..."`) | true | **DOUBLE-PREFIX** |
| | ingest_document | `str` | `"error: ..."` | false | — |
| | list_entities | `list \| str` | `"error: ..."` | false | — |
| | get_stats | TypedDict | ToolError(`"error: ..."`) | true | **DOUBLE-PREFIX** |
| | bookmark_source | `str` | `"error: ..."` | false | — |
| | list_bookmarks | `list` | `[]` (graceful) | n/a | — |
| | import_scope | `str` | `"error: ..."` (core lib) | false | — |
| | export_scope | `str` | `"error: ..."` (core lib) | false | — |
| **memory** | get_knowledge | `list[dict]` | (none explicit) | n/a | — |
| | record_learning | `str` | `"error: ..."` | false | — |
| | list_entries | `list \| str` | (none explicit) | n/a | — |
| | set_approval_state | `str` | **MIXED** | mixed | **MIXED** |
| | mark_for_deletion | `str` | ToolError | true | — |
| **project** | project_info | TypedDict | ToolError | true | — |
| | project_list | `list` | `[]` (graceful) | n/a | — |
| | project_readme | `str` | `"error: ..."` | false | — |
| | project_structure | `str` | `"error: ..."` | false | — |

**Summary:** 14 ToolError-only, 9 error-string-only, 1 mixed, 4 graceful/none. 3 bugs identified.

### 3b. Three Bugs Found

1. **Double-prefix (list_sources):** `raise ToolError("error: source store not available")` — "error:" is redundant because ToolError already sets `isError: true`.
2. **Double-prefix (get_stats):** Same pattern — `raise ToolError("error: graph store not available")`.
3. **Mixed pattern (set_approval_state):** Raises `ToolError` for missing entry but returns `"error: ..."` string for invalid transitions. Same tool, two patterns.

### 3c. Option Comparison

| Criterion | A: Full ToolError unification | B: Fix bugs + reaffirm convention | C: Status quo |
|-----------|------------------------------|-----------------------------------|---------------|
| Consistency | All errors → `isError: true` | Return-type-driven (documented) | Inconsistent |
| Spec alignment | Full (§6 SHOULD) | Partial (dual is spec-valid) | Partial |
| Agent simplification | Single error path | Dual but predictable | Dual, unclear rules |
| Code changes | ~10 tools | ~3 tools | 0 |
| Test changes | ~40 assertions | ~10 assertions | 0 |
| Runtime consumers | approve.py needs update | approve.py unchanged | No change |
| Risk | Medium — breaking change | Low — targeted fixes | None |
| Core lib impact | Wrappers needed | None | None |

### 3d. Key Finding: `approve.py` Is a Runtime Consumer

`serve/mcp-memory/src/owlbear_mcp_memory/approve.py` checks **both** patterns at 3 callsites:
```python
if result.isError or text_r.startswith("error:"):
```
Full ToolError unification would make the string check dead code but not break it. However, it means the blast radius extends beyond tests.

## 4. Recommendation (.82 confidence)

**Option B: Fix 3 bugs, reaffirm the return-type-driven convention.**

Rationale:
- The dual pattern has sound design rationale: typed returns can't embed error strings → ToolError; string returns can → `"error: ..."` prefix. Prior research #540 validated this.
- The MCP spec uses SHOULD, not MUST, for `isError: true` recommendations. Both patterns are spec-valid (S1, S2).
- Full unification (Option A) has disproportionate cost at "nice-to-have" priority: ~40 test assertions, 1 runtime consumer, core library wrappers.
- The 3 bugs are genuine inconsistencies that confuse agents. Fixing them + tightening docs satisfies AC1 and AC2.

If evidence emerges that agents struggle with the dual pattern, a follow-up task for full unification is created below.

Challenge: reconsider (.70) — Challenger correctly identified: (1) approve.py runtime consumer, (2) test churn underestimate (49 assertions, not 15), (3) core library boundary leak making full unification push the dual pattern one layer down. Revised from .85 to .82, adopted phased approach.

## 5. Follow-up Tasks

- **Phase 1 (T1):** Fix 3 bugs + tighten convention docs — created as follow-up task
- **Phase 2 (T2, gated):** Full ToolError unification — created as follow-up task, gated on evidence
