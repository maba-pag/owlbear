# Orchestrator Audit Log

> **Owning task:** #21 — Build audit log
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #21 asks for a lightweight audit log recording orchestrator dispatch and completion events for self-improvement analysis. v1 had `SecurityAuditLog(JsonlStore[SecurityEvent])` for security gating events (blocked commands, approvals). v2's audit log serves a different purpose: recording *what the orchestrator did* — which agents were dispatched, for which tasks, how long they took, and whether they succeeded. No gates, no blocking.

Key questions: (a) What event schema fits dispatch-level logging? (b) Should we reuse v1's `JsonlStore[T]` pattern or something simpler? (c) One file or many? (d) How does this relate to prior observability research (#141/#142)?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | v1 `SecurityAuditLog` + `JsonlStore` | `v1/src/owlbear/safety/audit_log.py`, `v1/src/owlbear/core/jsonl_store.py` | .95 |
| 2 | OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | .85 |
| 3 | AutoGen `logging.py` event classes | <https://github.com/microsoft/autogen/blob/main/python/packages/autogen-core/src/autogen_core/logging.py> | .75 |
| 4 | OwlBear observability research | `docs/research/agent-observability.md`, `docs/research/agent-analytics.md` | .90 |
| 5 | OwlBear JsonlStore research | `docs/research/jsonl-store-base-class.md` | .85 |
| 6 | Pydantic TypeAdapter docs | <https://docs.pydantic.dev/latest/concepts/type_adapter/> | .70 |

## 3. Analysis

### 3.1 v1 SecurityAuditLog vs v2 Audit Log

