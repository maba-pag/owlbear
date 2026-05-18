---
id: 1673
title: 'Consolidation test: Cockpit Memory Tab'
status: backlog
priority: needed
created: 2026-05-18T17:44:22.449391+02:00
updated: 2026-05-18T17:44:26.786279+02:00
tags:
  - consolidation-test
  - scope:memory
  - scope:cockpit
parent: 1659
depends_on:
  - 1667
  - 1668
  - 1669
  - 1670
  - 1671
  - 1672
ac:
  - 'Integration test verifies end-to-end flow: create memory entry via engine, fetch
    via GET /api/memories, approve via POST, edit (approved→curated downgrade), delete
    (soft-delete); asserts correct HTTP status codes and state transitions throughout'
  - All 6 sibling implementation tasks (#1667–#1672) pass their individual test 
    suites; no regressions in serve/mcp-memory/tests/ or tests/test_cockpit_* 
    suites
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1659

## Scope

End-to-end integration verification that the Memory engine extraction, MCP rewiring, cockpit API, and frontend component work together correctly.

### In Scope
- Integration test covering engine → cockpit API → response chain
- Regression verification across all sibling task test suites
- Cross-package import verification (owlbear-memory used by both mcp-memory and cockpit)

### Out of Scope
- Individual unit tests (covered by sibling tasks)
- Performance testing
- E2E browser tests (frontend tasks carry their own component tests)