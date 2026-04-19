---
id: 988
title: Update skill docs for guidance field and `block:user` tag
status: backlog
priority: needed
created: 2026-04-18T21:23:00.852313+00:00
updated: 2026-04-18T21:45:25.400397+00:00
tags:
- type:docs
- scope:skills
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D9.

## Problem
Skill docs don't document the new `guidance` field or `block:user` tag semantics.

## Acceptance Criteria
- `share/skills/h-mcp-kanban/SKILL.md`: document `guidance` field in tool schema section — purpose, when populated, JSON serialization order.
- `share/skills/r-pipeline-protocol/SKILL.md`: clarify DR-required-on-block rule, `block:user` exemption for user-driven blocks.
- `share/skills/w-decision-routing/SKILL.md`: add entry point note that block guidance directs agents here.
- No other skill files changed.

## Files
- `share/skills/h-mcp-kanban/SKILL.md`
- `share/skills/r-pipeline-protocol/SKILL.md`
- `share/skills/w-decision-routing/SKILL.md`

## Dependencies
- Depends on: all implementation tasks complete (needs final field names and message text)
[[2026-04-18]]
## Research
- Research doc: .owlbear/research/skill-docs-guidance-block-user-988.md
- Sources: 6 studied (all internal), 4 high-relevance
- Recommendation: three-file insertion plan confirmed (confidence: .90)
- Challenge: SKIPPED — trivial docs task, all decisions locked in Brief D9
- Follow-up tasks created: none (leaf task)
- Decision requests: none — T1 autonomous

### Insertion plan summary
1. `h-mcp-kanban/SKILL.md`: new "Response: Guidance Field" section after Tool Summary — documents `guidance: list[str]`, JSON order, when populated, advisory semantics
2. `r-pipeline-protocol/SKILL.md`: extend Blocking Convention — explicit DR-required rule, `block:user` exemption for Cockpit-initiated blocks
3. `w-decision-routing/SKILL.md`: entry-point note in "When to Create" section — confirms block-guidance directs agents here

### Dependency gap
`depends_on` is empty but must be [985, 989, 991] per architect graph. Implementation tasks must land before docs can reference final message text. Wire before dispatching to downstream agents.