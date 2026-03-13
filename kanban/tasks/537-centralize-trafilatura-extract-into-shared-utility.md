---
id: 537
title: Centralize trafilatura.extract into shared utility
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:42.2569434+01:00
updated: 2026-03-07T00:32:53.9181427+01:00
started: 2026-03-07T00:29:37.9506144+01:00
tags:
    - audit
    - dry
    - scope:core
class: standard
---

DRY-09: trafilatura.extract() wrapped in web_search.py, browser/content_extractor.py, bookmark_pipeline.py with slightly different fallback logic. See docs/software-design-audit.md.

Research complete -- see docs/research/centralize-trafilatura.md. Finding: content_extractor.py already has the correct shared utility (extract_content + ExtractionResult). The other two call sites should import-and-delegate. Two follow-up implementation tasks created.

## AC

- [x] Research doc at docs/research/centralize-trafilatura.md
- [x] Identified shared utility and call sites
- [x] Follow-up implementation tasks created
