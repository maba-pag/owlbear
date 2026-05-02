---
id: 1285
title: 'P2-01: Test — path neutrality verification for share/skills/'
status: research
priority: critical
created: 2026-05-02T16:01:17.041733+00:00
updated: 2026-05-02T16:02:39.723408+00:00
tags:
- phase-2
- scope:test
- shared-layer
parent: 1280
depends_on:
- 1282
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] Pytest test file exists that verifies P2 completion conditions
- [ ] Test asserts `grep -r 'serve/' share/skills/ | grep -v 'mcp-\|Example ('` returns zero hits
- [ ] Test asserts h-quality-runner contains prose directing agents to read project config for path routing
- [ ] Test asserts r-architecture-standards retains only generic MCP/module-quality rules (no namespace table, no domain taxonomy)
- [ ] Test asserts r-doc-standards chain has no dangling cross-references (skill ↔ instruction ↔ prompt)
- [ ] Test asserts 3 OwlBear-dev-only prompts exist in .owlbear/prompts/ not share/prompts/
- [ ] All tests fail initially (RED phase)

## Scope

- IN: Write pytest verification tests for P2 AC
- OUT: Implementing the actual genericization (that is #1286–#1291)