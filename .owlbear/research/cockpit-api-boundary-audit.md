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
| Cockpit → kanban `storage_io` | **Minor hygiene** | Generic utility; Cockpit owns `ideas.md` |
| Cockpit → events path hardcoding | **Config-drift risk** | `"archive"` hardcoded; configurable via `config.paths.archive_dir` |

### Finding 1: Decision Resolution Lifecycle (Substantive)

Cockpit rewrites decision file content (`_rewrite_response` → `path.write_text()`) and moves files from `pending/` to `resolved/` via `move_to_resolved()`. This means Cockpit owns the DR file lifecycle — format, content transformation, and storage layout transitions.

The kanban `decisions.py` module already has helpers (`parse_dr`, `canonical_summary`, `move_to_resolved`) but lacks a single `resolve_decision()` entry point that encapsulates rewrite+move+side-effects.

**Risk:** Any change to DR file format, frontmatter schema, or storage layout requires coordinated changes in both packages.

### Finding 2: Events Route Hardcodes Configurable Path (Config-Drift)

`routes/events.py` constructs `kanban_dir / "archive"` for SSE file-watching. The engine stores this as `self._archive_dir` (private) derived from `config.paths.archive_dir` (defaults to `"archive"` but is configurable). If archive_dir config changes, SSE events for archived tasks silently stop working.

`decisions/` and `activity.jsonl` paths are topology-fixed (not configurable) — those hardcodings are safe.

**Fix options:** Engine already exposes `board_config()` publicly. Cockpit could derive from `engine.board_config().paths.archive_dir`, or engine could add a public `archive_dir` property.

### Finding 3: `atomic_write` Import (Export Hygiene)

`routes/ideas.py` imports `atomic_write` from `owlbear_kanban.storage_io` (not in `__all__`). This is a generic crash-safe file-write utility, not kanban domain logic. Cockpit legitimately owns `ideas.md`.

**Risk:** Minimal. The utility is stable, stateless, and has no kanban-domain coupling.

## 4. Recommendation

**Fix Finding 1** by adding a `resolve_decision(path, response, notes, engine)` function to `owlbear_kanban.decisions` that owns the full rewrite-move-side-effect sequence. Cockpit calls it instead of performing the lifecycle itself.

**Fix Finding 2** by either:
- (a) Adding a public `archive_dir` property to `KanbanEngine`, or
- (b) Cockpit reads `engine.board_config().paths.archive_dir` (already available)

**Accept Finding 3** — promote `atomic_write` to `__all__` if desired, but current usage is low-risk and intentional.

Confidence: 0.80 (post-challenge — originally 0.78, recalibrated after challenger correctly narrowed the decision write issue and dismissed models concern).

Challenge: reconsider → revised severity hierarchy; dropped Finding 4 (models) as non-violation per repo convention; narrowed Finding 1 to write-side only; recalibrated Finding 3 to hygiene-only.

## 5. Follow-up Tasks

1. **Kanban: expose `resolve_decision()` in decisions module** — encapsulate rewrite+move+side-effects (T1 — refactor within existing module)
2. **Cockpit: delegate decision resolution to kanban's new API** — remove `path.write_text()` and direct file manipulation (T1 — refactor)
3. **Events route: use `board_config().paths.archive_dir`** — replace hardcoded `"archive"` (T1 — config-drift fix)
