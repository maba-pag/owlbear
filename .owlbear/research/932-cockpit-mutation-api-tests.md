# Cockpit Mutation API — RED Phase Test Feasibility

> **Owning task:** #932 — P1-06: RED — Cockpit mutation API tests
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #932 requires RED-phase failing tests for three cockpit mutation endpoints:
`POST /api/tasks/{id}/move`, `POST /api/tasks/{id}/edit`, `POST /api/tasks/{id}/release`.
Tests include conflict detection (D9), allowlisted field editing, audit logging, and error cases.

**Question:** Are these tests feasible with the current engine and cockpit infrastructure? What cockpit-level logic gaps exist between the engine's raw behaviour and the AC requirements?

## 2. Sources Studied

| # | Source | Relevance | What was used |
|---|--------|-----------|---------------|
| S1 | `serve/kanban/src/owlbear_kanban/engine.py` — mutation methods | 1.0 | Method signatures: `move_task`, `edit_task`, `release_task`, `claim_task` |
| S2 | `serve/kanban/src/owlbear_kanban/activity_log.py` | 0.9 | JSONL logging format, `actor` parameter flow |
| S3 | `tests/test_cockpit_read_api_930.py` + `test_cockpit_read_api.py` | 1.0 | Fixture pattern: `_make_board`, DI override, TestClient |
| S4 | `.owlbear/briefs/draft-cockpit/decisions.md` — D9, D12 | 1.0 | Conflict detection = `updated`-timestamp save-time check; backend exposes only allowed verbs |
| S5 | `.owlbear/briefs/draft-cockpit/brief.md` — Phase 1 spec | 0.9 | Endpoint contracts, allowlisted fields, audit requirements |
| S6 | `serve/cockpit/src/owlbear_cockpit/` — current read-only API | 0.8 | Adapter pattern, DI via `get_engine`, route structure |

## 3. Analysis

### Engine-vs-Cockpit Behaviour Gaps

| AC Requirement | Engine Behaviour | Cockpit Route Must |
|----------------|------------------|--------------------|
| Move validates `valid_transitions` | `move_task` accepts any configured status | Check `valid_transitions(current_status)` before delegating |
| Edit accepts full `tags`/`depends_on` lists | Engine uses `add_tags`/`remove_tags`, `add_deps`/`remove_deps` | Compute diffs: add = new − current, remove = current − new |
| D9: `updated` snapshot → 409 on stale | `edit_task` overwrites unconditionally | Re-read task, compare `updated` to request snapshot, 409 if mismatch |
| Release unclaimed → error | `release_task` is a no-op (no exception) | Check `claimed_by`; return 409 or 400 if not claimed |
| Block via `block_reason` | `blocked` and `block_reason` are independent | Set both `blocked=True` + `block_reason` atomically; null clears both |
| `actor: "cockpit"` in activity log | Actor = `self._agent_name` | Construct engine with `agent_name="cockpit"`, `activity_log=True` |
| Non-allowlisted field → 422 | Engine accepts anything in `edit_task` | Pydantic request model with explicit field allowlist |

### Test Structure (recommended)

| Class | Endpoint | Tests |
|-------|----------|-------|
| `TestMoveTask` | `POST /api/tasks/{id}/move` | Happy path, invalid target 422, non-existent task 404 |
| `TestEditTask` | `POST /api/tasks/{id}/edit` | Allowlisted fields, non-allowlisted 422, missing `updated` 422, stale `updated` 409, block/unblock |
| `TestReleaseTask` | `POST /api/tasks/{id}/release` | Happy path, unclaimed error, non-existent 404 |
| `TestAuditLogging` | All mutations | Verify `activity.jsonl` entries with `actor: "cockpit"` |

### Fixture Adaptation

Existing test fixtures need two changes for mutation tests:
1. **Enable `activity_log: true`** in `_CONFIG_YAML` (existing tests disable it).
2. **Pre-claim a task** via `seed_engine.claim_task("1")` for release tests.

## 4. Recommendation (confidence: .92)

**Proceed directly to RED phase.** All engine methods exist. The six cockpit-level logic gaps are well-defined and will be exercised by the tests (they'll fail because the routes don't exist yet, which is exactly what RED phase requires).

No engine changes needed. No architectural decisions pending — D9 and D12 are resolved in the brief.

Challenge: skipped — T1 autonomous, no recommendation between competing approaches.

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #932 AC is self-contained and complete. The GREEN phase (#934) already exists as a sibling task with dependency on #932.
