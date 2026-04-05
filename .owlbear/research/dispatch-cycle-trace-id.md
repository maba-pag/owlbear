# Dispatch-Cycle Trace ID for Orchestrator Protocol

> **Owning task:** #434 — Add dispatch-cycle trace ID to orchestrator protocol
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

OwlBear's orchestrator dispatches agents in waves across multiple cycles. Currently, `DispatchEvent` and `CompletionEvent` audit models carry a `session_id` (one per ACP session), but nothing correlates events that belong to the same orchestration cycle. The `LoopState.cycle` counter is a local integer — not globally unique across sessions. This makes it hard to debug "what happened in cycle 3 of yesterday's run?"

deer-flow's trace ID propagation pattern (§3C of `docs/research/deer-flow-adoptable-patterns.md`) identified this gap. This research evaluates implementation approaches, scoped to OwlBear's file-based, on-demand architecture.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| W3C Trace Context (Rec 2021) | w3.org/TR/trace-context | Standard for trace-id propagation: 16-byte UUID, parent-id per span (.85) |
| OpenTelemetry Traces | opentelemetry.io/docs/concepts/signals/traces | trace_id + span_id with context propagation for parent-child correlation (.80) |
| LangSmith Observability | docs.langchain.com/langsmith/observability-concepts | Trace = collection of runs bound by trace_id; threads link traces by session_id (.80) |
| deer-flow subagent system | github.com/bytedance/deer-flow | UUID propagated parent-to-subagent for debugging (.70, already analyzed #386) |
| OwlBear orchestrator source | packages/orchestrator/src/ | Current architecture baseline: loop.py, audit/models.py (.95) |

## 3. Analysis

### Current integration points

- `run_loop()` increments `state.cycle` (int) — where a UUID would be generated
- `dispatch_entry()` creates `DispatchEvent(session_id=...)` — no cycle reference
- `CompletionEvent` has `session_id` — no cycle reference
- `session_name` format: `owlbear-{agent}-{task_id}` — no cycle reference
- Channel A signal: `{VERDICT} #{id} -> {status} | {evidence}` — no trace ID
- Orchestrator **never reads Channel A** (by design, per agent-common.instructions.md)

### Approach comparison

| Criterion | A: Audit-only cycle_id | B: Full protocol (AC as-is) | C: OTel-compatible |
|-----------|----------------------|---------------------------|-------------------|
| Scope | cycle_id in audit events + session_name | A + Channel A/B format changes | A + B + hierarchical spans |
| Code diff | ~40 LOC (models + loop) | ~100 LOC + all agent .md files | ~200 LOC + tracing module |
| KISS | High | Medium | Low |
| Debug value | High — query audit by cycle | Medium — agents write IDs but orchestrator never reads them | High — but overkill |
| Protocol disruption | None | All 10+ agent instruction files | All agents + new dependency |
| YAGNI risk | Low | Medium | High |

### Key insight: Channel A is write-only

The orchestrator explicitly never reads Channel A signals (agent-common.instructions.md §Reading rules). Adding a cycle_id to Channel A is write-only overhead — no consumer exists. Channel B already includes timestamped agent sections; a cycle_id there provides marginal value over what structured audit logs offer.

Both W3C Trace Context and LangSmith solve this at the **infrastructure layer** (tracing headers, SDK-injected trace_ids), not by asking participants to manually propagate IDs in their output format. OwlBear's audit log is the infrastructure layer.

## 4. Recommendation (.80 confidence)

**Option A: Audit-centric trace ID.** Generate a UUID per cycle in `run_loop()`, thread it through `dispatch_wave()` and `dispatch_entry()`, and include it in `DispatchEvent`/`CompletionEvent`. Also embed it in the ACP `session_name` for easy grep.

Refine the original AC:
- AC-1 (cycle ID per wave): Yes — `uuid4().hex` per cycle in `run_loop()`, passed to all dispatches in that cycle.
- AC-2 (Channel A/B): Downscope — embed in `session_name` (infra-level). Don't mandate Channel A/B format changes. Agents can optionally reference the ID from their dispatch prompt.
- AC-3 (audit log correlation): Yes — add `cycle_id: str` field to both event models. Add optional `cycle_id` filter to `AuditLog.query()`.

**Risk:** Minimal. Pure additive change — no existing behavior altered. ~40 LOC.

**Alternative (bp):** Full protocol integration (Option B) if debugging needs evolve to require agent-written correlation. Can be added later without breaking Option A.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement audit-centric dispatch-cycle trace ID" --priority nice-to-have --status ideation --tags "scope:agents,phase-2,type:build" --body "## Context\nAdd a cycle_id (uuid4 hex) to the orchestrator dispatch loop and audit models for debugging correlation. Audit-only approach per docs/research/dispatch-cycle-trace-id.md.\n\n## Acceptance Criteria\n- [ ] DispatchEvent and CompletionEvent models include cycle_id: str field\n- [ ] run_loop() generates uuid4().hex per cycle, passes to dispatch_wave() and dispatch_entry()\n- [ ] ACP session_name format updated to owlbear-{cycle_id[:8]}-{agent}-{task_id}\n- [ ] AuditLog.query() accepts optional cycle_id filter\n- [ ] Existing tests updated for new field; new tests verify cycle_id propagation"
```
