---
id: 1290
title: 'P2-06: Migrate r-doc-standards chain atomically (skill + instruction + doc-audit
  prompt)'
status: research
priority: needed
created: 2026-05-02T16:01:17.114235+00:00
updated: 2026-05-02T16:02:39.769562+00:00
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

- [ ] r-doc-standards/SKILL.md: OwlBear-specific scope enumeration (doc-type table, serve/ paths, audience table) extracted
- [ ] If insufficient generic substance remains, entire skill moved to .owlbear/skills/; if generic rules remain, skill stays in share/ with reduced content
- [ ] doc-standards.instructions.md: applyTo and description updated to match new skill location
- [ ] doc-audit.prompt.md moved from share/prompts/ to .owlbear/prompts/
- [ ] No dangling cross-references between the three chain members (skill ↔ instruction ↔ prompt)
- [ ] Migration is atomic — all three files updated in the same commit
- [ ] Tests from #1285 pass for r-doc-standards chain assertions

## Scope

- IN: r-doc-standards/SKILL.md, doc-standards.instructions.md, doc-audit.prompt.md — all three atomically
- OUT: Other prompts (#1291), architecture extraction (#1289)