---
id: 505
title: Sync copilot-instructions.md agent inventory with actual files
status: backlog
priority: important
created: 2026-03-04T07:38:17.6612106+01:00
updated: 2026-03-06T23:41:36.6459272+01:00
started: 2026-03-06T23:40:07.8549374+01:00
tags:
    - audit
    - docs
class: standard
---

DOC-F-09: Agent inventory table lists writer agent but no writer.md exists in src/owlbear/agents/. Table says 8 agents, disk has 7. Verify intent and update table. AC: agent table matches files on disk. See docs/documentation-audit.md.

## Research (2026-03-06)

N/A - trivial docs sync, rationale: table-to-disk naming mismatch.

### Findings

**Original DOC-F-09 is stale.** writer.md now exists in src/owlbear/agents/. The actual mismatch is:

1. src/owlbear/agents/closer.md exists on disk but is NOT in the agent inventory table.
2. closer.md has the identical role as 'auditor' in the table ('Verify done tasks, archive confirmed, commit + push').
3. .github/agents/auditor.agent.md exists and matches the table entry.
4. No auditor.md exists in src/owlbear/agents/ - only closer.md.

This is a naming inconsistency: .github/agents/ and the table use 'auditor', but src/owlbear/agents/ uses 'closer' for the same role.

### Proposed fix

Rename src/owlbear/agents/closer.md to auditor.md and update name: field inside from 'closer' to 'auditor'. This aligns all three locations. No table change needed - table is already correct.
