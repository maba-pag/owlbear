---
id: 416
title: Approval gate Slack enrichment — send_blocks for interactive approvals
status: backlog
priority: important
created: 2026-03-01T20:20:34.8118849+01:00
updated: 2026-03-01T20:24:07.2504439+01:00
started: 2026-03-01T20:24:07.2504439+01:00
tags:
    - phase-13
    - slack
    - channels
    - agent
class: standard
---

From #307 slack-structured-proposals-research.md. Teach ApprovalGateToolset to use send_blocks() when channel supports it (isinstance check or duck-typing). Send interactive approval buttons instead of plain text. Non-Slack channels fall back to send(). AC: ApprovalGateToolset sends Block Kit approval buttons on Slack; plain text on CLI; button clicks route through text bridge to existing yes/no flow. Depends on #307, #413, #414.
