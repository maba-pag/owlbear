---
id: 756
title: 'P1-05: Tests — HTML→markdown cleaner'
status: research
priority: needed
created: '2026-04-10T10:55:24.919476+00:00'
updated: '2026-04-10T10:55:24.919476+00:00'
tags:
- phase-1
- type:test
- scope:browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for HTML→markdown cleaner:
1. HTML→markdown conversion with nav/header/footer/sidebar stripping
2. SharePoint-specific dynamic boilerplate removal
3. Content normalization (whitespace, encoding)
4. Idempotent output (same input → same output for hashing)

All tests fail (RED).

Parent: #751
