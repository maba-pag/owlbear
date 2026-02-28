---
id: 67
title: 'P6-03: Implement BrowserConfig CDP fields'
status: archived
priority: high
created: 2026-02-26T23:30:27.3028443+01:00
updated: 2026-02-27T10:00:32.8303287+01:00
started: 2026-02-26T23:43:00.4269968+01:00
completed: 2026-02-27T10:00:32.8303287+01:00
tags:
    - phase-6
    - browser
    - config
depends_on:
    - 66
class: standard
---

## Acceptance Criteria

Edit: src/owlbear/tools/browser/config.py

### New fields on BrowserConfig
- cdp_endpoint: str | None = None — CDP HTTP endpoint URL
- cdp_port: int = 9222 — Default CDP debugging port
- browser_executable: str | None = None — Override path for browser binary
- auto_launch: bool = True — Whether to auto-launch browser if CDP unavailable

### Validators
- cdp_endpoint when set: must match http://(localhost|127\.0\.0\.1) with optional port/path
- cdp_port: must be 1-65535 inclusive
- Use field_validator following existing _validate_regex_patterns / _timeout_non_negative pattern

### Invariants
- Frozen model — no changes to model_config
- All existing fields and validators unchanged
- All tests from #66 pass
- All existing tests in test_browser_config.py still pass
