---
id: 1897
title: 'Knowledge: MCP server v2-only migration (Phase B)'
status: archived
priority: needed
created: 2026-05-27T16:19:48.281533+02:00
updated: 2026-05-27T18:03:49.057978+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on:
  - 1896
ac:
  - AppContext contains only new v2 store fields
  - _consolidation.py deleted; logic migrated to EnrichmentStore
  - No dual-path legacy fallbacks remain in MCP tools
  - All MCP knowledge tests pass
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Remove all legacy components from MCP server AppContext. Wire all tools exclusively to new protocol stores.

## Changes required
- Remove AppContext fields: query_service, graph_store (old), ingest_pipeline, source_store (old), refresh_orchestrator, intra_doc_builder
- Remove dual-path in search_knowledge (delete query_service fallback)
- Migrate _consolidation.py logic into EnrichmentStore (phase-2 candidates)
- Remove init_db() call to old schema.py; new stores use ensure_tables()
- Update all MCP tool functions to use only v2 store APIs
- Delete _consolidation.py after migration

## Verification
- Full MCP test suite passes
- search_knowledge works without query_service
- store_enrichment phase-2 works via EnrichmentStore
- No imports from legacy knowledge modules remain in mcp-knowledge package

## Research
See .owlbear/research/knowledge-legacy-deletion.md §3.3, §3.1

[[2026-05-27T17:56:35+02:00]]
## Research

Key findings:
- All legacy AppContext fields have v2 replacements ready: query_facade (search), graph_store_v2 (graph), ingest_coordinator (refresh/ingest), source_store_v2 (sources)
- EnrichmentStore already accepts GraphStore Protocol — SqliteGraphStore is a drop-in replacement
- Consolidation migration (~540 LOC) requires moving helpers from mcp-knowledge _helpers.py into knowledge package to avoid reverse dependency
- `reviewed_pairs` DDL must move from legacy schema.py to EnrichmentStore.ensure_tables()
- Recommended two sub-phases: B1 (consolidation migration) then B2 (server cleanup) to reduce blast radius

Trade-off matrix: see .owlbear/research/mcp-knowledge-v2-migration.md §3
Follow-up tasks: #1899 (B1 consolidation migration), #1900 (B2 server v2-only)
Confidence: 0.85

[[2026-05-27T18:01:08+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | FAIL | Spans two distinct sub-phases: consolidation migration (B1) + server cleanup (B2) |
| Interface clarity | PASS | AC lines are specific and testable |
| Dependency correctness | FAIL (fixed) | #1899/#1900 incorrectly depended on this parent; corrected to #1900→#1899 only |
| Module layering | PASS | Changes stay within knowledge/mcp-knowledge domain |
| TDD compliance | N/A | Decomposed, not implemented directly |
| KISS/YAGNI | PASS | Research recommends 2-phase split to reduce blast radius |
| Premise challenge | PASS | v2 stores are ready; legacy removal is warranted |
| Pattern consistency | PASS | Follows established v2 migration pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Knowledge domain only |

### Design Diverge
- Skipped: single valid approach (decompose into B1 + B2), no alternatives

### Challenge Results
- Challenger: SKIPPED — task decomposed, no approval to challenge

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: N/A (decomposed)
- Test-writer: N/A

### Dependency Fix
- Removed #1897 from deps of #1899 (was circular — sub-task depending on parent)
- Removed #1897 from deps of #1900 (kept #1899 dep for sequential B1→B2 ordering)
- #1899 now has no deps (predecessor #1896 already archived)
- #1900 depends on [#1899] only

### Verdict: SPLIT
### Action Taken: Task spans two responsibilities (consolidation migration + server v2-only cleanup). Sub-tasks #1899 (B1) and #1900 (B2) already created by researcher with proper AC. Fixed inverted dependency structure. Archiving as decomposed → [#1899, #1900].

[[2026-05-27T18:03:49+02:00]]
## Audit
### Regression Detection
- No code changed (decomposition task); quality-runner not invoked
- Regression verdict: N/A (no changed_paths)

### Intent Verification
- Scope alignment: PASS (sub-tasks #1899 B1 + #1900 B2 together cover full original scope)
- Purpose match: PASS (v2-only migration decomposed into consolidation-first then server-cleanup)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
Good split decision. Correctly identified dual-responsibility, fixed inverted dependency structure, transferred AC to sub-tasks with proper research references.

### Commit Integrity
- Upstream commit presence: PARTIAL (research doc mcp-knowledge-v2-migration.md untracked; researcher should have committed before advancing. Process concern noted, not blocking.)
- Kanban commit packaging: pending (this archival)

### Deduction Breakdown
No applicable deductions: no code regressions (no code), no intent mismatch, no evidence concerns, no lint, AC quality 4/5 (above threshold), architect SPLIT verdict serves as review for decomposed task.

### Confidence: 1.00
### Action: archive
### Process Note
Research doc .owlbear/research/mcp-knowledge-v2-migration.md remains uncommitted. Researcher should commit deliverables before advancing.
