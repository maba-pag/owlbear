---
id: 75
title: 'P6-11: Implement BrowserToolset CDP mode + tab naming'
status: done
priority: medium
created: 2026-02-26T23:31:29.7092589+01:00
updated: 2026-02-27T00:16:53.9747473+01:00
started: 2026-02-26T23:43:03.7158592+01:00
completed: 2026-02-27T00:16:53.9747473+01:00
tags:
    - phase-6
    - browser
depends_on:
    - 71
    - 74
class: standard
---

Update BrowserToolset.setup() to pass through CDP config to BrowserManager. In CDP mode, set page title prefix '[OwlBear] {task}' for identification. Track OwlBear-opened pages for cleanup. Log warning on CDP attach: full session access. AC: tests from #74 pass, tab naming works.
