---
id: 148
title: 'Research: OpenClaw ecosystem — addon patterns, compatibility assessment'
status: archived
priority: someday
created: 2026-02-27T15:00:05.2199197+01:00
updated: 2026-03-22T19:17:36.3800551+01:00
started: 2026-03-01T20:09:04.9967263+01:00
completed: 2026-03-22T19:17:36.3800551+01:00
tags:
    - research
    - phase-14
blocked: true
block_reason: Superseded by archived OpenClaw research (#581/#590); remaining addon and marketplace questions need a fresh decision-scoped task if revived.
class: standard
---

Evaluate the OpenClaw addon ecosystem. What is it? What addons exist? Are they compatible with PydanticAI's tool system? Could we consume OpenClaw addons as OwlBear tools, or is the architecture too different?

Alternative framing: should OwlBear have its own addon/plugin system? What would that look like? Marketplace vs local only.

[[2026-03-21]] Sat 12:43
## Architecture Review
**Verdict:** Block

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Evaluate the OpenClaw addon ecosystem. What is it? What addons exist? Are they compatible with PydanticAI's tool system? Could we consume OpenClaw addons as OwlBear tools, or is the architecture too different? | Too broad and already answered by archived #581/#590 research; it mixes ecosystem inventory, compatibility analysis, and architectural feasibility without a bounded deliverable. | Block as superseded by existing research. |
| Alternative framing: should OwlBear have its own addon/plugin system? What would that look like? Marketplace vs local only. | This is a product and architecture decision, not an implementation-ready backlog item. It would cut across skill loading, toolset assembly, approval and sandboxing, and distribution policy. | Return to ideation; require a fresh decision-scoped task if revived. |

### Architecture Notes
- Existing extension points are OwlBear-native, not OpenClaw-addon-native:
  - build_toolsets() wires concrete toolsets and loads SkillRegistry from .github/skills/*/SKILL.md.
  - SkillRegistry progressively loads markdown skills, not third-party executable addon bundles.
  - AgentRegistry appends that SkillRegistry only for agents that explicitly declare skills.
- Archived research already covers this space:
  - #581 / docs/research/openclaw-ecosystem.md rejects third-party skill compatibility (.25 confidence) and records OwlBear's current skill system as already aligned with the useful patterns.
  - #590 / docs/research/openclaw-skills.md identifies the reusable OpenClaw patterns (heartbeat, session-memory hook, DAEMON_STARTUP) and rejects Lobster and broader addon compatibility work.
- A real addon or plugin-system effort would be multi-domain and not backlog-to-todo ready:
  - skills/registry.py loader format and trust model
  - bootstrap/toolsets.py assembly and wrapping invariants
  - bootstrap/registry.py agent exposure and tool resolution
  - approval, sandboxing, and packaging or distribution policy
- TDD compliance: N/A. This is a stale research and decision card, not an implementation task.
- Failure mode map: N/A. No codepath is being approved.

### Changes Made
- Verified #148 is a backlog research card with no explicit, testable AC.
- Verified the superseding archived research tasks #581 and #590 plus docs/research/openclaw-ecosystem.md and docs/research/openclaw-skills.md.
- Returning #148 to ideation with an explicit block reason instead of routing stale scope into builder flow.

### Dependencies
- Verified source-of-truth research: #581, #590.
- Verified resulting implementation follow-ups already exist: #616, #619, #622, #624.
