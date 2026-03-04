---
id: 544
title: Add version ceiling to pydantic-ai dependency
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:48.087624+01:00
updated: 2026-03-04T07:38:48.087624+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-02: pydantic-ai >=0.1.0 with no ceiling. Pre-1.0, actively refactoring. Fresh uv sync could pull breaking version. Add ceiling like >=0.1.0,<0.3. Lockfile mitigates day-to-day risk. AC: version ceiling in pyproject.toml. See docs/config-dependency-audit.md.
