---
id: 1187
title: 'P2-02: Create h-decision-requests skill + delete scribe and w-decision-routing'
status: research
priority: needed
created: 2026-04-30T00:52:00.447027+00:00
updated: 2026-04-30T00:53:22.505673+00:00
tags:
- phase-2
- scope:agents
- type:impl
parent: 1179
depends_on:
- 1186
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `share/skills/h-decision-requests/SKILL.md` created (~50 lines) documenting: when to create DR, how (create_dr tool params), body format, fire-and-forget semantics
- `share/agents/scribe.agent.md` deleted
- `share/skills/w-decision-routing/SKILL.md` deleted
- New skill has valid frontmatter (name: h-decision-requests, description, user-invocable: false)
- All tests from #1186 pass (deletion and existence checks)

## Scope

- IN: new skill creation + two file deletions
- OUT: reference updates in other files (handled by #1188)

Brief: see parent #1179
