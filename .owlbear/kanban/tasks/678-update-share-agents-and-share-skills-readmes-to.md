---
id: 678
title: Update share/agents and share/skills READMEs to reflect current counts
status: backlog
priority: nice-to-have
created: 2026-04-08T18:34:28.3160163+02:00
updated: 2026-04-08T18:34:28.3160163+02:00
tags:
    - scope:docs
    - ' type:docs'
    - ' source:analysis'
class: standard
---

## Context

Analysis synthesis identified that both READMEs in `share/` are stale:

- `share/agents/README.md`: Lists 15 agents, actual count is 23. Missing: voice panel agents (6: critic-voice, architect-voice, data-voice, enduser-voice, security-voice, pragmatist-voice), ideator, scribe. Tier assignment for voice agents and ideator is undefined.
- `share/skills/README.md`: Lists 29 skills, actual count is 32. Missing skills need identification by scanning the `share/skills/` directory.

## Acceptance Criteria

- [ ] AC1: `share/agents/README.md` lists all 23 agents with correct tier assignments
- [ ] AC2: Voice panel agents assigned to a tier (likely T3 or a new "Voice" tier)
- [ ] AC3: Ideator assigned to a tier (likely T1)
- [ ] AC4: Deprecated dispatcher agent marked clearly
- [ ] AC5: `share/skills/README.md` lists all 32 skills with correct category counts
- [ ] AC6: Deprecated/archived skills marked clearly (h-kanban-md, w-dispatch-planning, w-project-scoping)
