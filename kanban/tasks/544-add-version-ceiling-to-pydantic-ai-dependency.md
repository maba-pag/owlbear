---
id: 544
title: Add version ceiling to pydantic-ai dependency
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:48.087624+01:00
updated: 2026-03-07T00:47:43.8180798+01:00
started: 2026-03-07T00:45:03.3239141+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-02: pydantic-ai >=0.1.0 with no ceiling. See docs/config-dependency-audit.md.

Research (2026-03-07): N/A -- trivial version pin.
- Installed: v1.63.0, latest: v1.67.0, v1.0.0 released 2025-09-04
- Version policy: no breaking changes until V2 (April 2026 earliest)
- Current floor >=0.1.0 is wrong -- 0.1.x lacks Toolsets, RetryConfig, OpenAIChatModel
- Recommendation (.90): change to >=1.0.0,<2.0.0
- Risk: two private API imports (_agent_graph.HistoryProcessor, _run_context.RunContext) not covered by semver guarantee -- separate task needed

AC: Change pyproject.toml dep from pydantic-ai>=0.1.0 to pydantic-ai>=1.0.0,<2.0.0
