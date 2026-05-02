---
id: 1281
title: 'P1-01: Test — system instruction neutrality and init.py scaffold verification'
status: research
priority: critical
created: 2026-05-02T16:01:10.581833+00:00
updated: 2026-05-02T16:02:06.188964+00:00
tags:
- phase-1
- scope:test
- shared-layer
parent: 1280
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] Pytest test file exists that verifies P1 completion conditions
- [ ] Test asserts `grep -r 'serve/' share/instructions/` returns zero hits (excluding MCP server name mentions like `mcp-kanban`)
- [ ] Test asserts `.github/copilot-instructions.md` contains a Directory Structure section
- [ ] Test asserts `setup/init.py` generates a copilot-instructions.md with path-mapping scaffold section
- [ ] Test asserts no dangling cross-references from share/README.md or share/WIRING.md to removed content
- [ ] All tests fail initially (RED phase — implementation not yet done)

## Scope

- IN: Write pytest verification tests for P1 AC
- OUT: Implementing the actual file changes (that is #1282–#1284)