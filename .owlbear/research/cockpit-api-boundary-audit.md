# Cockpit Public API Boundary Audit

> **Owning task:** #1849 — Cockpit public API boundary audit
> **Date:** 2026-05-24 **Status:** Complete

## 1. Context and Question

Does Cockpit use exposed public APIs from other modules, or does it directly reach into private members or filesystem-owned data that belongs to other packages?

Scope: Cockpit backend (`serve/cockpit/`) imports and filesystem access into `owlbear_kanban` and `owlbear_memory`. Frontend was audited and found fully decoupled (communicates only via REST/SSE).

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/cockpit/src/owlbear_cockpit/` (all files) | Codebase | 1.0 |
| `serve/kanban/src/owlbear_kanban/__init__.py` | Public API surface | 1.0 |
| `serve/kanban/src/owlbear_kanban/engine.py` | Engine public properties | 1.0 |
| `serve/kanban/src/owlbear_kanban/topology.py` | Fixed product topology | 0.9 |
| `serve/kanban/src/owlbear_kanban/decisions.py` | Decision helpers | 0.9 |
| `serve/memory/src/owlbear_memory/__init__.py` | Memory public API | 0.8 |
| `serve/cockpit/web/src/` (frontend) | Frontend boundary check | 0.7 |

## 3. Analysis

### Boundary Classification

| Area | Verdict | Detail |
|------|---------|--------|
| Frontend (React) → Backend | **Clean** | All communication via `/api/*` REST + `/api/events` SSE |
| Cockpit → owlbear_memory | **Clean** | All imports from `__all__`-exported symbols |
| Cockpit → owlbear_kanban models | **Acceptable** | Direct submodule import is repo-standard (used by mcp-kanban too) |
| Cockpit → kanban decisions (read) | **Acceptable** | `deps.py` explicitly provides path; `parse_dr` is the module's purpose |
| Cockpit → kanban decisions (write) | **VIOLATION** | `path.write_text()` + `move_to_resolved()` = lifecycle ownership |

### Finding 1: Decision Resolution Lifecycle (Substantive)

Cockpit rewrites decision file content (`_rewrite_response` → `path.write_text()`) and moves files from `pending/` to `resolved/` via `move_to_resolved()`. This means Cockpit owns the DR file lifecycle — format, content transformation, and storage layout transitions.

The kanban `decisions.py` module already has helpers (`parse_dr`, `canonical_summary`, `move_to_resolved`) but lacks a single `resolve_decision()` entry point that encapsulates rewrite+move+side-effects.

**Risk:** Any change to DR file format, frontmatter schema, or storage layout requires coordinated changes in both packages.

### Scope Stop (AC 3 Compliance)

Per AC 3 and user direction, this audit stops at Finding 1. Additional observations discovered during the broad inventory pass are intentionally parked outside this task and are not part of this deliverable.

## 4. Recommendation

**Fix Finding 1** by adding a `resolve_decision(path, response, notes, engine)` function to `owlbear_kanban.decisions` that owns the full rewrite-move-side-effect sequence. Cockpit calls it instead of performing the lifecycle itself.

Confidence: 0.80 (post-challenge).

Challenge: reconsider -> narrowed the final recommendation to decision write-side coupling only.

## 5. Follow-up Tasks

1. **Kanban + Cockpit: expose and consume `resolve_decision()` boundary API** — encapsulate rewrite+move+side-effects in kanban and delegate from cockpit (T1 — boundary refactor)
