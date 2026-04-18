---
id: 1004
title: Ad-hoc Critic invocation in ideation flow (user-request + Mediator 
  self-trigger)
status: research
priority: important
created: 2026-04-18T21:47:42.612522+00:00
updated: 2026-04-18T21:47:42.612522+00:00
tags:
- type:improvement
- scope:agents
- scope:skills
- ideation
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem
The Critic (`ideation-critic`) is currently invoked only at fixed moment boundaries: standalone after M1, M2, M4, M5, and embedded inside each domain panelist's Critic loop. This works for planned moment transitions but misses the "unexpected hard call surfaces mid-flow" case — when the user proposes (or the Mediator considers) a structural addition or deviation that wasn't on the M3-M4 panel agenda.

During the ideation session for #984 (agent-audit prompt rewrite), the user explicitly requested: *"please reflect on that, maybe even ask the critic for its opinion, even if thats not planned. i think this is important to get right."* — referring to a proposed new audit dimension that surfaced mid-walkthrough. The ad-hoc Critic invocation surfaced critical false-positive risks (confidence 0.28 against the proposal) that would otherwise have been baked into the Brief.

This pattern needs to be encoded so it isn't dependent on the user knowing to ask.

## Fix
Allow ad-hoc Critic invocation at any point in the 6-moment flow, by either:
1. **User request:** user asks "what does the Critic think?" or similar — Mediator invokes `ideation-critic` standalone with current context.
2. **Mediator self-invocation:** when the user proposes (or Mediator considers) a structural addition, dimension change, or material deviation NOT covered by the prior panel deliberation, the Mediator MUST invoke the Critic standalone before incorporating it into the Brief or decisions.

## Acceptance Criteria
- `w-ideation` documents ad-hoc Critic invocation explicitly (likely as a new section or addition to existing Critic-loop section in `h-ideation-panel`).
- Trigger conditions defined: (a) user request, (b) Mediator self-trigger when proposed change is structural / changes dimension count / introduces new artifact / contradicts panel synthesis.
- Worked example showing a Mediator self-invocation: scenario, focused Critic prompt, how Critic's output is presented to user (with attribution and confidence).
- Rule clarifies this is ADDITIVE to existing fixed-boundary Critic checks, not a replacement.
- Brief (and decisions.md) record ad-hoc Critic findings the same way fixed-boundary findings are recorded.

## Context
Surfaced during ideation session for #984. Sister tasks: #996 (askQuestions discipline), #997 (skill pre-flight), #998 (planner approval), #999 (walkthrough quality). All five are ideation-workflow improvements from a single session.