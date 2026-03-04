---
id: 558
title: Consider RichChannel protocol for approval gate
status: ideation
priority: someday
created: 2026-03-04T07:39:00.3915663+01:00
updated: 2026-03-04T07:39:00.3915663+01:00
tags:
    - audit
    - refactor
    - safety
class: standard
---

ARC-07: ApprovalGateToolset uses hasattr(channel,'send_blocks') at runtime to choose Slack vs plain text. Minor duck-typing. Could extend ChannelPlugin or use RichChannel protocol. AC: design choice documented. See docs/architecture-audit.md.
