# Dedicated Security Audit Log

> **Owning task:** #525 — Create dedicated security audit log
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

SEC-14 from [docs/security-audit.md](security-audit.md) identified that security events (blocked commands, approval decisions, auth failures, path traversal attempts) are mixed into standard rotating logs via Python `logging` and into `events.jsonl` via `ObservabilityHook`. The `RotatingFileHandler` in `daemon.py` rotates at 5 MB / 3 backups — security events can be silently lost. Should we create a dedicated `SecurityAuditLog`, and if so, should it reuse `JsonlStore` or use a separate mechanism?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | OWASP Logging Cheat Sheet | <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | .95 |
| 2 | Python `logging.handlers` docs | <https://docs.python.org/3/library/logging.handlers.html> | .80 |
| 3 | structlog docs | <https://www.structlog.org/en/stable/> | .60 |
| 4 | OwlBear `JsonlStore` | `src/owlbear/core/jsonl_store.py` | .95 |
| 5 | OwlBear `ErrorJournal` | `src/owlbear/memory/error_journal.py` | .95 |
| 6 | OwlBear `ObservabilityHook` + `EventStore` | `src/owlbear/core/observability.py` | .90 |

## 3. Analysis

### 3.1 Approach Comparison

| Criterion | A: JsonlStore subclass (.90) | B: logging.FileHandler (.65) | C: structlog sink (.45) |
|-----------|------------------------------|-------------------------------|--------------------------|
| KISS | High — reuses proven pattern | Medium — separate config | Low — new dependency |
| New deps | 0 | 0 | structlog (not in stack) |
| Append-only | Native (file "a" mode) | Native (FileHandler mode='a') | Via handler config |
| Typed schema | Pydantic model | LogRecord (untyped dict) | Dict (untyped) |
| No rotation | Set high cap or skip | Set maxBytes=0 | Via handler config |
| Query support | `load()` + filter methods | Requires parsing text | Requires parsing |
| Integration | Matches ErrorJournal, EventStore | Different pattern from codebase | Foreign pattern |
| Test pattern | Matches existing test suite | Requires logging capture | Requires structlog test util |
| LOC estimate | ~60 (model + class) | ~40 (handler + formatter) | ~80 (config + processor) |

### 3.2 Security Event Sources (existing code)

| Source | File | Event type | Current logging |
|--------|------|------------|-----------------|
| `CommandSafetyGuard` | `core/command_guard.py` | command_blocked | `logger.warning` only |
| `ApprovalGateToolset` | `safety/gate.py` | approval_* | POST_TOOL_USE hook → EventStore |
| `TerminalToolset` | `tools/terminal.py` | path_escape_blocked | Raises `PermissionError`, no logging |
| Copilot auth | `auth/` module | auth_success, auth_failure | `logger.info/error` only |
| `error_to_user_message` | `core/errors.py` | error_sanitized | No logging of sanitization events |

### 3.3 Proposed Event Schema (OWASP-aligned: when/where/who/what)

| Field | Type | Purpose |
|-------|------|---------|
| `timestamp` | str (ISO-8601) | When |
| `event_type` | str (enum) | What category |
| `severity` | str (low/medium/high/critical) | Risk level |
| `actor` | str | Who — agent name or "user" |
| `session_id` | str | Which session |
| `tool_name` | str or None | Where — which tool triggered it |
| `detail` | str | What — human-readable description |
| `metadata` | dict | Extra context (command, pattern, path) |

Event types: `command_blocked`, `approval_granted`, `approval_denied`, `approval_timeout`, `approval_granted_all`, `auth_success`, `auth_failure`, `path_escape_blocked`.

### 3.4 Retention Strategy

OWASP recommends security logs use separate storage with longer retention. The `ErrorJournal` rotates at 10K entries. For security audit:

- **No entry-count rotation** (or very high cap like 500K).
- **Optional date-based archival** — future enhancement, not MVP.
- File location: `{workspace}/.owlbear/security_audit.jsonl`.

## 4. Recommendation (.90 confidence)

**Option A: `SecurityAuditLog(JsonlStore[SecurityEvent])`** — subclass `JsonlStore` exactly as `ErrorJournal` does, with a Pydantic `SecurityEvent` model and no rotation (or 500K cap). Wire it into bootstrap alongside `ErrorJournal`. Emit events from each source via a `log_security_event()` convenience method.

**Risks:**

- File grows unbounded if no rotation → mitigate with 500K entry cap (~50 MB estimated).
- Adding `audit_log` param to multiple callsites → mitigate by passing through `HookRegistry` custom hook or direct injection.

**Integration approach:** Pass `SecurityAuditLog` instance through bootstrap to the components that emit security events: `CommandSafetyGuard`, `ApprovalGateToolset`, `TerminalToolset`. Each calls `audit_log.log(...)` directly. This is simpler than routing through hooks (which would require a new hook event type and coupling).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement SecurityAuditLog class (JsonlStore subclass)" --priority needed --status backlog --tags "security,observability,phase-5" --body "Create SecurityEvent Pydantic model and SecurityAuditLog(JsonlStore[SecurityEvent]) in src/owlbear/safety/audit_log.py. Fields: timestamp, event_type, severity, actor, session_id, tool_name, detail, metadata. 500K entry cap. Convenience log() method. AC: class exists, unit tests pass, schema matches docs/research/security-audit-log.md section 3.3. See docs/research/security-audit-log.md"

kanban\kanban-md.exe create "Wire SecurityAuditLog into bootstrap and security emitters" --priority needed --status backlog --tags "security,observability,phase-5" --depends-on 525 --body "Pass SecurityAuditLog through bootstrap to CommandSafetyGuard, ApprovalGateToolset, TerminalToolset. Emit events: command_blocked from guard, approval_* from gate, path_escape_blocked from terminal. AC: security events appear in .owlbear/security_audit.jsonl during integration tests. See docs/research/security-audit-log.md section 3.2."

kanban\kanban-md.exe create "Add auth events to SecurityAuditLog" --priority important --status backlog --tags "security,auth,phase-5" --depends-on 525 --body "Emit auth_success and auth_failure events from copilot auth module to SecurityAuditLog. AC: auth events in security_audit.jsonl. See docs/research/security-audit-log.md section 3.2."
```
