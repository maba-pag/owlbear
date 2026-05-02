---
id: 1289
title: 'P2-05: Extract r-architecture-standards sections to .owlbear/instructions/'
status: research
priority: needed
created: 2026-05-02T16:01:17.102347+00:00
updated: 2026-05-02T16:02:39.763654+00:00
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

- [ ] New file .owlbear/instructions/architecture.instructions.md created with applyTo: "serve/**"
- [ ] Contains extracted v2 overview, namespace table, domain taxonomy, package dependency rules from r-architecture-standards
- [ ] r-architecture-standards/SKILL.md retains only generic MCP server conventions, module-quality rules, error handling patterns
- [ ] No `serve/` paths remain in the shared r-architecture-standards skill (MCP names excluded)
- [ ] Tests from #1285 pass for r-architecture-standards assertions

## Scope

- IN: r-architecture-standards/SKILL.md, .owlbear/instructions/architecture.instructions.md (new)
- OUT: Other skill genericizations (#1286–#1288), doc-standards chain (#1290)