---
id: 1282
title: 'P1-02: Split owlbear-system.instructions.md — extract directory table to .github/copilot-instructions.md'
status: research
priority: critical
created: 2026-05-02T16:01:10.599380+00:00
updated: 2026-05-02T16:02:06.193591+00:00
tags:
- phase-1
- scope:docs
- shared-layer
parent: 1280
depends_on:
- 1281
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] §2 Directory Structure table extracted from owlbear-system.instructions.md
- [ ] Extracted table added to `.github/copilot-instructions.md` under a Directory Structure heading
- [ ] owlbear-system.instructions.md retains §1 Decision Heuristics, Tech Stack, Pipeline, §3 Memory Governance, §4 Operational Fundamentals
- [ ] owlbear-system.instructions.md description/title updated to project-neutral wording (no "OwlBear system" in the description frontmatter)
- [ ] No `serve/` paths remain in owlbear-system.instructions.md (MCP server names excluded)
- [ ] Tests from #1281 pass for the instruction-neutrality assertions

## Scope

- IN: owlbear-system.instructions.md edit, .github/copilot-instructions.md addition
- OUT: Cross-reference updates (that is #1283), init.py changes (#1284)