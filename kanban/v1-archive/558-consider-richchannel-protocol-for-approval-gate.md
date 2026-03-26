---
id: 558
title: Consider RichChannel protocol for approval gate
status: archived
priority: someday
created: 2026-03-04T07:39:00.3915663+01:00
updated: 2026-03-22T19:17:44.236804+01:00
started: 2026-03-07T02:20:41.5285563+01:00
completed: 2026-03-22T19:17:44.236804+01:00
tags:
    - audit
    - refactor
    - safety
blocked: true
block_reason: 'Duplicate of archived #482 split work (#675/#676/#677). RichChannel was rejected in research and the underlying ChannelPlugin change already shipped.'
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

[[2026-03-21]] Sat 07:02
## Architecture Review

**Verdict:** BLOCK -> ideation (close as superseded)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| design choice documented | The research is correct, but the decision is now obsolete: the codebase already adopted the widen-ChannelPlugin approach and removed the duck-typed branch this task was evaluating. | SUPERSEDED |

### Architecture Notes

The current source tree already resolves ARC-07 without introducing a separate RichChannel protocol:
- src/owlbear/channels/base.py widens ChannelPlugin with send_file, send_blocks, and send_image default implementations.
- src/owlbear/safety/gate.py now calls channel.send_blocks() directly.
- src/owlbear/tools/screenshot.py now calls channel.send_image() directly.
- A repo-wide search for hasattr(channel...) / hasattr(self.channel...) in src/ returns zero matches.

Task lineage also confirms this is stale board state, not actionable implementation scope:
- #482 is archived as the umbrella task and explicitly marked split/superseded.
- #675 archived the protocol widening.
- #676 archived the production-code cleanup that removed hasattr duck-typing.
- #677 archived the protocol fallback tests.

Routing #558 to todo would violate KISS/YAGNI and the single-source-of-truth rule by reopening already archived work. No separate test task is needed because there is no remaining implementation task to send into TDD flow.

### Changes Made
- Appended this Architecture Review.
- Marked task for backlog rejection because the implementation already shipped under archived split tasks.

### Dependencies
- Verified: #482 archived (umbrella split task).
- Verified: #675 archived (ChannelPlugin defaults).
- Verified: #676 archived (removed production hasattr checks).
- Verified: #677 archived (tests for widened protocol).
