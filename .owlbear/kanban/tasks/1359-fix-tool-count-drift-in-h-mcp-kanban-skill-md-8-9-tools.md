---
id: 1359
title: Fix tool count drift in h-mcp-kanban SKILL.md (8 → 9 tools)
status: backlog
priority: nice-to-have
created: 2026-05-05T08:55:03.657866+00:00
updated: 2026-05-05T08:55:18.815088+00:00
tags:
- docs
- mcp-kanban
parent: 1349
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context\n\n`share/skills/h-mcp-kanban/SKILL.md` description says "8 tools" but the actual server exposes 9 (create_dr was added as the 9th). Flagged as informational drift in two consecutive review cycles for #1349.\n\n## Acceptance Criteria\n\n- [ ] SKILL.md description updated from "8 tools" to "9 tools"\n- [ ] Tool listing in SKILL.md includes `create_dr` entry\n- [ ] No other content drift between SKILL.md and serve/mcp-kanban/README.md\n\n## Notes\n\n- SKILL.md is agent-executable → architect scope, not doc-writer\n- Parent: #1349