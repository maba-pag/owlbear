---
id: 71
title: 'P6-07: Implement BrowserManager CDP connect + cleanup'
status: done
priority: high
created: 2026-02-26T23:31:00.2985806+01:00
updated: 2026-02-27T00:07:24.4053103+01:00
started: 2026-02-26T23:43:02.0975448+01:00
completed: 2026-02-27T00:07:24.4053103+01:00
tags:
    - phase-6
    - browser
depends_on:
    - 70
class: standard
---

## Acceptance Criteria

Edit: src/owlbear/tools/browser/manager.py

### Dual-mode __aenter__
- If config.cdp_endpoint is set: call pw.chromium.connect_over_cdp(config.cdp_endpoint)
- Reuse browser.contexts[0] for context
- Open new page in reused context
- Else: existing launch() path unchanged

### State tracking
- Add _is_cdp: bool flag (True when CDP mode, False when launch mode)
- Track pages created by OwlBear in _owned_pages: list[Page]

### CDP-aware __aexit__
- CDP mode: close only pages in _owned_pages, then browser.disconnect() (never browser.close())
- Launch mode: existing cleanup unchanged (page -> context -> browser -> pw.stop)
- Playwright stop() called in both modes

### Invariants
- All tests from #70 pass
- All existing launch-mode tests still pass unchanged
- page property works identically in both modes
