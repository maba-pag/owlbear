---
id: 319
title: Add fix-attempt delegation to builder tdd-workflow
status: ideation
priority: needed
created: 2026-03-30T20:38:22.4647449+02:00
updated: 2026-03-30T20:38:22.4647449+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 318
class: standard
---

AC:
1. tdd-workflow skill updated: after 2nd verify failure, construct retry_hint and delegate to fix-attempt subagent
2. Builder agents array updated to include fix-attempt
3. Retry_hint includes specific error info (Reflexion-style verbal feedback)
4. Builder handles fix-attempt result: FIXED continues to commit, FAILED blocks task
5. Builder still caps at 2 retries total (same-context + fresh-context = 2 total attempts after initial)
See docs/research/fresh-context-retry-builder.md
