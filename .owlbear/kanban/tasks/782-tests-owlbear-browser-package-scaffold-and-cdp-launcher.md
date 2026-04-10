---
id: 782
title: Tests — owlbear_browser package scaffold and CDP launcher
status: backlog
priority: needed
created: '2026-04-10T12:30:44.020270+00:00'
updated: '2026-04-10T12:30:44.020270+00:00'
tags:
- phase-1
- scope:browser
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `import owlbear_browser` succeeds
- Tests verify CDP launcher class exists with `launch()`, `connect()`, `close()` async methods
- Tests verify Edge binary path resolution (Windows)
- Tests use mocked subprocess/CDP — no real browser launch in unit tests
- File: `tests/test_browser_cdp_775.py`

## Context
- WS-C: Browser Packages
- Scope item 1 (part 1) from #775
- See research F5: owlbear_browser has no cross-namespace deps
