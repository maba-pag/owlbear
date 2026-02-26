---
id: 73
title: 'P6-09: Implement BearClaw browser CLI'
status: done
priority: medium
created: 2026-02-26T23:31:14.5768479+01:00
updated: 2026-02-27T00:16:50.9659969+01:00
started: 2026-02-26T23:43:02.8467371+01:00
completed: 2026-02-27T00:16:50.9659969+01:00
tags:
    - phase-6
    - cli
    - browser
depends_on:
    - 69
    - 72
class: standard
---

Add 'bearclaw browser' typer group to cli.py. Commands: start [--port 9222] launches Edge with CDP debug port (uses launcher module), stop kills tracked PID, status checks if CDP endpoint is reachable. Store PID in config dir. AC: tests from #72 pass.
