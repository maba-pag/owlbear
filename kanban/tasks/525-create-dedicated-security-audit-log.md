---
id: 525
title: Create dedicated security audit log
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:32.6960467+01:00
updated: 2026-03-07T00:15:49.8288514+01:00
started: 2026-03-07T00:06:04.8208398+01:00
tags:
    - audit
    - security
    - observability
class: standard
---

SEC-14: Security events (blocked commands, approvals, auth failures) mixed into standard rotating logs. Security events can be lost in rotation.

Research complete. See docs/security-audit-log-research.md.

**Recommendation (.90):** Create SecurityAuditLog(JsonlStore[SecurityEvent]) in src/owlbear/safety/audit_log.py. Pydantic model with OWASP-aligned fields (timestamp, event_type, severity, actor, session_id, tool_name, detail, metadata). 500K entry cap. Wire into CommandSafetyGuard, ApprovalGateToolset, TerminalToolset.

**Research checklist:**
1. Theoretical validity - Sound; append-only JSONL for security events is industry standard (OWASP A09)
2. Prior art - OWASP Logging Cheat Sheet + Python logging.handlers + existing JsonlStore pattern
3. Technical feasibility - Confirmed; reuses JsonlStore base class, zero new deps
4. Architecture fit - Sits in safety/ alongside gate.py and policy.py; injected through bootstrap
5. Implementation approach - Subclass JsonlStore, Pydantic SecurityEvent model, direct injection

AC: security events in dedicated file with longer retention.
