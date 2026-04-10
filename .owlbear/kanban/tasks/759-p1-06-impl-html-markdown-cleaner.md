---
id: 759
title: 'P1-06: Impl — HTML→markdown cleaner'
status: research
priority: needed
created: '2026-04-10T10:55:57.210371+00:00'
updated: '2026-04-10T10:55:57.210371+00:00'
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
GREEN phase. `serve/browser/src/owlbear_browser/cleaner.py`:
- HTML→markdown with boilerplate stripping
- SharePoint-specific normalization
- Idempotent output for stable hashing

All P1-05 (#756) tests pass.

Parent: #751
