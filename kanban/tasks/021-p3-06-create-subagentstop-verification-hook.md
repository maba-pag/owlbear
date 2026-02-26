---
id: 21
title: 'P3-06: Create SubagentStop verification hook'
status: ideation
priority: medium
created: 2026-02-24T15:12:41.8109498+01:00
updated: 2026-02-26T18:53:01.1697782+01:00
tags:
    - phase-3
    - hooks
depends_on:
    - 16
class: standard
---

AC: Create .github/hooks/subagent-stop-verify.json. Hook fires on SubagentStop event. Checks that subagent produced expected changes: (1) if task involved file creation, verify files exist, (2) if task involved tests, run relevant test file. Exit 2 to block if verification fails, 0 to allow. Backing script reads subagent output from stdin JSON, performs checks. If VS Code hooks not stable, comment out with explanation. Files: .github/hooks/subagent-stop-verify.json + backing script.
