---
id: 528
title: Consolidate triple-nested exception swallowing in agent._record_usage
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:34.6885367+01:00
updated: 2026-03-04T07:38:34.6885367+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

F-06: Three successive except Exception blocks for usage retrieval, cost calculation, premium lookup. Configuration bugs invisible. Consolidate to single try/except, log at WARNING not DEBUG. AC: single exception handler, failures visible. See docs/code-quality-audit.md.
