---
id: 1286
title: 'P2-02: Extract file-placement and layout sections to .github/copilot-instructions.md'
status: research
priority: needed
created: 2026-05-02T16:01:17.059804+00:00
updated: 2026-05-02T16:02:39.736412+00:00
tags:
- phase-2
- scope:docs
- shared-layer
parent: 1280
depends_on:
- 1285
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] r-project-standards §2 File Placement table extracted; skill retains commit format, attribution, priority, tags
- [ ] h-python-conventions Project Layout section extracted; skill retains coding conventions
- [ ] Extracted content (file placement table + project layout paths) added to .github/copilot-instructions.md
- [ ] No `serve/` paths remain in r-project-standards or h-python-conventions (MCP names excluded)
- [ ] Tests from #1285 pass for these two skills

## Scope

- IN: r-project-standards/SKILL.md, h-python-conventions/SKILL.md, .github/copilot-instructions.md
- OUT: Other P2 skills (#1287–#1291)