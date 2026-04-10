---
id: 474
title: Fix JavaScript injection in browser title prefix
status: archived
priority: needed
created: 2026-03-04T07:37:52.7515934+01:00
updated: 2026-03-06T19:28:18.9742039+01:00
started: 2026-03-06T15:35:21.7426026+01:00
completed: 2026-03-06T19:28:18.9742039+01:00
tags:
    - audit
    - security
    - browser
class: standard
---

## SEC-06: JavaScript Injection in Browser Title Prefix

> **Security audit ref:** docs/security-audit.md SEC-06
> **OWASP:** A03:2021 Injection | **Severity:** Medium

### Vulnerability

In `src/owlbear/tools/browser/toolset.py` L109-111, `task_label` is interpolated directly into JavaScript strings via f-string and `.format()`:

1. **L110:** `page.evaluate(f"document.title = '{prefix} ' + document.title")` — single quote in prefix breaks JS syntax or allows arbitrary code execution in browser context.
2. **L111:** `page.evaluate(_TITLE_OBSERVER_JS.format(prefix=prefix))` — curly braces or quotes in prefix break the template or inject code into the MutationObserver.

**Exploit example:** If `task_label = "Task'; alert('xss');//"`, line 110 becomes:
`document.title = '[OwlBear Task'; alert('xss');//] ' + document.title`

### Fix (parameterized evaluate)

Playwright's `page.evaluate()` accepts a second argument that is safely serialized — no string interpolation needed.

**Line 110 fix:** `await self.page.evaluate("(prefix) => { document.title = prefix + ' ' + document.title }", prefix)`

**Line 111 fix:** Rewrite `_TITLE_OBSERVER_JS` as an arrow function that receives `prefix` as a parameter instead of embedding it via `.format()`. The JS template becomes:
`(prefix) => { const titleEl = document.querySelector('title'); ... const PREFIX = prefix; ... }`
Then call: `await self.page.evaluate(observer_fn, prefix)`

### Test changes needed

Existing tests in `tests/test_browser_toolset.py` (class `TestBrowserToolsetTabNaming`) inspect `page.evaluate.call_args_list[N].args[0]` to find the prefix in the JS string. After the fix, the prefix will be passed as a second positional arg (`call_args_list[N].args[1]`), so tests must be updated.

Add a new test: `test_cdp_setup_special_chars_in_task_label` — pass a `task_label` with single quotes, double quotes, backslashes, and curly braces, assert no exception and prefix passed as argument.

### Files to change

- `src/owlbear/tools/browser/toolset.py` — rewrite `_TITLE_OBSERVER_JS` + both `page.evaluate()` calls in `setup()`
- `tests/test_browser_toolset.py` — update 4 existing tests + add 1 new test for special chars

### AC

- [ ] Title set safely with parameterized `page.evaluate()` (no f-string/format interpolation of user data into JS)
- [ ] MutationObserver installed safely with parameterized `page.evaluate()`
- [ ] Test covers `task_label` containing `'`, `"`, `{}`, `\` without error
- [ ] All existing browser toolset tests pass
- [ ] ruff clean
