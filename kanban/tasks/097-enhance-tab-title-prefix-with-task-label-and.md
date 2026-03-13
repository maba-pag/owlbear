---
id: 97
title: Enhance tab title prefix with task label and MutationObserver
status: archived
priority: high
created: 2026-02-27T03:15:01.2541819+01:00
updated: 2026-02-27T13:21:34.1800871+01:00
started: 2026-02-27T03:32:44.0527301+01:00
completed: 2026-02-27T13:21:34.1800871+01:00
tags:
    - phase-6
    - browser
depends_on:
    - 114
class: standard
---

Enhance tab title prefix with task label and MutationObserver in CDP mode.
See docs/research/cdp-tab-groups.md for details.

## Scope
- CDP mode only (launch mode unchanged)
- Title prefix + MutationObserver JS, both injected via page.evaluate() in BrowserToolset.setup()
- BrowserManager is NOT modified (task_label is a BrowserToolset concern)

## Architecture notes
- Pattern: existing code in src/owlbear/tools/browser/toolset.py line ~87
- Current: page.evaluate('document.title = [OwlBear] + document.title')
- Enhanced: two page.evaluate() calls — one for title, one for MutationObserver
- Follow existing test pattern in tests/test_browser_toolset.py TestBrowserToolsetTabNaming

AC:
- [ ] BrowserToolset.setup() signature: async def setup(self, *, task_label: str | None = None) -> None
- [ ] CDP mode with task_label: title set to [OwlBear {task_label}] {original_title}
- [ ] CDP mode without task_label: title set to [OwlBear] {original_title} (backward compat)
- [ ] MutationObserver JS injected via second page.evaluate() call in CDP mode
- [ ] Observer watches document.querySelector('title') for childList changes and re-applies prefix
- [ ] Observer handles missing title element gracefully (no crash)
- [ ] MutationObserver JS is a module-level constant _TITLE_OBSERVER_JS in toolset.py (prefix interpolated at call time)
- [ ] Launch mode: setup() unchanged (no page.evaluate calls, no title prefix, no observer)
- [ ] CDP warning log preserved
- [ ] All tests from #114 pass green
- [ ] uv run ruff check clean
