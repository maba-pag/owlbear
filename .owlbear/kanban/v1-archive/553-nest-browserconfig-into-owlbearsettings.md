---
id: 553
title: Nest BrowserConfig into OwlBearSettings
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:55.9671683+01:00
updated: 2026-03-22T19:17:43.4894703+01:00
started: 2026-03-07T00:55:28.949134+01:00
completed: 2026-03-22T19:17:43.4894703+01:00
tags:
    - audit
    - config
    - browser
blocked: true
block_reason: 'Stale duplicate of archived #843; current AC/research no longer match the codebase (leaf-node BrowserConfig move, bootstrap package split).'
class: standard
---

INT-18: BrowserConfig not configurable via OWLBEAR_ env vars. See docs/research/browser-config-nesting.md for full analysis.

Approach: Nest BrowserConfig into OwlBearSettings using env_nested_delimiter='__' and nested_model_default_partial_update=True.

AC:
1. OwlBearSettings has browser: BrowserConfig field with env_nested_delimiter='__' and nested_model_default_partial_update=True in model_config
2. OWLBEAR_BROWSER__HEADLESS=true correctly sets settings.browser.headless (and all other BrowserConfig fields)
3. bootstrap.py uses settings.browser instead of BrowserConfig() in all 3 call sites (_build_hooks_and_reporters, _build_web_search_toolset, build_toolsets)
4. Existing BrowserConfig tests still pass (BrowserConfig stays a frozen BaseModel)
5. New test verifies env var override for at least one nested field

[[2026-03-21]] Sat 02:53
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. OwlBearSettings has browser: BrowserConfig field with env_nested_delimiter='__' and nested_model_default_partial_update=True in model_config | Already implemented in src/owlbear/config.py; not new builder work | Mark task stale |
| 2. OWLBEAR_BROWSER__HEADLESS=true correctly sets settings.browser.headless (and all other BrowserConfig fields) | Headless/CDP behavior is already covered in tests/test_config.py, but 'and all other BrowserConfig fields' is too broad to verify mechanically | Do not dispatch from current AC |
| 3. bootstrap.py uses settings.browser instead of BrowserConfig() in all 3 call sites (_build_hooks_and_reporters, _build_web_search_toolset, build_toolsets) | Outdated: src/owlbear/bootstrap.py no longer exists; bootstrap is now split across hooks.py, knowledge.py, toolsets.py, and __init__.py | Return task to ideation; research/AC need refresh |
| 4. Existing BrowserConfig tests still pass (BrowserConfig stays a frozen BaseModel) | Partly satisfied, partly vague. Current architecture keeps BrowserConfig in owlbear.config and re-exports it from owlbear.tools.browser.config to preserve the config leaf-node rule | Do not dispatch from current AC |
| 5. New test verifies env var override for at least one nested field | Already implemented by archived task #843 and current tests in tests/test_config.py | Mark task redundant |

### Architecture Notes
- Current code already satisfies the substantive goal:
  - src/owlbear/config.py contains env_nested_delimiter='__', nested_model_default_partial_update=True, and a browser field.
  - tests/test_config.py verifies OWLBEAR_BROWSER__HEADLESS and OWLBEAR_BROWSER__CDP_PORT plus partial-update regression coverage.
  - tests/test_browser_config_nesting.py adds architectural regression guards for leaf-node placement and settings.browser bootstrap wiring.
- The original research recommendation is now stale in one important way: it says config.py should import BrowserConfig from owlbear.tools.browser.config. That would violate the leaf-node rule in architecture-standards. The repo solved this correctly by defining BrowserConfig in owlbear.config and re-exporting it from owlbear.tools.browser.config.
- AC3 is also stale: src/owlbear/bootstrap.py no longer exists. The relevant wiring now lives in src/owlbear/bootstrap/hooks.py, src/owlbear/bootstrap/knowledge.py, src/owlbear/bootstrap/toolsets.py, and src/owlbear/bootstrap/__init__.py.
- TDD compliance exists already via archived RED task #843, so there is no missing test prerequisite. The board problem here is task staleness, not missing tests.
- Because the implementation has already landed under #843 and follow-on regression tests, sending #553 to todo would create duplicate builder work.

### Changes Made
- Claimed #553 for architecture review.
- Appended this Architecture Review with stale-task evidence.
- Returning #553 to ideation with an explicit block reason so it is not dispatched as fresh implementation work.

### Dependencies
- Verified: archived RED and implementation evidence exists in #843.
- Verified: no new dependencies required.
- Verified current evidence in src/owlbear/config.py, src/owlbear/bootstrap/hooks.py, src/owlbear/bootstrap/toolsets.py, src/owlbear/bootstrap/knowledge.py, src/owlbear/bootstrap/__init__.py, tests/test_config.py, and tests/test_browser_config_nesting.py.
