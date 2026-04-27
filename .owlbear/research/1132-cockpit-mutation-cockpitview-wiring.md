# Cockpit Mutation CockpitView Wiring

> **Owning task:** #1132 — Wire cockpit mutation routes through CockpitView facade
> **Date:** 2026-04-27 **Status:** Complete

## 1. Context and Question

Task #1132 proposes routing all three mutation endpoints (`move`, `edit`, `release`) through the `CockpitView` facade instead of raw `KanbanEngine` calls. CockpitView already exists (engine.py L3077) with required OCC on all three methods. Dependencies #1130 and #1133 are archived.

**Question:** What are the concrete obstacles, and what is the minimal scope that delivers the highest value?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` L1–227 | 1.0 — current route implementations |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` CockpitView L3077–3250 | 1.0 — facade methods and signatures |
| 3 | `serve/kanban/src/owlbear_kanban/engine.py` move_task L1074–1140 | 0.9 — no same-status rejection |
| 4 | `serve/kanban/src/owlbear_kanban/engine.py` valid_transitions L563–580 | 0.9 — excludes current status |
| 5 | `serve/cockpit/src/owlbear_cockpit/deps.py` | 0.9 — only get_engine exists |
| 6 | `serve/cockpit/src/owlbear_cockpit/models.py` | 0.9 — TaskDetailOut schema |
| 7 | `tests/test_cockpit_mutation_api.py` L387–605 | 0.9 — 4 xfail release tests, all citing #1132 |
| 8 | `tests/test_cockpit_mutation_api_1134.py` | 0.8 — edit CAS tests (direct engine approach) |
| 9 | `serve/kanban/src/owlbear_kanban/models.py` L274, L322 | 0.8 — claimed_by Field(exclude=True) |
| 10 | `.owlbear/research/cockpit-mutation-occ-parity.md` | 0.7 — parent #1130 research |

## 3. Analysis

### 3.1 Current State per Route

| Route | OCC | CAS engaged? | Bug |
|-------|-----|-------------|-----|
| `POST /move` | Yes (MoveRequest.updated, precheck + engine CAS) | Yes | None — #1135 fixed this |
| `POST /edit` | Precheck only (req.updated != task.updated) | No — TOCTOU gap | #1134 in-progress to fix |
| `POST /release` | None — no request body | No | **Broken**: uses `task.claimed_by` which is `Field(exclude=True)` → always None → always 409 |

### 3.2 CockpitView Obstacles for Full Delegation

| Obstacle | Severity | Detail |
|----------|----------|--------|
| **CockpitView.edit_task lacks `title`** | High | Engine.edit_task accepts `title`, CockpitView.edit_task doesn't. Route EditRequest supports title. |
| **Param naming mismatch** | Medium | Route builds `add_tags`/`remove_tags` (engine names); CockpitView uses `add_tag`/`remove_tag` |
| **Block handling mismatch** | Medium | Route sets `blocked: bool` + `block_reason`; CockpitView uses sentinel pattern on `block_reason` alone |
| **Edit needs show_task for diffs** | Low | Tags/depends_on full-replacement → diff needs current state; can't remove show_task call |
| **Move same-status regression** | High | Engine.move_task allows same-status moves; route precheck rejects them. Removing precheck = behavior regression (existing test at test_cockpit_mutation_api.py L185) |
| **_task_to_detail claimed_by AttributeError** | Medium | SingleTaskResponse has no `claimed_by` attr; `_task_to_detail` references `task.claimed_by` → would crash |
| **_task_to_detail claimed bug** | Low | Current helper doesn't pass `claimed_at` → `claimed` always False in mutation responses (pre-existing) |

### 3.3 Option Comparison

| Option | Description | Fixes release? | Fixes edit TOCTOU? | Pattern consistency | Complexity |
|--------|-------------|---------------|-------------------|-------------------|------------|
| **A: Full CockpitView (all 3)** | Route all through CockpitView | Yes | Yes | Full | High — requires CockpitView.edit_task extension + helper rewrite |
| **B: CockpitView for move + release, engine for edit** | Hybrid: CockpitView where clean, engine where friction | Yes | Deferred to #1134 | Partial | Medium — move/release clean, edit untouched |
| **C: CockpitView release only, rest stays** | Minimal: fix broken release via CockpitView | Yes | Deferred to #1134 | Minimal | Low — release + DI + ReleaseRequest |
| **D: Direct engine (no CockpitView)** | Pass expected_updated to engine directly in all routes | Yes (needs claimed_at check) | Yes | None | Low — but duplicates CockpitView purpose |

### 3.4 Risk Assessment

- **Release is the critical deliverable.** The route is *actually broken* — not just a pattern gap. Any claimed task returns 409 because `claimed_by` is always None.
- **Edit TOCTOU is already being fixed by #1134** via direct engine CAS. CockpitView delegation for edit is redundant unless pattern consistency is prioritized.
- **Move is already correct** (#1135). CockpitView delegation adds source tagging but requires retaining the valid_transitions precheck.
- **CockpitView.edit_task title gap** is an engine-layer change — violates #1132's "route layer only" scope boundary.

## 4. Recommendation

**Option B (hybrid)** — confidence: 0.78

Route `move` and `release` through CockpitView; leave `edit` on direct engine (fixed by #1134). This delivers the highest value within the stated scope boundary.

Specific changes:
1. **deps.py**: Add `get_cockpit_view` DI provider (wraps get_engine)
2. **release route**: Add `ReleaseRequest(updated: str)`, delegate to `CockpitView.release_task(expected_updated=req.updated)`, catch `ConcurrencyError` → 409
3. **move route**: Delegate to `CockpitView.move_task(expected_updated=req.updated)`, retain valid_transitions precheck (read via `view.engine` or separate engine dep)
4. **_task_to_detail**: Fix to use `claimed_at` (from SingleTaskResponse) instead of `claimed_by`, fixing the pre-existing `claimed: False` bug
5. **Error mapping**: `ConcurrencyError` → 409, `NotFoundError` → 404, `ValidationError` → 422

**Deferred:** CockpitView.edit_task title support + full edit delegation → separate task.

Challenge: reconsider (confidence 0.58). Challenger flagged: underestimated edit prerequisite surface, move same-status regression risk, and acceptance-surface undercount. All accepted and incorporated — resulted in recommending Option B (hybrid) instead of Option A (full delegation).

## 5. Follow-up Tasks

1. **Extend CockpitView.edit_task with title param** — engine-layer prerequisite for future full delegation
2. **Refine #1132 AC** — reduce scope from "all three routes" to "move + release through CockpitView; edit via #1134"
3. **Update release tests** — 5 existing release tests send no body; need ReleaseRequest with `updated`
