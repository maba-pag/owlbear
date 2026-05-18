---
id: 1655
title: 'Consolidation test: knowledge source lifecycle'
status: archived
priority: needed
created: 2026-05-18T03:11:28.669033+02:00
updated: 2026-05-18T18:45:42.240606+02:00
tags:
  - scope:knowledge
  - scope:mcp-knowledge
  - consolidation-test
parent: 1650
depends_on:
  - 1651
  - 1654
  - 1652
ac:
  - 'AC-1: Integration test runs against real SQLite + stub vector store; lifecycle
    fixture: source persisted via create(), plus ≥1 document, ≥1 chunk, ≥1 entity
    in DB'
  - 'AC-2: _update_source_record() called twice: first refreshed>0 (bumps both timestamps),
    then skipped>0. Proof: before/after wall-clock window around skipped call; persisted
    last_checked_at (parsed) falls within [before, after] window. last_refreshed_at
    unchanged from refreshed-path value.'
  - 'AC-3: list_sources(ctx) after both refreshes includes all 5 health fields. Proof:
    before/after wall-clock window around skipped call; serialized last_checked_at
    (parsed) falls within [before, after] window. last_refreshed_at retains the earlier
    refreshed-path value.'
  - 'AC-4: remove_source(ctx, source_id) is called; stub delete_embedding invoked
    for each chunk and entity ID; return dict documents, chunks, entities counts each
    > 0 matching pre-removal fixture'
  - 'AC-5: Post-removal: SELECT on documents, chunks, entities, edges, document_status
    for the removed source returns zero rows (no orphans)'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Scope

**In-scope:** Integration verification across O2 refresh honesty (#1651), O1 health exposure (#1654), and O4 remove_source (#1652).

**Out-of-scope:** O3 retype (gated on research outcome in #1653).

[[2026-05-18T18:45:42+02:00]]
## Audit

### Regression Detection
Quality-runner full suite: 4903 passed, 20 failed, 14 skipped, 9 errors. All 20 failures are in unrelated files (test_cockpit_view.py, test_server.py, test_engine_accessor_migration.py, test_graph_store_counts.py) last modified by other tasks — confirmed pre-existing background quality debt. Task changed only serve/mcp-knowledge/tests/test_knowledge_source_lifecycle.py (test-only, no source changes). Lint: clean.

### Intent Verification
Changed file stays within scope:knowledge + scope:mcp-knowledge domain. Purpose is consolidation integration test verifying lifecycle across 3 archived dependency tasks (#1651, #1654, #1652). No extraneous scope.

### Architect Quality
Score: 4/5 — AC-2/AC-3 initially missed the stale-object false-green vulnerability, requiring 3 arch cycles to reach the before/after wall-clock window pattern. Final ACs are specific, provable, and well-grounded in upstream patterns. The iteration was productive and the final product strong.

### Commit Integrity
3 commits, all attributed to test-writer with #1655 reference:
- 187887cf — initial durable consolidation test (472 insertions)
- d1033879 — first AC-2/AC-3 strengthening attempt
- c870716a — final wall-clock window pattern implementation

Builder had no source changes (pass-through for consolidation-test), consistent with task scope.

### Deduction Breakdown
No deductions. Background failures separated per scoped analysis.

### Confidence: 1.00
### Action: Archive

### Process Note
Kanban file lost uncommitted pipeline state during git stash conflict — task restored from audit evidence and re-archived.
