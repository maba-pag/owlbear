---
id: 758
title: 'P1-04: Impl — Edge launcher + CDP connection manager'
status: research
priority: critical
created: '2026-04-10T10:55:57.179743+00:00'
updated: '2026-04-10T10:55:57.179743+00:00'
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
GREEN phase. `serve/browser/` package:
- launcher.py: find Edge binary, launch with CDP args
- cdp_manager.py: connect/disconnect lifecycle, login redirect detection
- CDP binds exclusively to 127.0.0.1

All P1-03 (#755) tests pass. Depends on CDP spike go-ahead (#753).

Parent: #751
