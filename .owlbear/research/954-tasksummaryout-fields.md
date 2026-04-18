# Extend TaskSummaryOut with block_reason and claimed

> **Owning task:** #954 — Extend TaskSummaryOut with block_reason and claimed fields
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

The cockpit `TaskSummaryOut` model is missing `block_reason` and `claimed` — both present in the engine's `TaskSummary`. The kanban board UI needs these for block-badge tooltips and running indicators. Discovered during #931 research (see `.owlbear/research/931-kanban-board-tests.md` §3.1).

**Question:** What changes are needed to expose these fields, and are there any risks?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/models.py` L98–132 | Codebase | 1.0 |
| 2 | `serve/cockpit/src/owlbear_cockpit/models.py` L1–17 | Codebase | 1.0 |
| 3 | `serve/cockpit/src/owlbear_cockpit/routes/read.py` L73–82 | Codebase | 1.0 |
| 4 | `tests/test_cockpit_read_api.py` | Codebase | 0.9 |
| 5 | `.owlbear/research/931-kanban-board-tests.md` | Prior research | 0.8 |

## 3. Analysis

### Current state

| Layer | `block_reason` | `claimed` |
|-------|---------------|-----------|
| Engine `TaskSummary` | ✅ `str \| None = None` | ✅ `bool = False` |
| Adapter `list_tasks()` | ✅ pass-through | ✅ pass-through |
| Route constructor | ❌ not mapped | ❌ not mapped |
| `TaskSummaryOut` model | ❌ missing | ❌ missing |
| Tests | ❌ no assertions | ❌ no assertions |

### Gap analysis

The adapter already returns engine `TaskSummary` objects directly — no adapter changes needed. The gap is in two places:

1. **Model** — `TaskSummaryOut` needs both fields (with same defaults as engine model).
2. **Route** — `list_tasks` route manually constructs `TaskSummaryOut`; needs `block_reason=s.block_reason, claimed=s.claimed` added.

Note: `TaskDetailOut` already has `block_reason` (but not `claimed`). `claimed` isn't relevant for detail since the full `Task` model uses `claimed_by: str | None` — a richer representation. The summary's boolean `claimed` is only meaningful for list views.

### Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking API consumers | Low | Low | Additive change; new fields have defaults |
| Serialisation mismatch | Very low | Low | Pydantic defaults match engine defaults |

## 4. Recommendation

Proceed with direct implementation. Confidence: **0.95**.

This is a mechanical 3-file change (model + route + tests). No design decisions, no alternative approaches. The pattern is already established by `TaskDetailOut.block_reason`.

Challenge: N/A — trivial research, no recommendation to challenge.

Tier: **T1 — Autonomous** (additive field pass-through, no architecture or security impact).

## 5. Implementation Approach

1. **`models.py`** — Add `block_reason: str | None = None` and `claimed: bool = False` to `TaskSummaryOut`.
2. **`routes/read.py`** — Add `block_reason=s.block_reason` and `claimed=s.claimed` to the `TaskSummaryOut(...)` constructor in `list_tasks`.
3. **`tests/test_cockpit_read_api.py`** — Assert `block_reason` appears in blocked-task summary responses; assert `claimed` field exists in task summaries; add a test for a claimed task scenario.

### Testing strategy

- Extend `test_tasks_filter_by_blocked_returns_only_blocked_tasks` to verify `block_reason` value.
- Add test for `claimed` using `start_work` in the seed fixture.
- Extend `test_tasks_each_summary_has_required_fields` to include new fields.
