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

DRY-09: trafilatura.extract() wrapped in web_search.py, browser/content_extractor.py, bookmark_pipeline.py with slightly different fallback logic. Centralize in extract_text_content(html) utility. AC: single extraction utility, all callers use it. See docs/software-design-audit.md.

Research complete  see docs/centralize-trafilatura-research.md. Finding: content_extractor.py already has the correct shared utility (extract_content + ExtractionResult). The other two call sites should import-and-delegate. Two follow-up implementation tasks created.
