# MCP server.py L481 status_names Dict-Form Bug

> **Owning task:** #1172 — Fix MCP server.py L481 status_names dict-form assumption
> **Date:** 2026-04-29 **Status:** Complete

## 1. Context and Question

`move_task` in the MCP server wraps `collect_guidance` in `contextlib.suppress(Exception)`.
L481 extracts status names via `[s["name"] for s in board_config().statuses]` — a pattern
that assumes `statuses` is `list[dict]`. Post-Brief-C, `BoardConfig.statuses` is `list[str]`.
The dict subscript on a string raises `TypeError`, silently caught. Move guidance (forward-skip
warnings) has been broken on all new-schema boards since Brief-C landed.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L478-485 | Internal | 1.0 — bug site |
| `serve/kanban/src/owlbear_kanban/models.py` L137-222 | Internal | 1.0 — BoardConfig type |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` L22-120 | Internal | 1.0 — consumer |
| `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` L70-90 | Internal | 0.9 — stale mock |
| `serve/cockpit/src/owlbear_cockpit/routes/read.py` L53-66 | Internal | 0.8 — correct pattern |
| `.owlbear/research/1155-config-schema-grouping-validation.md` | Internal | 0.9 — discovery |

## 3. Analysis

### Root Cause

The code was written when `BoardConfig.statuses` was `list[dict[str, Any]]` (pre-Brief-C
legacy schema). Brief-C's model validator `_normalise_legacy` now converts all dict-form
statuses to plain strings at model creation. L481 was never updated.

### Impact

| Aspect | Assessment |
|--------|-----------|
| **Broken feature** | `collect_guidance("move", ...)` never receives `status_names` → forward-skip warnings never fire |
| **Severity** | Low-moderate — guidance is UX sugar for pipeline agents, not correctness-critical |
| **Blast radius** | Only affects `move_task` guidance. Other guidance call sites (edit_task, end_work, start_work) don't pass `status_names` |
| **Silent failure** | `contextlib.suppress(Exception)` hides the TypeError — no error logged |

### Fix (trivial, ~2 lines)

| Component | Current (broken) | Fix |
|-----------|-----------------|-----|
| `server.py` L481 | `[s["name"] for s in app_ctx.engine.board_config().statuses]` | `list(app_ctx.engine.board_config().statuses)` |
| `test_mcp_lifecycle_tools.py` L76 | `engine.board_config.return_value.statuses = [{"name": s} for s in [...]]` | `engine.board_config.return_value.statuses = [...]` |

`BoardConfig` already provides a `status_names` property (L222) that returns `self.statuses`
directly. The cockpit's `routes/read.py` uses this correctly as a reference pattern.

### Stale Research Docs

Three older research docs reference the dict-form pattern (informational, no code impact):
- `.owlbear/research/move-task-guidance-991.md` L34, L43
- `.owlbear/research/block-time-guidance-mcp-973.md` L51
- `.owlbear/research/status-priority-validation-814.md` L31, L65, L79

These are historical artifacts and do not need correction — they predate Brief-C.

## 4. Recommendation (confidence: .95)

**T1 — Autonomous fix.** No architecture, security, or user-facing format changes. The fix
is a 1-line change in `server.py` + 1-line test mock correction in `test_mcp_lifecycle_tools.py`.
No new tests needed — existing guidance tests in `test_guidance_rules_973.py` already cover
the `status_names` kwarg path. Once L481 stops raising, those tests exercise the live path.

Challenge: FALLBACK — trivial fix with .95 confidence; challenger adds no value.

## 5. Follow-up Tasks

1. Fix `server.py` L481 + stale test mock (single task at backlog — ready to build)
