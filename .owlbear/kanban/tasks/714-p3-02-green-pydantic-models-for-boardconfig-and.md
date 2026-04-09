---
id: 714
title: 'P3-02: GREEN — Pydantic models for BoardConfig and TaskRecord'
status: todo
priority: needed
created: 2026-04-09T03:24:35.9375742+02:00
updated: 2026-04-09T06:20:50.5463912+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 713
class: standard
---

## Objective
Implement internal Pydantic models for `BoardConfig` and `TaskRecord` inside `serve/mcp-kanban/src/owlbear_mcp_kanban/`.

Brief: see parent #712

## AC
- [ ] `BoardConfig` model matches config.yml schema (version, board.name, tasks_dir, statuses as list of dicts, priorities, defaults, claim_timeout, next_id, tui — preserved)
- [ ] `TaskRecord` model matches task file frontmatter spec (all fields including claimed_by, claimed_at, started, completed, class — preserved via extra='allow' or equivalent)
- [ ] Unknown fields preserved via model config
- [ ] Timestamps stored as strings (ISO 8601), not datetime objects
- [ ] All T01 (#713) tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` (new)

[[2026-04-09]] Thu 06:20
## Architecture Review

### Context
GREEN implementation task for `engine_models.py`. **Critical finding: the deliverable already exists.** #713's builder created `engine_models.py` (86 lines, 4 models) during the RED task's pipeline lifecycle — 44 tests pass, 100% coverage. All AC for #714 is already satisfied.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `BoardConfig` matches config.yml schema (version, board.name, tasks_dir, statuses, priorities, defaults, claim_timeout, next_id, tui) | SATISFIED — `engine_models.py` L40-57: `BoardConfig` with all fields, `BoardInfo`/`BoardDefaults` sub-models. Verified against `.owlbear/kanban/config.yml` (version=10, claim_timeout="1h", next_id=734, tui section present). | None — already implemented |
| `TaskRecord` matches task file frontmatter (all fields incl. claimed_by, claimed_at, started, completed, class — preserved via extra='allow') | SATISFIED — `engine_models.py` L59-86: 13 explicit fields + `extra="allow"` for `class`, `started`, `completed`. Verified against task files (e.g. task #2 has `started`, `completed`, `class`). | None — already implemented |
| Unknown fields preserved via model config | SATISFIED — `ConfigDict(extra="allow")` on all 4 model classes | None |
| Timestamps stored as strings (ISO 8601), not datetime | SATISFIED — `created: str`, `updated: str`, `claimed_at: str \| None` | None |
| All T01 (#713) tests pass | SATISFIED — 44/44 pass per #713 reviewer (confidence .98) | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Engine-internal data models only |
| Interface clarity | PASS | 4 models with clear field types and docstrings |
| Dependency correctness | PASS | #713 (RED) is `done` |
| Module layering | PASS | `engine_models.py` inside `owlbear_mcp_kanban` package, separate from MCP-boundary `models.py` |
| TDD compliance | PASS | RED task #713 completed first |
| KISS/YAGNI | PASS | Minimal models with `extra="allow"` — no over-engineering |
| Premise challenge | PASS (redundant) | Deliverable already exists from #713 builder. Task is effectively a pipeline pass-through. Not rejecting because the file does need to exist — the duplicate work arose from RED/GREEN task split where the builder in RED already delivered the GREEN work. |
| Pattern consistency | PASS | Follows existing `models.py` patterns: `ConfigDict`, `Field(default_factory=list)`, `str` timestamps |
| Security surface | N/A | Engine-internal models reading local YAML files — no new system boundary |
| Single domain | PASS | Kanban engine domain only |

### Architecture Notes

1. **Redundancy origin**: The planner created RED/GREEN task pairs (#713/#714), but the pipeline processes each task through test-writer → builder → reviewer → docs. The builder in #713 implemented `engine_models.py` to make the tests pass — which is exactly what #714 asks for. All downstream agents should treat this as a pass-through.
2. **Model design verified**: `BoardInfo`/`BoardDefaults` sub-models correctly decompose nested config.yml structure. `extra="allow"` on all models preserves vendor fields (`tui`, `class`, `started`, `completed`). Timestamp-as-string strategy avoids Go nanosecond drift.
3. **File location**: `serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py` — correct per parent #712 brief (D6: engine inside mcp-kanban).

### Challenge Results
- Challenger: FALLBACK — agent not available in current agent set
- Architect response: Independent evaluation confirms all AC already satisfied. Redundancy is a planning artifact, not a quality concern.

### Verdict: APPROVE
### Action Taken: Approved #714 to todo as pipeline pass-through. All AC already satisfied by #713's builder implementation (`engine_models.py`, 86 lines, 44 tests, 100% coverage). Downstream agents should confirm existing deliverables and pass through.
