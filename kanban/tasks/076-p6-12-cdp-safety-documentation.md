---
id: 76
title: 'P6-12: CDP safety + documentation'
status: done
priority: medium
created: 2026-02-26T23:31:37.3851097+01:00
updated: 2026-02-27T00:19:11.6853102+01:00
started: 2026-02-26T23:43:04.0984721+01:00
completed: 2026-02-27T00:19:11.6853102+01:00
tags:
    - phase-6
    - browser
    - docs
depends_on:
    - 75
class: standard
---

## Acceptance Criteria

### Safety validation
- Verify cdp_endpoint validator rejects non-localhost URLs (covered by #67)
- Add CDP-awareness note to URLSafetyGuard docstring
- Any new safety code must include tests in existing test files

### Documentation updates
- copilot-instructions.md: add CDP browser mode to tech stack or browser notes
- README.md: add bearclaw browser start/stop/status to CLI section
- Update browser module docstrings (manager.py, toolset.py) to mention CDP connect mode

### Verification
- Full test suite green
- Lint clean: ruff check
- No new dependencies required beyond existing playwright
