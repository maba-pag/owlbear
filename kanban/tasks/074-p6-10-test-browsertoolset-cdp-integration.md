---
id: 74
title: 'P6-10: Test BrowserToolset CDP integration'
status: archived
priority: medium
created: 2026-02-26T23:31:21.8368884+01:00
updated: 2026-02-27T10:00:36.2050071+01:00
started: 2026-02-26T23:43:03.218346+01:00
completed: 2026-02-27T10:00:36.2050071+01:00
tags:
    - phase-6
    - test
    - browser
depends_on:
    - 71
class: standard
---

## Acceptance Criteria

Test file: tests/test_browser_toolset.py (extend existing file)

### CDP-mode setup/teardown
- BrowserToolset(config=cdp_config).setup() causes BrowserManager to enter CDP mode
- teardown() disconnects (does not close user browser)

### Tool wrapper integration in CDP mode
- All 6 tool wrappers receive a page from CDP-connected browser and work correctly
- Navigate tool applies URL safety guard identically in CDP mode

### Backward compatibility
- All existing BrowserToolset tests pass with zero changes
- Default BrowserToolset() still uses launch mode
