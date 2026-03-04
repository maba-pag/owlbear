---
id: 475
title: Wire ErrorJournal into daemon and agent error paths
status: ideation
priority: needed
created: 2026-03-04T07:37:53.8656234+01:00
updated: 2026-03-04T07:37:53.8656234+01:00
tags:
    - audit
    - resilience
    - scope:core
class: standard
---

J-1/INT-03: ErrorJournal is fully implemented but never instantiated or wired. Zero imports outside definition file. Create in bootstrap, log from daemon._recover_from_error, expose query to agents. AC: ErrorJournal active in production, errors recorded. See docs/resilience-audit.md, docs/integration-audit.md.
