---
id: 558
title: Consider RichChannel protocol for approval gate
status: backlog
priority: someday
created: 2026-03-04T07:39:00.3915663+01:00
updated: 2026-03-07T02:26:09.3008221+01:00
started: 2026-03-07T02:20:41.5285563+01:00
tags:
    - audit
    - refactor
    - safety
class: standard
---

ARC-07: ApprovalGateToolset uses hasattr(channel,'send_blocks') at runtime to choose Slack vs plain text. Minor duck-typing. Could extend ChannelPlugin or use RichChannel protocol. AC: design choice documented.

Research complete - see docs/research/rich-channel-protocol.md

**Finding (.90 confidence):** Do NOT create a RichChannel protocol. This task is subsumed by #482 (Extend ChannelPlugin protocol for rich capabilities). Widening ChannelPlugin with default fallback implementations (PEP 544 default method bodies) eliminates all hasattr duck-typing without introducing a second protocol. A RichChannel protocol would just replace hasattr with isinstance checks - same branching, no real improvement.

Research checklist:
1. Theoretical validity: RichChannel is theoretically valid but unnecessary - PEP 544 default bodies solve this more simply
2. Prior art: PEP 544 default bodies, mypy Protocol docs, channel-protocol-extension.md
3. Technical feasibility: 3 hasattr sites eliminated by #482
4. Architecture fit: RichChannel adds complexity without benefit (KISS/YAGNI violation)
5. Implementation approach: Proceed with #482 - no new tasks needed

Disposition: Duplicate of #482. Close when #482 is implemented.
