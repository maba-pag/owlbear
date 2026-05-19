---
id: 1008
title: 'Test: auth success-failure audit events (RED)'
status: archived
priority: nice-to-have
created: 2026-03-26 12:40:41.074567+01:00
updated: 2026-03-26 13:37:09.592296+01:00
tags:
- audit
- security
- auth
- test
- type:test
- cli
class: standard
archival_reason: completed
archival_refs: []
---

TDD RED phase for #848 (auth audit events).

## AC

1. Add tests in tests/test_auth_audit_events.py that exercise the auth_success and auth_failure SecurityEvent contracts from #848 AC1-AC2: correct event_type, severity, actor, session_id, tool_name, detail, and metadata values.
2. Tests verify AC3: neither event includes access_token, copilot_token, device_code, or user_code in detail or metadata.
3. Tests verify AC5: _login_async() accepts audit_log parameter for test injection.
4. Tests verify AC7: audit-log write failures do not affect login outcome.
5. Tests verify AC4: existing CLI output and browser behavior preserved (mocked).
6. All new tests fail on current HEAD (RED phase).

**Likely files:** tests/test_auth_audit_events.py

[[2026-03-26]] Thu 13:05

## Research

**Checklist:** all 7 items validated

1. **Theoretical validity:** Sound TDD RED phase; SecurityEvent + SecurityAuditLog infra exists from #525/#847
2. **Prior art:** test_security_audit_log.py (mock sink injection, field verification, best-effort), test_cli_auth.py (async auth mock patterns)
3. **Technical feasibility:** All deps present; _login_async() lacks audit_log param so tests fail RED correctly
4. **Architecture fit:** Single file tests/test_auth_audit_events.py; direct SecurityAuditLog import permitted (AC6)
5. **Implementation approach:** Combine mock patterns from test_cli_auth.py + test_security_audit_log.py
6. **Testing strategy:** N/A (this IS the test task)
7. **Findings:** Well-scoped, no gaps found. No new follow-up tasks needed; #848 covers implementation.

**RED failure modes:** TypeError on audit_log kwarg (AC1-AC5), no events emitted (AC1-AC3), no error_to_user_message call (AC2)

[[2026-03-26]] Thu 13:16

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC | Assessment | Action |
|-----|------------|--------|
| AC1 auth_success/auth_failure event contracts | Precise: exact field values pinned from #848 AC1-AC2 | Kept |
| AC2 no token leakage | Clear negative constraint, maps to #848 AC3 | Kept |
| AC3 audit_log injection param | Verifiable: current _login_async() lacks param, tests fail RED | Kept |
| AC4 best-effort write failures | Maps to #848 AC7, testable via mock injection | Kept |
| AC5 CLI behavior preserved | Maps to #848 AC4, testable via mocked output | Kept |
| AC6 all tests fail RED | Standard TDD constraint | Kept |

### Architecture Notes

Single-domain task (test). Target file: tests/test_auth_audit_events.py.
Follows existing patterns from test_security_audit_log.py (SecurityEvent field verification, mock sink injection) and test_cli_auth.py (async auth mock patterns).
SecurityAuditLog and SecurityEvent imports from owlbear.safety.audit_log are established patterns.
error_to_user_message import from owlbear.core.errors is available.
RED failure modes correctly identified: TypeError on missing audit_log kwarg, no events emitted, missing error_to_user_message call.

### Dependencies

- Verified: #525 (SecurityAuditLog) at archived
- Verified: #848 depends_on includes #1008 (TDD ordering enforced)
