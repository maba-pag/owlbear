---
id: 743
title: Implement loop detection in orchestrator dispatch
status: todo
priority: needed
created: 2026-03-11T21:16:59.0137115+01:00
updated: 2026-03-12T08:38:40.0876961+01:00
started: 2026-03-12T08:38:40.0876961+01:00
tags:
    - phase-daemon
    - agent
    - orchestrator
claimed_by: researcher
claimed_at: 2026-03-12T08:38:40.0876961+01:00
class: standard
---

Add per-task failure counting to orchestrator wave dispatch. After configurable max failures (default 3), skip task and escalate to user via channel (Slack/CLI) with retry/skip/stop options. Persist attempt counts in ErrorJournal. See docs/research/mission-control-research.md S3.2 and S4.
