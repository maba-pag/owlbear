---
id: 475
title: Wire ErrorJournal into daemon and agent error paths
status: archived
priority: needed
created: 2026-03-04T07:37:53.8656234+01:00
updated: 2026-03-06T19:28:19.5391136+01:00
started: 2026-03-06T15:44:15.0955266+01:00
completed: 2026-03-06T19:28:19.5391136+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

J-1/INT-03: ErrorJournal is fully implemented but never instantiated or wired.
Zero imports outside definition file. See docs/resilience-audit.md (J-1, J-2),
docs/integration-audit.md (INT-03).

## Research Findings

### Current State

- `ErrorJournal` (`src/owlbear/memory/error_journal.py`) — fully implemented:
  `log()` (append + rotate), `query()` (filter by tool_name/error_type/last_n),
  10K-entry rotation. Extends `JsonlStore[ErrorEntry]`.
- `ErrorEntry` is a Pydantic BaseModel with: timestamp, error_type, tool_name,
  exception_message, action_taken, attempt_number, resolved, session_id.
- Tests exist: `tests/test_error_journal.py` (unit), `tests/test_error_recovery.py`
  (integration) — both import/test the class directly but nothing in production uses it.
- **Zero imports** in `bootstrap.py`, `daemon.py`, `core/agent.py`, or any toolset.

### Integration Points (3 changes needed)

**1. Instantiate in `bootstrap()` (`src/owlbear/bootstrap.py` ~L870)**

- Create `ErrorJournal(workspace=workspace)` after workspace is resolved (L858).
- Pass to a new `ErrorJournalHook` and/or store on `BootstrapResult` so daemon can use it.
- Pattern: follow `ObservabilityHook` — it takes `EventStore(path)` in `build_hooks()`,
  registers on all events. ErrorJournal hook should register only on `ON_ERROR`.

**2. Log errors from `daemon._recover_from_error()` (`src/owlbear/daemon.py` L183-245)**

- `_recover_from_error` is called from `run_daemon` on every `agent.turn()` failure.
- It classifies errors (TRANSIENT/AUTH/PERMANENT) and retries or reports.
- Add `ErrorJournal.log()` calls at each terminal path:
  - TRANSIENT retries exhausted (L221): log with `resolved=False`, `action_taken="transient_retries_exhausted"`.
  - TRANSIENT retry succeeds (L218 `return`): log with `resolved=True`, `action_taken="transient_retry"`.
  - AUTH retry succeeds (L230): log with `resolved=True`, `action_taken="auth_refresh"`.
  - AUTH retry fails (L233): log with `resolved=False`, `action_taken="auth_refresh_failed"`.
  - PERMANENT/TOOL_SEMANTIC (L239): log with `resolved=False`, `action_taken="permanent"`.
- `session_id`: use `str(agent.session.path)` (same pattern as `_record_usage` in `agent.py` L189).
- `error_type`: use `classify_error(exc).value` (already imported).
- `tool_name`: `"agent.turn"` (no specific tool context at daemon level).
- Timestamp: `datetime.now(UTC).isoformat()`.
- Option A: pass `ErrorJournal` as param to `_recover_from_error`. Cleanest — no global state.
- Option B: register an `ErrorJournalHook` on `ON_ERROR` instead. But ON_ERROR data dict
  from `agent.turn()` only has `{"error": exc, "prompt": prompt}` — no attempt/action_taken.
  **Recommend Option A** for daemon-level logging (richer context).

**3. Expose query to agents via ON_ERROR hook or toolset**

- For agent-side learning: a `query_error_journal` PydanticAI tool that calls `journal.query()`.
- Simplest: add to an existing toolset or create a small `ErrorJournalToolset`.
- **Recommend deferring tool exposure to a follow-up task** — wiring into daemon
  is the priority (this task). Agent tool exposure is a separate concern.

### Hook-Based Alternative (ON_ERROR)

The `ON_ERROR` event fires from `agent.turn()` (agent.py L144) with
`{"error": exc, "prompt": prompt}`. An `ErrorJournalHook` registered on ON_ERROR
could auto-log errors. However:

- ON_ERROR data lacks `attempt_number`, `action_taken`, `resolved`, `tool_name`.
- The daemon's `_recover_from_error` has the retry/resolution context.
- **Verdict:** Use direct `journal.log()` calls in `_recover_from_error`, not a hook.
  The hook lacks the required context for meaningful error journal entries.

### Risk: Synchronous I/O (J-2 from resilience-audit)

`ErrorJournal` uses blocking file I/O (`Path.open`). In the async daemon loop,
rotation of 10K entries could block the event loop. Mitigations:

- For MVP: acceptable — rotation happens rarely (once per 10K errors).
- For later: wrap `_maybe_rotate` in `asyncio.to_thread()` or use aiofiles.
- **Recommend: wire now, optimize later.** File-append is fast; rotation is rare.

### Signature Change for `_recover_from_error`

```
async def _recover_from_error(
    exc: Exception,
    message: str,
    *,
    agent: OwlBearAgent,
    channel: ChannelPlugin,
    settings: OwlBearSettings | None,
+   error_journal: ErrorJournal | None = None,  # NEW — optional for backward compat
) -> None:
```

And in `run_daemon`, pass `error_journal` through from a new param or
from BootstrapResult.

## Acceptance Criteria

- [ ] `ErrorJournal` instantiated in `bootstrap()` with `workspace` path
- [ ] `ErrorJournal` passed to `run_daemon` → `_recover_from_error`
- [ ] Every error path in `_recover_from_error` calls `journal.log()` with
      appropriate ts, error_type, tool_name, exc_message, action_taken,
      attempt, resolved, session_id
- [ ] Existing tests still pass (no regressions)
- [ ] New test: daemon error paths produce journal entries
- [ ] ruff clean

## Follow-up Tasks (separate from this task)

- Expose `query_error_journal` tool to agents (agent-facing learning)
- Address J-2: async file I/O for ErrorJournal rotation
- Dedup strategy for journal entries on retry (I-3 from resilience-audit)
