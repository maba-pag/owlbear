---
id: 494
title: Expand command guard blocklist and document limitations
status: backlog
priority: important
created: 2026-03-04T07:38:09.2339754+01:00
updated: 2026-03-06T23:29:18.4565431+01:00
started: 2026-03-06T23:23:22.4453535+01:00
tags:
    - audit
    - security
    - scope:core
class: standard
---

SEC-04: DEFAULT_BLOCKED_COMMANDS regex patterns are fundamentally bypassable (rm -r -f /, git push -f, python -m pip). Document that blocklist is defense-in-depth only, not a security boundary. Expand patterns to cover common variations. AC: documented as non-boundary, expanded patterns. See docs/security-audit.md.
