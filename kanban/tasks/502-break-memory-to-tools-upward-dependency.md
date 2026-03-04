---
id: 502
title: Break memory to tools upward dependency
status: ideation
priority: important
created: 2026-03-04T07:38:15.2330855+01:00
updated: 2026-03-04T07:38:15.2330855+01:00
tags:
    - audit
    - architecture
    - scope:core
class: standard
---

INT-07: memory/knowledge/refresh.py imports tools.browser.crawl_config and tools.browser.integration. Violates layering (memory depends on tools). Inject crawl function as callback parameter instead. AC: memory package has no tools imports. See docs/integration-audit.md.
