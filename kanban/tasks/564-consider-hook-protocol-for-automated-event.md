---
id: 564
title: Consider Hook protocol for automated event registration
status: backlog
priority: someday
created: 2026-03-04T07:39:07.0113635+01:00
updated: 2026-03-07T04:29:50.1410163+01:00
started: 2026-03-07T04:29:50.1410163+01:00
tags:
    - audit
    - dry
    - hooks
class: standard
---

DECISION: Keep explicit hook registration. See docs/hook-protocol-research.md. The 8 hook classes (not 9 -- escalation.py deleted by #484) use 3 different registration patterns. Only 6/8 are uniform. Net LOC savings would be negative. KISS/YAGNI/Django all argue against auto-registration magic. AC satisfied: decision documented.
