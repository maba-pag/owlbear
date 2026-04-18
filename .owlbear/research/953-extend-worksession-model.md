# Extend WorkSession Model with Agent, Started_at, Duration, Outcome

> **Owning task:** #953 — Extend WorkSession model with agent, started_at, duration, outcome fields
> **Date:** 2026-04-18  **Status:** Complete

## 1. Context and Question

Task #953 (child of #926, depends on #952) requires extending the `WorkSession` dataclass from 2 fields (`task_id`, `state`) to 6 fields. The cockpit Activity tab needs `agent`, `started_at`, `duration`, and `outcome` to render session rows. All data must be derived from existing JSONL events — no new log schema (Brief D10).

Questions: (a) Can all 4 new fields be derived from existing JSONL event data? (b) What edge cases exist for each field? (c) What's the simplest implementation approach?

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py` L48–117 | .95 | WorkSession dataclass + `_collect_task_sessions()` state machine |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py` L752 | .95 | `claim` event: `detail=self._agent_name`, `actor=self._agent_name` |
| 3 | `serve/kanban/src/owlbear_kanban/engine.py` L905–920 | .95 | `end_work` detail formats: `success:`, `reject:`, `outcome=fail`, `blocked:` |
| 4 | `serve/kanban/tests/test_list_sessions.py` (500 lines) | .90 | 23 tests; assert only on `.task_id` and `.state`; no direct WorkSession construction |
| 5 | `serve/kanban/tests/test_list_sessions_952.py` (340 lines) | .85 | Confirms prefixed detail format for success/reject after #952 fix |
| 6 | `.owlbear/briefs/draft-cockpit/brief.md` D10 | .90 | Sessions derived from activity.jsonl; no new log schema |
| 7 | `.owlbear/research/926-list-sessions-green.md` F1 | .85 | Identified the 4-field gap; confirmed fields are derivable |

## 3. Analysis

### 3.1 Field Derivation from JSONL Events

| New Field | Source Event | Source Attribute | Edge Cases |
|-----------|-------------|-----------------|------------|
| `agent: str` | `claim` | `detail` (= agent name) | Superseded claims: agent from original claim |
| `started_at: str` | `claim` | `timestamp` | Already tracked as `open_claim_ts` |
| `duration: float \| None` | close − claim | `timestamp` delta in seconds | None for running/stuck (incl. superseded claims) |
| `outcome: str \| None` | close event | `detail` or literal | None for running/stuck; see outcome table below |

### 3.2 Outcome Mapping

| Close Action | `outcome` Value | Example |
|--------------|----------------|---------|
| `end_work` (success) | Raw detail string | `"success: todo -> in-progress"` |
| `end_work` (reject) | Raw detail string | `"reject: in-progress -> todo"` |
| `end_work` (fail) | Raw detail string | `"outcome=fail"` |
| `end_work` (block) | Raw detail string | `"blocked: needs X"` |
| `release` | `"released"` | — |
| `sweep-release` | No session created | Existing behaviour unchanged |
| running/stuck | `None` | Open or superseded sessions |

### 3.3 Implementation Approach

**Dataclass change** (~4 LOC): Add 4 fields to `WorkSession`.

**State machine change** (~15 LOC in `_collect_task_sessions()`):
- Track `open_claim_agent` alongside existing `open_claim_ts`
- On close: compute `duration = (close_dt - claim_dt).total_seconds()`, set `outcome`
- On superseded claim / unclosed: `duration=None`, `outcome=None`
- Duration calc needs timezone-aware parsing (same pattern as `_state_from_age`)

**Export** (~1 LOC): Add `WorkSession` to `__init__.py` imports and `__all__`.

**Test compatibility**: All 23 existing tests access `.task_id` and `.state` via `list_sessions()` — no direct `WorkSession()` construction. Adding required fields won't break them since `_collect_task_sessions()` will populate all fields.

### 3.4 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| Existing tests break from new required fields | Low | Med | Tests never construct WorkSession directly |
| Duration float precision | Negligible | Low | `total_seconds()` is standard; no sub-second precision needed |
| Timezone-naive timestamps in duration calc | Low | Med | Apply same UTC-default pattern as `_state_from_age` |

## 4. Recommendation

Proceed with direct implementation. Confidence: **.90**.

This is a mechanical extension — all data is available in existing JSONL events, the state machine already tracks the needed timestamps, and the implementation pattern follows existing code in `_state_from_age()`. No design alternatives to evaluate; the AC prescribes exact field names, types, and derivation logic.

Challenge: skipped (trivial implementation, no design choices to challenge).

## 5. Follow-up Tasks

None needed beyond existing #953 task — the AC is complete and self-contained. The task should advance to `backlog` for decomposition into RED (tests) and GREEN (implementation) subtasks by the pipeline.
