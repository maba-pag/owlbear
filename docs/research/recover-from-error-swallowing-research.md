# Fix `_recover_from_error` Swallowing PERMANENT Errors

> **Owning task:** #471 — Fix _recover_from_error swallowing PERMANENT errors
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

`daemon.py:_recover_from_error` handles errors from `agent.turn()` across three
categories (TRANSIENT, AUTH, PERMANENT/TOOL_SEMANTIC). In every path, the
final step calls `await channel.send(f"Error: {exc}")` **unguarded**. If
`channel.send` fails (e.g. Slack WebSocket disconnected), the error is silently
lost — no journal entry, no fallback log, no re-raise. The resilience audit
(P-2, CF-2) flagged this as HIGH severity.

**Question:** How should errors always be recorded even when channel delivery
fails? Should ErrorJournal be wired in here?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python Logging Cookbook — Multiple handlers/destinations | <https://docs.python.org/3/howto/logging-cookbook.html> | .85 — Shows multi-handler pattern: if one sink fails, others still capture. `logger.exception()` always writes to RotatingFileHandler configured in `setup_logging`. |
| 2 | 12-Factor App — XI. Logs | <https://12factor.net/logs> | .70 — "Treat logs as event streams." Errors are events that must never vanish. Local file logging is the backstop. |
| 3 | OwlBear resilience-audit.md (P-2, CF-2, J-1) | docs/resilience-audit.md | 1.0 — Direct audit finding. Also notes J-1: ErrorJournal exists but is never wired anywhere. |
| 4 | OwlBear `memory/error_journal.py` | src/owlbear/memory/error_journal.py | 1.0 — Existing ErrorJournal class: sync JSONL append + query + rotation. Ready to use. |

## 3. Analysis

### 3.1 Where exactly does `channel.send` go unguarded?

Three locations in `_recover_from_error` (daemon.py L183–236):

| Path | Line(s) | Unguarded `channel.send` |
|------|---------|--------------------------|
| TRANSIENT (retries exhausted) | ~L225 | `await channel.send(f"Error: {last_exc}")` |
| AUTH (refresh failed) | ~L231 | `await channel.send(f"Error: {retry_exc}")` |
| PERMANENT / TOOL_SEMANTIC | ~L235 | `await channel.send(f"Error: {exc}")` |

All three share the same bug: if `channel.send` raises, the error disappears.

### 3.2 Fix options

| Criterion | A: Wrap channel.send only | B: Wrap + ErrorJournal | C: ErrorJournal-first |
|-----------|---------------------------|------------------------|----------------------|
| Complexity | Low (~10 LOC) | Medium (~25 LOC) | Medium (~25 LOC) |
| Error guaranteed logged? | Yes (logger.exception) | Yes (journal + logger) | Yes (journal first) |
| Agent learning from past errors? | No | Yes | Yes |
| Wires dead code (J-1)? | No | Yes | Yes |
| KISS | High | Medium | Medium |
| YAGNI risk | None | Low — journal already built | Low |

### 3.3 ErrorJournal feasibility

- `ErrorJournal.log()` needs: `ts`, `error_type`, `tool_name`, `exc_message`,
  `action_taken`, `attempt`, `resolved`, `session_id`.
- `_recover_from_error` has access to `exc`, `message`, `agent`, `channel`,
  `settings`. It does NOT have `workspace` path or `session_id`.
- `run_daemon` receives `config_dir` but not `workspace`. Wiring requires
  either: (a) adding `workspace` param to `run_daemon` → `_recover_from_error`,
  or (b) deriving workspace from `config_dir` parent (brittle), or (c) passing
  an `ErrorJournal` instance.
- J-2 notes ErrorJournal is sync I/O — for single appends this is sub-ms,
  acceptable. Rotation of 10K entries could block, but that's a separate concern.

### 3.4 ErrorJournal wiring scope

Wiring ErrorJournal into `_recover_from_error` partially addresses J-1 but is
**not** the full J-1 fix (which requires wiring into bootstrap, agents, hooks).
Recommend: fix the channel-swallowing bug now (Option A), create a separate task
for full ErrorJournal wiring (J-1). This keeps #471 surgical.

## 4. Recommendation (.85 confidence)

**Option A: Wrap `channel.send` in try/except with `logger.exception` fallback.**

Rationale:

- KISS: smallest diff, directly fixes AC. `logger.exception()` writes to the
  RotatingFileHandler configured in `setup_logging()`, so the error is persisted
  to disk even when the channel is dead.
- Avoids scope creep: ErrorJournal wiring requires plumbing workspace/session_id
  through `run_daemon` and `_recover_from_error`, which is a larger change that
  should be its own task.
- AC is met: "errors always recorded (to journal **or fallback log**), channel
  send failure handled gracefully."

Implementation pattern for each of the 3 paths:

```python
# Before (all 3 paths):
await channel.send(f"Error: {exc}")

# After:
try:
    await channel.send(f"Error: {exc}")
except Exception:  # noqa: BLE001
    logger.exception("Channel delivery failed for error: %s", exc)
```

If the builder wants to also add ErrorJournal in the same PR, that's fine but
not required by this AC.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Wrap channel.send in _recover_from_error with try/except fallback logging" --status todo --priority needed --tags "resilience,scope:core,phase-7" --body "Fix P-2 from resilience-audit.md. Wrap all 3 channel.send calls in _recover_from_error (TRANSIENT exhausted, AUTH failed, PERMANENT) in try/except. On failure: logger.exception() so the error is always persisted to the RotatingFileHandler. AC: (1) channel.send failure does not lose the original error, (2) fallback log entry contains the original exception, (3) daemon loop continues. See docs/recover-from-error-swallowing-research.md."

kanban\kanban-md.exe create "Wire ErrorJournal into daemon and bootstrap" --status ideation --priority important --tags "resilience,scope:core" --body "Address J-1 from resilience-audit.md. ErrorJournal class exists but is never instantiated. Wire it into bootstrap (create instance, pass to daemon) and have daemon record errors to journal. Requires adding workspace/session_id params. Separate from #471. See docs/resilience-audit.md J-1, J-2."
```

## 6. Testing Strategy

- Mock `channel.send` to raise `RuntimeError`.
- Call `_recover_from_error` with a PERMANENT-category exception.
- Assert: `logger.exception` was called with the original error.
- Assert: no unhandled exception escapes `_recover_from_error`.
- Repeat for TRANSIENT (retries exhausted) and AUTH (refresh failed) paths.
