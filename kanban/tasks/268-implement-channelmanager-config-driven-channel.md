---
id: 268
title: Implement ChannelManager - config-driven channel creation
status: archived
priority: important
created: 2026-02-28T14:20:42.4985699+01:00
updated: 2026-02-28T23:54:32.8525358+01:00
started: 2026-02-28T15:05:52.7580399+01:00
completed: 2026-02-28T23:54:32.8525358+01:00
tags:
    - phase-8
    - agent
    - channels
class: standard
---

## Context
Replaces the manual if/else channel selection in bearclaw CLI with a config-driven registry.
Adapted from nanobot ChannelManager pattern. See docs/research/bootstrap-assembly.md S3.2.

## Architectural Decision: MERGED into #267
The create_channel() helper function inside bootstrap.py (#267) fulfills this task's requirements.
A separate ChannelManager class adds an unnecessary abstraction layer for what is currently a
3-branch factory function (cli/slack/voice). Per KISS and YAGNI:

- Single-channel operation: bootstrap takes channel_name, creates one channel. No registry needed.
- Multi-channel (future): when we add MessageBus support, a ChannelManager makes sense. Not now.
- The bootstrap research doc itself says: 'NO for bootstrap MVP, YES as follow-up' regarding MessageBus.

## Original Acceptance Criteria (now fulfilled by #267 create_channel helper)
- [x] create_channel(settings, name) -> ChannelPlugin factory function (in bootstrap.py)
- [x] Supports: cli, slack, voice (lazy import for optional deps)
- [x] Unit tests with mock channels (tested as part of bootstrap tests)
- [ ] ~~ChannelManager class~~ — NOT NEEDED for MVP

## Status
Merged into #267. This task should be closed.