| Aspect | v1 SecurityAuditLog | v2 Audit Log (#21) |
|--------|--------------------|--------------------|
| Purpose | Security gating events | Self-improvement analysis |
| Event types | command_blocked, approval_*, auth_* | dispatch, completion |
| Granularity | Per-tool-call / per-gate check | Per-agent-invocation |
| Gates/blocking | Wired into safety hooks | None — read-only analytics |
| Schema fields | 8 (security-focused) | 6-8 (dispatch-focused) |
| Consumers | Security review | Retrospective/retro skill, planner |

**Verdict:** Distinct systems. No code reuse from v1 SecurityAuditLog — only the `JsonlStore` pattern is relevant.

### 3.2 Overlap with Observability Research (#141/#142)

The v1 observability research recommended an `ObservabilityHook` writing per-tool-call telemetry (seconds granularity). Task #21 operates at dispatch granularity (minutes-to-hours per event). They are complementary layers:

- **Audit log** = dispatch lifecycle (1 event per agent invocation)
- **Observability** = tool-level telemetry (many events per invocation)

Both should use the same JSONL + Pydantic pattern but are separate modules.

### 3.3 Design Options

| Criterion | A: Inline JSONL (.85) | B: JsonlStore base first (.70) | C: stdlib logging (.40) |
|-----------|----------------------|-------------------------------|------------------------|
| New deps | 0 | 0 | 0 |
| LOC | ~100 (models + class) | ~160 (base + subclass) | ~80 (handler + formatter) |
| KISS | High | Medium — premature abstraction | Medium — untyped |
| Typed schema | Pydantic frozen models | Same | LogRecord (untyped dict) |
| Query support | `load()` + filter | Inherited from base | Requires text parsing |
| YAGNI risk | Low | Medium — only 1 consumer in v2 | Low |
| Reuse path | Extract base when 2nd store appears | Ready for reuse | Different pattern |

### 3.4 Proposed Event Schema (OWASP when/where/who/what)

**DispatchEvent:**

| Field | Type | Maps to |
|-------|------|---------|
| `timestamp` | `str` (ISO-8601) | When |
| `task_id` | `int` | What (target) |
| `agent` | `str` | Who |
| `prompt_summary` | `str` | What (input, truncated) |
| `session_id` | `str` | Where (ACP session) |

**CompletionEvent:**

| Field | Type | Maps to |
|-------|------|---------|
| `timestamp` | `str` (ISO-8601) | When |
| `task_id` | `int` | What (target) |
| `agent` | `str` | Who |
| `outcome` | `str` (success/failure) | What (result) |
| `duration_ms` | `int` | How long |
| `files_changed` | `list[str]` | What changed |
| `error` | `str or None` | What went wrong |

### 3.5 File Strategy

AC says "one file per day or per session." For a single-laptop system:

| Strategy | Pros | Cons |
|----------|------|------|
| Per-session | Natural boundary, easy to correlate | Many small files |
| Per-day | Fewer files, simple date-based query | Mixed sessions in one file |
| Single file + trim | Simplest; v1 pattern (500K cap) | All-or-nothing rotation |

**Recommendation:** Per-session file in `data/audit/` (aligns with v2's `data/` directory for runtime artifacts). Filename: `{session_id}.jsonl`. Query across sessions by globbing `data/audit/*.jsonl`.

## 4. Recommendation (.85 confidence)

**Option A: Inline JSONL with Pydantic models.** ~100 LOC in `packages/orchestrator/src/owlbear/audit/`. Two frozen Pydantic models (`DispatchEvent`, `CompletionEvent`), one `AuditLog` class with `log_dispatch()`, `log_completion()`, `query()`. JSONL files per session in `data/audit/`.

Rationale: KISS — only one JSONL store exists in v2 today, so building a `JsonlStore[T]` base class is premature. When a second store appears, extract the base via refactoring. AutoGen uses untyped dicts via stdlib logging — we get better type safety with Pydantic for ~20 more LOC.

**Risks:**

| Risk | Mitigation |
|------|------------|
| Code duplication if 2nd store appears | Extract `JsonlStore[T]` base when needed (researched in `docs/research/jsonl-store-base-class.md`) |
| `data/audit/` not in `.gitignore` | Add to `.gitignore` during implementation |
| Prompt summary could leak sensitive data | Truncate to first 100 chars; exclude tool args |

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement audit log module (DispatchEvent + CompletionEvent)" --priority needed --status ideation --tags "phase-2,scope:orchestrator,type:build" --body "Create packages/orchestrator/src/owlbear/audit/ with:\n- __init__.py exporting AuditLog, DispatchEvent, CompletionEvent\n- models.py: frozen Pydantic models (DispatchEvent, CompletionEvent) per schema in docs/research/orchestrator-audit-log.md S3.4\n- log.py: AuditLog class with log_dispatch(), log_completion(), query(date_range, agent, outcome)\n- JSONL append-only, one file per session in data/audit/{session_id}.jsonl\n- TypeAdapter for serialization\n\nAC:\n- [ ] Module at packages/orchestrator/src/owlbear/audit/\n- [ ] DispatchEvent model: timestamp, task_id, agent, prompt_summary, session_id\n- [ ] CompletionEvent model: timestamp, task_id, agent, outcome, duration_ms, files_changed, error\n- [ ] AuditLog.log_dispatch() appends DispatchEvent to session JSONL\n- [ ] AuditLog.log_completion() appends CompletionEvent to session JSONL\n- [ ] AuditLog.query() filters by date range, agent, outcome across session files\n- [ ] No approval gates or blocking behavior\n- [ ] Unit tests for write, read, query\n- [ ] data/audit/ added to .gitignore\n\nSee docs/research/orchestrator-audit-log.md"

kanban\kanban-md.exe create "Wire audit log into orchestrator dispatch loop" --priority needed --status ideation --tags "phase-2,scope:orchestrator,type:build" --depends-on 21 --body "Integrate AuditLog into the orchestrator dispatch flow:\n- Create AuditLog instance at orchestrator startup\n- Call log_dispatch() before each agent invocation (after AcpClient.new_session)\n- Call log_completion() after each agent returns (capture outcome, duration, files changed)\n- Pass session_id from AcpClient to audit log\n\nAC:\n- [ ] AuditLog instantiated in orchestrator bootstrap\n- [ ] Every dispatch produces a DispatchEvent in the session JSONL\n- [ ] Every completion produces a CompletionEvent with duration and outcome\n- [ ] Integration test verifying events appear after a dispatch cycle\n\nDepends on: audit log module task + #19 (ACP client)\nSee docs/research/orchestrator-audit-log.md"
```
