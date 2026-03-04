---
id: 482
title: Extend ChannelPlugin protocol for rich capabilities
status: ideation
priority: important
created: 2026-03-04T07:37:59.7568289+01:00
updated: 2026-03-04T07:37:59.7568289+01:00
tags:
    - audit
    - refactor
    - channels
class: standard
---

ARC-10/INT-06: ChannelPlugin defines only name/send/receive. SlackChannel adds send_blocks, send_file, send_image, register_action. CLIChannel adds send_file. Consumers use hasattr duck-typing. Define RichChannelPlugin protocol or add optional methods with defaults. AC: no hasattr channel checks in production code. See docs/architecture-audit.md, docs/integration-audit.md.
