# Analysis Module Implementation Readiness

> **Owning task:** #179 — Implement analysis module with pattern detectors
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #179 (spawned from #31 research) implements the analysis module with four pattern detectors. This research validates implementation readiness: dependency status, API compatibility, namespace placement, detector edge cases, and testing strategy.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OwlBear audit log module | `packages/orchestrator/src/owlbear/audit/` | .95 |
| 2 | Parent research (#31) | `docs/research/self-improvement-analysis-pipeline.md` | .95 |
| 3 | AutoGen telemetry + structured logging | `microsoft.github.io/autogen/stable/.../telemetry.html` | .70 |
| 4 | LangSmith evaluation concepts | `docs.langchain.com/langsmith/evaluation` | .65 |
| 5 | Orchestrator pyproject.toml | `packages/orchestrator/pyproject.toml` | .90 |
| 6 | OwlBear audit log tests (#185) | `tests/test_audit_log.py` | .85 |

## 3. Analysis

### 3.1 Dependency #21 — Ready

Task #21 (Build audit log) is archived. The `owlbear.audit` module provides:

| API | Signature | Status |
|-----|-----------|--------|
| `DispatchEvent` | `frozen BaseModel`: timestamp, task_id, agent, prompt_summary, session_id | Implemented |
| `CompletionEvent` | `frozen BaseModel`: timestamp, task_id, agent, outcome, duration_ms, files_changed, error | Implemented |
| `AuditLog.query()` | `(date_range?, agent?, outcome?) -> list[Event]` | Implemented |
| `audit_adapter` | `TypeAdapter[AuditEvent]` — discriminated union on `type` | Implemented |

All 36 tests pass. No blockers.

### 3.2 Namespace Placement

The orchestrator wheel packages two namespaces (confirmed in `pyproject.toml`):

| Namespace | Contents | Purpose |
|-----------|----------|---------|
| `owlbear` | `audit/`, `voice/`, `planner/` | Domain models and utilities |
| `owlbear_orchestrator` | `acp_client`, `process_supervisor`, `error_journal` | Operational process code |

**AC specifies `owlbear_orchestrator/analysis/`** — correct. Analysis is an operational concern (analyzing dispatch process data), not a domain model. The cross-import `from owlbear.audit import ...` works because both namespaces ship in the same wheel.

### 3.3 Stale Dispatch Detection — Edge Cases

The stale detector must correlate `DispatchEvent` → `CompletionEvent`. Matching key: `(task_id, agent, session_id)`. Edge cases:

| Scenario | Expected behavior |
|----------|------------------|
| Dispatch + completion within 1h | Not stale |
| Dispatch with no completion, age > 1h | Stale proposal generated |
| Dispatch with no completion, age < 1h | Not stale (still in flight) |
| Multiple dispatches for same task (redispatch) | Each dispatch matched independently |
| Completion without dispatch (orphan) | Ignored — no proposal |

Reference timestamp: `analyze()` should accept an optional `now` parameter (default `datetime.now(UTC)`) for deterministic testing. The `window` parameter filters events by age; stale detection uses event timestamps vs `now`.

### 3.4 Testing Strategy

Synthetic JSONL fixtures per detector. All fixtures are in-memory (no file I/O in unit tests except `tmp_path` for integration). Recommended fixture shapes:

| Detector | Fixture | Expected proposals |
|----------|---------|-------------------|
| high_error_rate | 5 completions for agent A: 3 fail, 2 succeed (60%) | 1 proposal |
| high_error_rate | 2 completions for agent B: 2 fail (100% but < 3 min) | 0 proposals |
| slow_agent | Agent A avg 10s, global avg 3s, 3+ dispatches | 1 proposal |
| slow_agent | Agent B avg 5s, global avg 3s (< 2x) | 0 proposals |
| repeated_failure | 2 failures on task 42 | 1 proposal |
| repeated_failure | 1 failure on task 42, 1 on task 43 | 0 proposals |
| stale_dispatch | Dispatch 2h ago, no completion | 1 proposal |
| stale_dispatch | Dispatch 30min ago, no completion | 0 proposals |
| empty log | No events | 0 proposals |

### 3.5 AC Refinement Suggestions

The AC is well-specified. Two implementation notes for the builder:

1. **`now` parameter** — `analyze()` should accept `now: datetime | None = None` for deterministic stale detection in tests. Default to `datetime.now(UTC)`.
2. **Threshold constants** — Define as module-level constants in `detectors.py` for easy tuning: `ERROR_RATE_THRESHOLD = 0.40`, `MIN_DISPATCHES = 3`, `SLOW_FACTOR = 2.0`, `STALE_THRESHOLD = timedelta(hours=1)`.

## 4. Recommendation (.90 confidence)

**Proceed to implementation.** All dependencies satisfied, AC is complete, namespace placement is correct, edge cases identified. The parent research (#31) validated the design; this pass confirms readiness.

No blockers. No decision requests needed.

## 5. Follow-up Tasks

No new tasks needed — #179 is already the follow-up from #31 with complete AC. The AC refinement suggestions (§3.5) are implementation guidance for the builder, not scope changes.
