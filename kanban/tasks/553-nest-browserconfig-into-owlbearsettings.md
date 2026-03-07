---
id: 553
title: Nest BrowserConfig into OwlBearSettings
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:55.9671683+01:00
updated: 2026-03-07T01:02:29.2486181+01:00
started: 2026-03-07T00:55:28.949134+01:00
tags:
    - audit
    - config
    - browser
class: standard
---

INT-18: BrowserConfig not configurable via OWLBEAR_ env vars. See docs/browser-config-nesting-research.md for full analysis.

Approach: Nest BrowserConfig into OwlBearSettings using env_nested_delimiter='__' and nested_model_default_partial_update=True.

AC:
1. OwlBearSettings has browser: BrowserConfig field with env_nested_delimiter='__' and nested_model_default_partial_update=True in model_config
2. OWLBEAR_BROWSER__HEADLESS=true correctly sets settings.browser.headless (and all other BrowserConfig fields)
3. bootstrap.py uses settings.browser instead of BrowserConfig() in all 3 call sites (_build_hooks_and_reporters, _build_web_search_toolset, build_toolsets)
4. Existing BrowserConfig tests still pass (BrowserConfig stays a frozen BaseModel)
5. New test verifies env var override for at least one nested field
