---
id: 1188
title: 'P2-03: Update agent/skill/instruction references + decisions README'
status: research
priority: important
created: 2026-04-30T00:52:05.085246+00:00
updated: 2026-04-30T00:53:36.518422+00:00
tags:
- phase-2
- scope:agents
- type:impl
parent: 1179
depends_on:
- 1186
- 1187
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- 7 agent files updated (researcher, test-writer, builder, doc-writer, reviewer, auditor, orchestrator): scribe removed from `agents:` list, DR instructions replaced with `h-decision-requests` skill reference
- `share/skills/r-pipeline-protocol/SKILL.md`: all scribe references replaced with create_dr tool usage
- `share/skills/w-orchestration/SKILL.md`: "dispatch scribe" pattern removed from orchestration cycle
- `share/instructions/pipeline-agents.instructions.md`: scribe references removed (if present)
- `.owlbear/decisions/README.md` rewritten for new format: 5-field schema, Cockpit as primary resolve path, file-edit as fallback
- All static tests from #1186 pass (no stale scribe refs)

## Scope

- IN: reference updates across agent/skill/instruction files + decisions README rewrite
- OUT: new skill creation (done in #1187), code changes, Cockpit

Brief: see parent #1179
