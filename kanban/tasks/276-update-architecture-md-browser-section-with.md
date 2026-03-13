---
id: 276
title: Update architecture.md browser section with constraint rationale
status: archived
priority: important
created: 2026-02-28T14:21:56.3714242+01:00
updated: 2026-03-01T00:02:51.0211954+01:00
started: 2026-02-28T22:56:18.9799922+01:00
completed: 2026-03-01T00:02:51.0211954+01:00
tags:
    - docs
    - browser
    - phase-6
class: standard
---

## Context
Research #264 confirmed 'keep custom' decision for browser module.

## Acceptance Criteria
- [ ] Update architecture.md browser section with specific constraint citations
- [ ] Reference docs/research/browser-automation.md for full analysis
- [ ] Note: no OSS library handles Edge CDP lifecycle (find/probe/launch/connect)
- [ ] Note: browser-use conflicts with PydanticAI agent architecture
- [ ] Note: KISS — 1200 LOC vs 15-20k LOC alternatives
