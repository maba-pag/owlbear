---
id: 482
title: Extend ChannelPlugin protocol for rich capabilities
status: backlog
priority: important
created: 2026-03-04T07:37:59.7568289+01:00
updated: 2026-03-06T23:10:35.4599661+01:00
started: 2026-03-06T23:05:04.7768026+01:00
tags:
    - audit
    - refactor
    - channels
class: standard
---

ARC-10/INT-06: ChannelPlugin defines only name/send/receive. SlackChannel adds send_blocks, send_file, send_image, register_action. CLIChannel adds send_file. Consumers use hasattr duck-typing.

Research complete  see docs/channel-protocol-extension-research.md

Recommendation (.85 confidence): Widen ChannelPlugin with default fallback implementations (send_file, send_blocks, send_image delegate to send()). Make CLIChannel/SlackChannel explicitly inherit ChannelPlugin. Delete all 3 hasattr checks. Do NOT add register_action (zero consumers).

Research checklist:
1. Theoretical validity: Sound  PEP 544 supports default method bodies in Protocols
2. Prior art: PEP 544, mypy Protocol docs
3. Technical feasibility: Fully compatible with Python 3.12, PydanticAI, existing tests
4. Architecture fit: Minimal change  widens one protocol, inherits in 2 channels, removes 3 hasattr checks
5. Implementation approach: Add 3 methods with send()-delegating defaults to ChannelPlugin

AC: no hasattr channel checks in production code.
