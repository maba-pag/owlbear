---
id: 114
title: Tests for enhanced tab title prefix (task_label + MutationObserver)
status: archived
priority: high
created: 2026-02-27T03:38:15.9587595+01:00
updated: 2026-02-27T13:21:46.095033+01:00
started: 2026-02-27T12:56:44.5123112+01:00
completed: 2026-02-27T13:21:46.095033+01:00
tags:
    - phase-6
    - browser
    - test
class: standard
---

Write failing tests for the enhanced tab title prefix feature before implementation (TDD).
See docs/cdp-tab-groups-research.md for context.

Pattern: existing tests in tests/test_browser_toolset.py class TestBrowserToolsetTabNaming.

AC:
- [ ] Test: setup(task_label='Task 65') in CDP mode calls page.evaluate() with title string containing [OwlBear Task 65]
- [ ] Test: setup() (no task_label) in CDP mode calls page.evaluate() with [OwlBear] prefix (backward compat)
- [ ] Test: Launch mode setup() does NOT call page.evaluate() for title (unchanged behavior)
- [ ] Test: In CDP mode, a second page.evaluate() call installs MutationObserver JS
- [ ] Test: MutationObserver JS string contains the correct prefix for the given task_label
- [ ] Existing TestBrowserToolsetTabNaming tests updated (old exact-string assertions replaced)
- [ ] All tests written before implementation — they MUST fail until #97 is implemented
