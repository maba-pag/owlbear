---
id: 761
title: 'P1-08: Impl — Content extractor'
status: research
priority: needed
created: '2026-04-10T10:55:57.270970+00:00'
updated: '2026-04-10T10:55:57.270970+00:00'
tags:
- phase-1
- scope:browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. `serve/browser/src/owlbear_browser/extractor.py`:
- Static JS-based DOM extraction
- Delegates to cleaner for HTML→markdown
- Login redirect detection (fail-fast)
- Only static/pre-defined extraction JavaScript

All P1-07 tests pass. Depends on launcher (#758) + cleaner (#758b).

Parent: #751
