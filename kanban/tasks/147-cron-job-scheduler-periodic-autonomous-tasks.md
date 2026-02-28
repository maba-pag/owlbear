---
id: 147
title: Cron job scheduler — periodic autonomous tasks
status: ideation
priority: someday
created: 2026-02-27T14:59:53.7566789+01:00
updated: 2026-02-27T14:59:53.7566789+01:00
tags:
    - phase-12
    - daemon
depends_on:
    - 124
class: standard
---

Schedule recurring tasks: knowledge graph updates (re-crawl sources), codebase health checks (run tests, lint), upstream update scanning, analytics aggregation.

Simple cron-like scheduling stored in config. The daemon (bearclaw run) checks the schedule and triggers agent tasks. Each scheduled task is just a prompt sent to the appropriate agent.
