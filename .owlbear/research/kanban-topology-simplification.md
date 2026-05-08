# Kanban Topology Simplification — Implementation Map

> **Owning task:** #1437 — Simplify kanban topology for deployment readiness
> **Date:** 2026-05-08  **Status:** Complete

## 1. Context and Question

The deployment readiness audit (`.owlbear/research/kanban-mcp-deployment-audit.md`) found the kanban engine exposes ~20 editable config fields for board topology. The approved direction (task #1437) removes configurable topology, hard-codes product constants, and splits implicit side effects into explicit operations. This research maps every approved-direction item to concrete file changes and identifies domain slices for the planner.

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| Kanban engine | `serve/kanban/src/owlbear_kanban/` (engine.py, config_loader.py, agent_view.py, storage.py, dispatch.py, decisions.py) | 1.0 — primary target |
| MCP server | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | 1.0 — tool layer |
| Cockpit bridge | `serve/cockpit/src/owlbear_cockpit/` (routes/read.py, models.py, view.py) | 0.9 — /api/board + mutation routes |
| Seed template | `seed/.owlbear/kanban/config.yml` | 0.8 — template for new projects |
| Agent guidance | `share/skills/h-mcp-kanban/SKILL.md`, `share/skills/r-pipeline-protocol/SKILL.md` | 0.8 — agent-facing docs |
| Deployment audit | `.owlbear/research/kanban-mcp-deployment-audit.md` | 0.7 — prior findings context |

## 3. Analysis — Config Surface Inventory

### Fields to hard-code as product constants

| Config field | Current value (seed) | Becomes | Affected files |
|---|---|---|---|
| `statuses` | 7 statuses (research→done) | Module constant | config_loader.py, engine.py |
| `priorities` | 5 levels (someday→critical) | Module constant | config_loader.py, engine.py |
| `paths.tasks_dir` | `"tasks"` | Literal in storage | config_loader.py, storage.py |
| `paths.archive_dir` | `"archive"` | Literal in storage | config_loader.py, storage.py |
| `pipeline.entry_status` | `"research"` | Derived from statuses[0] | config_loader.py |
| `pipeline.terminal_status` | `"done"` | Derived from statuses[-1] | config_loader.py |
| `pipeline.wave_size` | `4` | Module constant | config_loader.py, dispatch.py |
| `pipeline.claim_timeout` | `"1h"` | Module constant | config_loader.py, engine.py |
| `pipeline.default_priority` | `"important"` | Module constant | config_loader.py |
| `agents.agent_map` | `{}` | Remove entirely | config_loader.py, agent_view.py |
| `agents.agent_types` | `{}` | Remove entirely | config_loader.py |
| `agents.agent_compatibility` | `{}` | Remove entirely | config_loader.py, dispatch.py |
| `policy.archival_reasons` | 5 reasons | Module constant | config_loader.py, engine.py |
| `policy.non_impl_tags` | `[]` | Remove (dispatch internal) | config_loader.py, dispatch.py |
| `policy.status_predicates` | `{}` | Remove (dispatch internal) | config_loader.py, dispatch.py |
| `activity_log` | `false` | Remove (always on) | config_loader.py, engine.py |
| `next_id` | `1` | Remove (scan-based) | config_loader.py, storage.py |

### Fields to keep in config.yml

| Field | Reason |
|---|---|
| `schema: grouped` | Format marker for migration detection |

**Result:** config.yml shrinks from ~30 lines to 1 line.

### Side effects to extract

| Current behavior | Change |
|---|---|
| `pick_tasks` step 2 calls `resolve_pending_drs()` | Remove; new explicit `resolve_drs` MCP tool |
| `create_task` emits no activity event | Add "create" event |
| `activity_log` flag gates logging | Remove flag; always emit |

### Transition validation

`valid_transitions(status)` returns `all_statuses - {status}` (any-to-any except self). This is correct for the pipeline and doesn't need restriction — agents self-govern via pipeline-protocol. The function should remain but source its status set from constants instead of config.

### List filter semantics

The `archived` parameter handling has an impedance mismatch between layers: engine uses `archived: bool`, MCP/agent_view uses `status="archived"` + `archival_reason`. The agent_view translation is correct but undocumented. No code change needed; clarify in MCP tool descriptions.

## 4. Recommendation — Domain Slices for Decomposition

Confidence: 0.85. Challenge: skipped (decomposition plan, not a binary recommendation).

The approved direction maps cleanly to 8 implementation domains plus the existing verification probe (#1438). Dependencies are minimal — most slices are parallelizable after the engine constants slice.

| # | Domain | Scope | Dependencies |
|---|---|---|---|
| 1 | Engine: topology constants | Hard-code statuses, priorities, paths, pipeline, policy as module constants. Strip config_loader schema. Update BoardConfig model. | None — foundational |
| 2 | Engine: scan-based ID allocation | Replace `config.next_id` with filename-scan under create lock. Remove next_id from config. | Slice 1 (config schema change) |
| 3 | Engine: pick_tasks read-only | Remove `resolve_pending_drs()` call from pick_tasks pipeline. | None |
| 4 | Engine: activity always-on + create events | Remove `activity_log` toggle. Add "create" event to `create_task`. | Slice 1 (config schema change) |
| 5 | MCP: resolve_drs tool + annotation fixes | Add `resolve_drs` tool. Fix annotations/descriptions. Normalize error codes. Clarify list filter docs. | Slice 3 (pick_tasks change) |
| 6 | Cockpit: topology from constants | `/api/board` returns constants. Update `BoardOut` model. SSE unchanged. | Slice 1 |
| 7 | Seed + migration + docs | Strip seed config.yml. Add migration note for existing boards. Update README. | Slice 1 |
| 8 | Agent guidance | Update `h-mcp-kanban` for resolve_drs tool. Review `r-pipeline-protocol` for config refs. | Slice 5 |

**Existing:** #1438 (P4-01 verification probe) — depends on slices 1–6 completing.

## 5. Follow-Up Tasks

Delegate to planner: create 8 child tasks under #1437 at `backlog` status covering slices 1–8 above, with #1438 updated to depend on the implementation slices. Each task needs measurable AC grounded in the approved direction and this analysis.
