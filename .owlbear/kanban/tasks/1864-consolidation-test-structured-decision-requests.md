---
id: 1864
title: 'consolidation test: structured decision requests'
status: backlog
priority: needed
created: 2026-05-24T21:00:15.672050+02:00
updated: 2026-05-24T21:00:29.588681+02:00
tags:
  - consolidation-test
parent: 1850
depends_on:
  - 1851
  - 1852
  - 1853
  - 1854
  - 1855
  - 1856
  - 1857
  - 1858
  - 1859
  - 1860
  - 1861
  - 1862
  - 1863
ac:
  - 'End-to-end integration: create a decision request via engine, verify it appears
    in Cockpit GET /api/requests/pending response, resolve via POST /api/requests/{id}/resolve
    with selected_option_id, verify task body contains write-back summary and task
    is unblocked.'
  - 'End-to-end integration: create an action request via engine, resolve via Cockpit
    POST with free_text=null (bare Complete), verify task body contains AR write-back
    and task is unblocked.'
  - 'Sweep integration: create a request, manually set resolution fields in pending
    file, trigger pick_tasks, verify sweep moves file to resolved/ and unblocks task.'
proof_bundle: critical
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Cross-layer integration tests: engine → Cockpit API → side effects
- Sweep-to-pick_tasks integration verification
- Conditional unblock with multiple sibling requests scenario
- Verifies the full pipeline works when all layers are composed

**Out of scope:**
- Frontend E2E tests (visual rendering not tested here)
- Individual unit tests (covered by sibling tasks)

## Test scope
`tests/test_cockpit_*` (integration tests using TestClient)