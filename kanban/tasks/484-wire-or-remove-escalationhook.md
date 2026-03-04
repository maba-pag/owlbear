---
id: 484
title: Wire or remove EscalationHook
status: ideation
priority: important
created: 2026-03-04T07:38:01.1970371+01:00
updated: 2026-03-04T07:38:01.1970371+01:00
tags:
    - audit
    - yagni
    - hooks
    - scope:core
class: standard
---

YAGNI-02/INT-03: EscalationHook is fully implemented and tested but never imported or registered in bootstrap.py. Orphan code. Either wire into bootstrap for ON_ERROR events or delete with tests. AC: no dead production code for this feature. See docs/software-design-audit.md, docs/integration-audit.md.
