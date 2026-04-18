---
id: 982
title: 'Docs: skill updates for guidance + block:user'
status: backlog
priority: important
created: 2026-04-18T21:18:36.281028+00:00
updated: 2026-04-18T21:18:36.281028+00:00
tags:
- type:docs
parent: 973
depends_on:
- 977
- 980
- 981
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Documentation updates per D9.

## Acceptance Criteria
Files updated:

1. `share/skills/h-mcp-kanban/SKILL.md` — document the `guidance: list[str]` field on `KanbanTask`. List the three V1 guidance triggers (block, forward-skip, success-commit) and what each emits. Note that the field is the first in JSON serialization order for salience.

2. `share/skills/r-pipeline-protocol/SKILL.md` — clarify "every block requires a Decision Request" rule. Document the `block:user` tag exemption (agents do NOT create DRs for tasks tagged `block:user`). Cross-reference w-decision-routing.

3. `share/skills/w-decision-routing/SKILL.md` — add a note that the kanban MCP server's `guidance` field on block operations directs the agent here.

No changes to scribe agent or DR file format (out of scope per Brief).