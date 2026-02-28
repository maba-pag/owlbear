---
id: 72
title: 'P6-08: Test BearClaw browser CLI subcommands'
status: archived
priority: medium
created: 2026-02-26T23:31:07.3645159+01:00
updated: 2026-02-27T10:00:35.2308714+01:00
started: 2026-02-26T23:43:02.4702466+01:00
completed: 2026-02-27T10:00:35.2308714+01:00
tags:
    - phase-6
    - test
    - cli
    - browser
depends_on:
    - 69
class: standard
---

TDD tests for bearclaw browser start/stop/status commands. Test: start launches Edge with correct flags, stop kills tracked PID, status checks CDP endpoint reachability. Mock subprocess calls. AC: all CLI paths tested, error cases covered.
