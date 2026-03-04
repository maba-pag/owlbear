---
id: 500
title: Add import guard to bookmark_pipeline trafilatura
status: ideation
priority: important
created: 2026-03-04T07:38:13.5690379+01:00
updated: 2026-03-04T07:38:13.5690379+01:00
tags:
    - audit
    - config
    - knowledge
class: standard
---

F-07: bookmark_pipeline.py _default_web_read() imports trafilatura without guard. Raises raw ModuleNotFoundError without crawl/search extras. AC: ImportError handled with install instructions. See docs/config-dependency-audit.md.
