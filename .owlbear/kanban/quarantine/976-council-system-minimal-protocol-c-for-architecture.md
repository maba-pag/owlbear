---
id: 976
title: Council system — minimal Protocol C for architecture decisions
status: archived
priority: someday
created: 2026-03-24T03:03:35.9686875+01:00
updated: 2026-03-25T03:04:35.1144702+01:00
tags:
    - agent
    - phase-14
    - research
blocked: true
block_reason: 'Research recommends deferral at .40 confidence. No trigger conditions met: Copilot rate limit still binding, no architect-gate quality failures observed, no external project management. Three prior research docs independently rejected multi-persona deliberation. Revisit when a trigger condition from research doc section 4 is met.'
class: standard
---

Implement opt-in parallel-then-synthesize council for architecture gate decisions only. See docs/research/council-debate-system.md section 4. AC: (1) 2 perspective agents + 1 moderator agent using PydanticAI programmatic hand-off. (2) Council output is a structured Pydantic model with positions, consensus, dissent, and confidence. (3) Triggered only by kanban task tag council:arch. (4) Human approval gate on council output. (5) Token cost per session is at most 4 LLM calls. (6) No changes to default pipeline — council is opt-in only. Depends on: none (P8 agent framework is complete).

[[2026-03-24]] Tue 17:23

## Research

Research doc: docs/research/council-protocol-c-validation.md

Key findings:

- Technical feasibility confirmed (.85): asyncio.gather + PydanticAI structured output suffices; pydantic_graph beta is YAGNI.
- Architecture fit clean (.75): new council.py module, tag-triggered, no pipeline changes.
- Token cost still binding: 3 extra calls x 5 arch decisions = 15 calls per session (50 pct of Copilot rate-limit window).
- No evidence of architect-gate quality failures that would justify the cost.
- Three prior research docs independently rejected multi-persona deliberation.
- Nothing material changed since parent research (#145).

Recommendation: maintain deferral at .40 confidence. Trigger conditions in research doc section 4.
No new follow-up tasks (this task IS the follow-up from #145).

[[2026-03-25]] Wed 03:04

## Architecture Review

**Verdict:** BLOCK to ideation

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 2 perspective agents + 1 moderator using PydanticAI hand-off | Technically sound (asyncio.gather suffices) | No change needed if implemented |
| Council output is structured Pydantic model | Follows existing patterns (RetroFindings, ExtractionResult) | No change needed |
| Triggered only by council:arch tag | Correct opt-in isolation | No change needed |
| Human approval gate on council output | Correct safety boundary | No change needed |
| Token cost at most 4 LLM calls per session | Unrealistic: 3 calls x ~5 arch decisions = 15 calls/session (50 pct of rate-limit window) | AC contradicts research finding |
| No changes to default pipeline | Clean isolation | No change needed |

### Architecture Notes

The AC is well-specified for eventual implementation, but all four evaluation signals say defer:

1. Research recommendation: .40 confidence, maintain deferral. Nothing material changed since parent research (#145).
2. Token cost: 15 extra calls/session at current Copilot rate limits. AC line 5 claims 4 calls total but research calculates 15. This contradiction alone requires a rethink.
3. No demand signal: Zero architect-gate quality failures observed in board history that a council would have caught.
4. Prior art rejection: Three independent OwlBear research docs (conductor-orchestrator-superpowers, orchestration-agent-frameworks, quorum-room) all rejected multi-persona deliberation.

The existing 4-agent pipeline (researcher, architect, reviewer, auditor) already provides multi-perspective coverage at zero additional token cost.

Trigger conditions for revisiting (from research doc section 4):

- Copilot switches to non-rate-limited plan or higher-throughput endpoint
- Evidence that single-architect decisions produced quality defects a council would catch
- OwlBear manages external projects where the architect lacks domain context

### Changes Made

- Blocked to ideation: no trigger conditions met, research recommends deferral
- Task preserved as-is for future activation when a trigger condition is met

### Dependencies

- None changed. Task has no downstream dependents.

[[2026-03-25]] Wed 03:04

## Architecture Review

**Verdict:** BLOCK to ideation

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 2 perspective agents + 1 moderator using PydanticAI hand-off | Technically sound (asyncio.gather suffices) | No change needed if implemented |
| Council output is structured Pydantic model | Follows existing patterns (RetroFindings, ExtractionResult) | No change needed |
| Triggered only by council:arch tag | Correct opt-in isolation | No change needed |
| Human approval gate on council output | Correct safety boundary | No change needed |
| Token cost at most 4 LLM calls per session | Unrealistic: 3 calls x ~5 arch decisions = 15 calls/session (50 pct of rate-limit window) | AC contradicts research finding |
| No changes to default pipeline | Clean isolation | No change needed |

### Architecture Notes

The AC is well-specified for eventual implementation, but all four evaluation signals say defer:

1. Research recommendation: .40 confidence, maintain deferral. Nothing material changed since parent research (#145).
2. Token cost: 15 extra calls/session at current Copilot rate limits. AC line 5 claims 4 calls total but research calculates 15. This contradiction alone requires a rethink.
3. No demand signal: Zero architect-gate quality failures observed in board history that a council would have caught.
4. Prior art rejection: Three independent OwlBear research docs (conductor-orchestrator-superpowers, orchestration-agent-frameworks, quorum-room) all rejected multi-persona deliberation.

The existing 4-agent pipeline (researcher, architect, reviewer, auditor) already provides multi-perspective coverage at zero additional token cost.

Trigger conditions for revisiting (from research doc section 4):

- Copilot switches to non-rate-limited plan or higher-throughput endpoint
- Evidence that single-architect decisions produced quality defects a council would catch
- OwlBear manages external projects where the architect lacks domain context

### Changes Made

- Blocked to ideation: no trigger conditions met, research recommends deferral
- Task preserved as-is for future activation when a trigger condition is met

### Dependencies

- None changed. Task has no downstream dependents.
