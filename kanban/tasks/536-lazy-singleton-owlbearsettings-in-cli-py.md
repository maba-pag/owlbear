---
id: 536
title: Lazy-singleton OwlBearSettings in cli.py
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:41.3865662+01:00
updated: 2026-03-10T17:33:21.5568366+01:00
started: 2026-03-07T00:29:37.413524+01:00
tags:
    - audit
    - dry
    - scope:cli
depends_on:
    - 481
class: standard
---

DRY-05: OwlBearSettings() instantiated 12 times in cli.py. pydantic-settings re-reads env vars each time. See docs/lazy-singleton-settings-research.md

**Approach:** functools.cache getter (.90 confidence). Add @functools.cache on a get_settings() function, replace 12 call sites. Add autouse cache_clear() fixture for tests.

**AC:**

- [ ] get_settings() with @functools.cache in cli.py
- [ ] All 12 OwlBearSettings() calls replaced with get_settings()
- [ ] Autouse fixture calls get_settings.cache_clear() after each test
- [ ] All existing CLI tests pass without modification
- [ ] ruff clean
