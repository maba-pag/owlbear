---
id: 450
title: Set user-invocable false on pipeline agents
status: archived
priority: important
created: 2026-03-03T17:30:07.5852603+01:00
updated: 2026-03-04T07:58:25.9301118+01:00
started: 2026-03-03T18:03:40.5085201+01:00
completed: 2026-03-04T07:58:25.9301118+01:00
tags:
    - agent-refactor
    - agent
    - phase-refactor
depends_on:
    - 443
    - 444
    - 445
    - 446
class: standard
---

Add user-invocable: false to builder, reviewer, writer, closer frontmatter. These agents should only be dispatched by orchestrator. User confirmed they never invoke these directly. See docs/agent-quality-analysis.md section 6.7.
