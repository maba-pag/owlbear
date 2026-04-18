# Cockpit `block:user` Tag Lifecycle in Mutation Routes

> **Owning task:** #990 — Cockpit `block:user` tag lifecycle in mutation routes
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Cockpit-initiated blocks are indistinguishable from agent-initiated blocks. The `block:user` tag provides a best-effort provenance marker so agents reading a blocked task know whether to create a Decision Request. This research validates the implementation approach for injecting `block:user` in the Cockpit mutation route.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | Codebase | 1.0 — injection target |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` L642–645 | Codebase | 0.9 — engine tag semantics |
| 3 | `.owlbear/briefs/draft-blocked-task-dr-enforcement/stances/architect.md` Q4 | Design doc | 1.0 — architect-approved implementation |
| 4 | `.owlbear/briefs/draft-blocked-task-dr-enforcement/decisions.md` D3 | Decision | 1.0 — authoritative decision |
| 5 | `tests/test_cockpit_mutation_api.py` | Codebase | 0.9 — existing test patterns |

## 3. Analysis

### Research Gate Checklist

| # | Gate | Verdict |
|---|------|---------|
| 1 | Theoretical validity | **Pass** — tag-based provenance is standard; no auth needed per D3 |
| 2 | Environment audit | **Pass** — no existing mechanism distinguishes block origins |
| 3 | Prior art | **N/A** — internal feature; architect stance + D3 serve as authority |
| 4 | Technical feasibility | **Pass** — engine `add_tags`/`remove_tags` are idempotent (dedup on add, silent on missing remove) |
| 5 | Architecture fit | **Pass** — injection is post-`_build_edit_kwargs`, pre-`engine.edit_task`; no engine changes |
| 6 | Implementation approach | **Pass** — architect provided exact code; edge cases analyzed below |
| 7 | Testing strategy | **Pass** — 3 integration tests extend existing `TestFromAC_EditTask` class |

### Edge Case: Tag-Diff Conflict

When a user sends both `tags: [...]` AND `block_reason`, `_apply_list_diff` runs first. If the task already has `block:user` and the user's desired tag list omits it, `_apply_list_diff` puts `block:user` into `remove_tags`. The post-injection code must override this.

| Scenario | `_apply_list_diff` result | Post-injection fix |
|----------|--------------------------|-------------------|
| Block + tags omit `block:user` | `remove_tags: ["block:user"]` | Strip from `remove_tags`, add to `add_tags` |
| Unblock + tags include `block:user` | `add_tags: ["block:user"]` | Strip from `add_tags`, add to `remove_tags` |
| Block + tags include `block:user` | `add_tags: ["block:user"]` | Idempotent — engine deduplicates |
| Block + no tags field | no tag kwargs | `setdefault("add_tags", []).append(...)` |

The architect's code handles all four scenarios correctly.

### Implementation Location

**File:** `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`
**Injection point:** `edit_task` route, after `kwargs = _build_edit_kwargs(req, task)`, before `engine.edit_task(str(task_id), **kwargs)` (line ~173).

### Test Plan

Three new tests in `tests/test_cockpit_mutation_api.py`, extending `TestFromAC_EditTask`:

1. **Block → has `block:user`**: POST edit with `block_reason` set → response tags include `block:user`
2. **Unblock → `block:user` removed**: Pre-block with tag, POST edit with `block_reason: null` → response tags exclude `block:user`
3. **Block + explicit tags → `block:user` merged**: POST edit with `block_reason` + `tags: ["scope:test"]` → response tags include both `scope:test` and `block:user`

## 4. Recommendation

Proceed with architect's exact implementation (confidence: **0.92**).

The approach is minimal (~8 LOC production, ~50 LOC tests), requires no engine changes, and the edge-case analysis confirms correctness. The only risk is the tag-diff conflict scenario, which the architect's code already handles.

Challenge: skipped (trivial implementation with architect-approved code; no alternative approaches to evaluate).

## 5. Follow-up Tasks

Task #990 itself is the implementation task — already scoped with AC and files. No additional follow-up tasks needed; the existing AC covers all identified scenarios including the tag-diff conflict edge case (AC item 6: "block with explicit tags list").
