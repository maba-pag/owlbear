---
id: 1274
title: 'P1-08: Update memory skill documentation'
status: review
priority: important
created: 2026-05-02T03:43:38.563184+00:00
updated: 2026-05-03T14:06:01.512060+00:00
tags:
- phase-1
- scope:docs
parent: 1266
depends_on:
- 1273
blocked: false
block_reason:
claimed_at: 2026-05-03T14:06:01.512060+00:00
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
[[2026-05-03]]
## Test-Writer Notes
- Non-impl pass-through: AC references only SKILL.md files (h-mcp-memory, h-memory-structure, w-mem-curation, r-pipeline-protocol).
- No Python implementation keywords found in AC (no `implement`, `function`, `class`, `src/`, `serve/`, `.py`, `endpoint`).
- All 5 AC lines describe documentation content updates to `.md` skill files — no testable Python interfaces exist.
- No tests applicable.
[[2026-05-03]]
## Builder Notes
- Non-implementation task detected from Test-Writer Notes.
- No code or test changes required in GREEN phase.
- Files changed: none.
- Tests: not applicable (documentation-only scope).
- Lint: not applicable for builder phase on this pass-through task.
- Evidence summary: AC and scope target SKILL.md documentation updates only.
- Post-task reflection:
  - Problem faced: none; task is explicitly pass-through.
  - Workaround applied: followed Step 0a non-impl path to avoid unnecessary edits.
  - Pattern discovered: explicit Test-Writer pass-through markers prevent false implementation work.
  - Quality gap: none observed for builder scope.