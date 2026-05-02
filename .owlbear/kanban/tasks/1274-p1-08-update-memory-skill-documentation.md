---
id: 1274
title: 'P1-08: Update memory skill documentation'
status: todo
priority: important
created: 2026-05-02T03:43:38.563184+00:00
updated: 2026-05-02T03:45:18.132518+00:00
tags:
- phase-1
- scope:docs
parent: 1266
depends_on:
- 1273
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Update skill documentation to reflect the new file-based architecture, tool API, and curation workflow.

Brief: see parent #1266

## Scope

**In scope:**
- `share/skills/h-mcp-memory/SKILL.md` — tool reference (5 tools, params, access rules)
- `share/skills/h-memory-structure/SKILL.md` — entry shape, file format, frontmatter schema
- `share/skills/w-mem-curation/SKILL.md` — curation workflow (state promotion, delete/purge, approval flow)
- `share/skills/r-pipeline-protocol/SKILL.md` — update Post-task Reflection section to reference new tool names

**Out of scope:**
- Agent file changes (no `.agent.md` modifications in this task)
- Consumer documentation (README updates for the package if needed — separate task)
- Instruction stub changes (existing `applyTo` patterns remain valid)

## Acceptance Criteria

- [ ] h-mcp-memory documents all 5 tools with params, return values, and access restrictions
- [ ] h-memory-structure documents the YAML frontmatter schema, 9 categories, 4 states, confidence range
- [ ] w-mem-curation reflects the state machine (pending→curated→approved→deleted) and purge flow
- [ ] r-pipeline-protocol Post-task Reflection references `store_learning` (not old tool name)
- [ ] No references to SQLite, old tool names, or old schema remain in updated skills
- [ ] All skill files pass markdown lint (no broken links, valid frontmatter)