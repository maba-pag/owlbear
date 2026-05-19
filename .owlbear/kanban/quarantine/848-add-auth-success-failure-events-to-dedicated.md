---
id: 848
title: Add auth success-failure events to dedicated security audit log
status: archived
priority: nice-to-have
created: 2026-03-18T00:04:39.805024+01:00
updated: 2026-03-26T12:41:36.2266168+01:00
tags:
    - audit
    - security
    - auth
    - observability
depends_on:
    - 525
    - 1008
class: standard
---

Follow-up from #525. Scope ONLY the interactive bearclaw auth login flow in src/bearclaw/commands/auth.py. Reuse the dedicated security audit log introduced by #525; do not add a second auth-only log.

## AC

1. After `save_token()` succeeds in `_login_async()`, append a SecurityEvent with `event_type='auth_success'`, `severity='info'`, `actor='user'`, `session_id=''`, `tool_name=None`, `detail='Copilot device-flow login succeeded'`, `metadata={}`.
2. When the login flow raises, append a SecurityEvent with `event_type='auth_failure'`, `severity='warning'`, `actor='user'`, `session_id=''`, `tool_name=None`, `detail=error_to_user_message(exc)`, `metadata={}`. The original exception propagates unchanged.
3. Neither `auth_success` nor `auth_failure` events include access_token, copilot_token, device_code, or user_code in `detail` or `metadata`.
4. Existing CLI output (`typer.echo`) and `webbrowser.open()` behavior remain unchanged.
5. `_login_async()` accepts an optional `audit_log: SecurityAuditLog | None = None` parameter, defaulting to `SecurityAuditLog(Path.cwd())` when not provided. This follows the existing `Path.cwd()` workspace-root convention used by the daemon command.
6. `bearclaw/commands/auth.py` imports `SecurityAuditLog` directly from `owlbear.safety.audit_log` (permitted: bearclaw is a top-level CLI consumer, not a lower-layer module).
7. Audit-log write failures inside `_login_async()` are best-effort: swallowed at the call boundary so they never affect login outcome or CLI output.

**Likely files:** src/bearclaw/commands/auth.py (only file changed).

[[2026-03-26]] Thu 12:41

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC | Assessment | Action |
|-----|------------|--------|
| AC1 auth_success event | Refined: pinned severity/actor/session_id/tool_name/detail/metadata | Rewrote |
| AC2 auth_failure event | Refined: pinned error_to_user_message for detail, exception propagation | Rewrote |
| AC3 no token leakage | Clear negative constraint, testable | Kept |
| AC4 CLI behavior unchanged | Clear preservation constraint | Kept |
| AC5 injection param | NEW: _login_async() takes optional audit_log for testability | Added |
| AC6 module layering | NEW: explicit layering rationale | Added |
| AC7 best-effort audit | NEW: swallow write failures at call boundary | Added |

### Architecture Notes

Single-domain task (cli). Changes ONLY in src/bearclaw/commands/auth.py.
SecurityAuditLog from owlbear.safety.audit_log is reused as-is (no changes to core domain).
bearclaw/ is a top-level CLI consumer, importing from safety/ is permitted.
Existing audit sink pattern (CommandSafetyGuard, ApprovalGateToolset, TerminalToolset) uses Callable sink injection by bootstrap. The auth CLI is standalone, not bootstrap-wired, so direct SecurityAuditLog instantiation is appropriate.
Path.cwd() for workspace follows daemon command fallback convention.
JsonlStore.append() auto-creates parent directories.

### Changes Made

- Refined AC1-AC2 with exact event field values
- Added AC5 (injection parameter), AC6 (layering rationale), AC7 (best-effort)
- Created test task #1008 (TDD RED) with depends_on 848
- Added depends_on 1008 to #848

### Dependencies

- Verified: #525 (SecurityAuditLog) at done/archived
- Verified: #847 (RED tests for #525) at archived
- Added: #1008 (test task) must complete before #848 enters in-progress
