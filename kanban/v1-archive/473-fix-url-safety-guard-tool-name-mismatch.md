---
id: 473
title: Fix URL safety guard tool name mismatch
status: archived
priority: needed
created: 2026-03-04T07:37:52.0224627+01:00
updated: 2026-03-06T19:28:18.4852719+01:00
started: 2026-03-06T15:32:09.3340793+01:00
completed: 2026-03-06T19:28:18.4852719+01:00
tags:
    - audit
    - security
    - browser
class: standard
---

SEC-10: URLSafetyGuard hook checks tool_name=='navigate' but registered name is 'browser_navigate'. Hook path never matches -- defense-in-depth broken. Direct check_url() call in actions.py still works.

## Research Findings

### Problem (two issues)
1. **Tool name mismatch** -- safety.py L70 checks 	ool_name != 'navigate' but toolset.py L140 registers the tool as rowser_navigate. The hook __call__ path never matches.
2. **Not registered in bootstrap** -- bootstrap.py L172 registers CommandSafetyGuard but NOT URLSafetyGuard. Even with the correct name, the hook would never fire.

### Working defense
The direct call in actions.py L49 (guard.check_url(url)) works correctly -- navigation IS protected. But the hook-based defense-in-depth layer is broken.

### Files to change
- src/owlbear/tools/browser/safety.py L70: Change 'navigate' to 'browser_navigate'
- src/owlbear/bootstrap.py ~L172: Add URLSafetyGuard().register(hooks) alongside CommandSafetyGuard
- tests/test_browser_safety.py L31: Update _navigate_data helper to use 'browser_navigate'
- tests/test_browser_safety.py: Add integration test that verifies HookedToolset + URLSafetyGuard blocks a bad URL end-to-end

### AC
- [ ] safety.py hook checks tool_name == 'browser_navigate'
- [ ] URLSafetyGuard registered in bootstrap hook setup
- [ ] Existing tests updated with correct tool name
- [ ] New integration test: HookedToolset + URLSafetyGuard blocks denied URL
- [ ] Direct check_url path in actions.py still works (no regression)
