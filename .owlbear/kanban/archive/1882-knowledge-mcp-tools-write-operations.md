---
id: 1882
title: 'Knowledge: MCP tools — write operations'
status: archived
priority: needed
created: 2026-05-25T19:05:34.718298+02:00
updated: 2026-05-27T01:33:15.459331+02:00
tags:
  - knowledge
  - layer-3
  - research
parent:
depends_on:
  - 1870
  - 1875
  - 1876
  - 1877
  - 1878
ac:
  - Research doc identifies wiring strategy, gap analysis, and sequencing for 
    all MCP write tools
  - 'Follow-up tasks created covering: lifespan expansion, remove_source, register_source,
    get_next_batch, store_enrichment, ingest_document'
  - 'Each follow-up task has correct dependency chain (all depend on lifespan task
    #1888)'
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective

Wire MCP server write tools (ingest, delete_source, register_source, enrichment operations) to the new protocol-conformant implementations.

## Context

- MCP server: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
- Depends on: IngestCoordinator (#1877, #1878), SourceStore (#1870), EnrichmentStore (#1875, #1876)

## Implementation Notes

- knowledge_ingest: accepts batch documents via IngestRequest; delegates to IngestCoordinator.ingest
- knowledge_delete_source: calls IngestCoordinator.delete_source; returns PurgeResult summary
- knowledge_register_source: validates typed SourceConfig discriminated union; calls SourceStore.register_source
- Enrichment tools: claim_batch, submit_extractions, release_claim map directly to EnrichmentStore methods
- Error handling: Pydantic validation errors → MCP error with details; runtime errors → MCP error with message

[[2026-05-27T01:01:16+02:00]]
## Research

Key findings:
- 6 write tools to rewire; 4 have clean protocol targets, 2 (phase-2 consolidation, retry_failed_enrichment) remain on old helpers (protocol gap)
- Dual-table issue: old `knowledge_sources` vs new `source_registry` — resolved by running both table sets via ensure_tables()
- Text hydration gap for enrichment claim: MCP adapter must call ContentStore.get_chunk() after claim_batch()
- AC item `release_claim` has no protocol method — closest is mark_failed() + stale-claim auto-recovery
- Recommended: phased wiring (confidence .82), prioritise clean replacements first

Doc: .owlbear/research/mcp-knowledge-write-ops-wiring.md
Follow-up tasks created: #1888 (lifespan), #1889 (remove_source), #1890 (register_source), #1891 (get_next_batch), #1892 (store_enrichment), #1893 (ingest_document)

[[2026-05-27T01:05:57+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research + decomposition for MCP write tool wiring |
| Interface clarity | PASS | AC rewritten to match research deliverable |
| Dependency correctness | PASS | Deps #1870, #1875–#1878 all archived; follow-ups #1888–#1893 correctly chain |
| Module layering | PASS | N/A (research task) |
| TDD compliance | PASS | Proof bundle: skip (no testable code) |
| KISS/YAGNI | PASS | Phased wiring strategy avoids big-bang risk |
| Premise challenge | PASS | Current MCP server uses raw SQL + old helpers; protocol stores exist and are ready |
| Pattern consistency | PASS | Follows existing MCP server structure |
| Security surface | PASS | No new boundaries in this research task |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Design Diverge
- Trigger: skipped — single valid approach (phased wiring per research)

### Key Decision
Original AC described implementation work now fully decomposed into #1888–#1893. Rewrote AC to match actual deliverable (research strategy + follow-up creation). Tagged `research` for test-writer pass-through. This unblocks #1888 (lifespan expansion) which gates all subsequent wiring tasks.

### Verdict: APPROVE
### Action Taken: AC rewritten to research deliverable, proof_bundle=skip, tagged research, advanced to todo

[[2026-05-27T01:08:19+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Task tagged `research`; deliverable is research doc + follow-up task creation, not testable Python interfaces.
- Passing through to builder.

[[2026-05-27T01:12:05+02:00]]
## Builder Notes
- Proof bundle: skip
- Implementation: no code changes required in builder phase (research pass-through task)
- AC evidence:
  - Research strategy/gap analysis doc exists at `.owlbear/research/mcp-knowledge-write-ops-wiring.md`
  - Follow-up tasks exist: #1888, #1889, #1890, #1891, #1892, #1893
  - Dependency chain validated: #1889-#1893 each depend on #1888
- Tests: not applicable for this task (no implementation scope)
- Coverage: not applicable
- ruff: not applicable
- Approach: validated deliverables against AC, then advanced unchanged to review.

[[2026-05-27T01:28:01+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1882 -> docs | AC mapped to artifacts and evidence sufficient.
- Builder evidence review: sufficient for `proof_bundle=skip`; task is a research deliverable with no executable source changes, so no independent rerun was required.

| AC Line | Artifact Evidence | Status |
|---|---|---|
| Research doc identifies wiring strategy, gap analysis, and sequencing for all MCP write tools | `.owlbear/research/mcp-knowledge-write-ops-wiring.md:23-64` covers current/target architecture, protocol gaps including phase-2, retry_failed_enrichment, and release_claim, plus phased sequencing through ingest_document; follow-up section at `.owlbear/research/mcp-knowledge-write-ops-wiring.md:75-82` matches the recommended sequence. | PASS |
| Follow-up tasks created covering: lifespan expansion, remove_source, register_source, get_next_batch, store_enrichment, ingest_document | Verified task set exists: #1888 lifespan/AppContext, #1889 remove_source, #1890 register_source, #1891 get_next_batch, #1892 store_enrichment phase-1, #1893 ingest_document. Titles and bodies match the follow-up list in the research doc. | PASS |
| Each follow-up task has correct dependency chain (all depend on lifespan task #1888) | Verified dependency graph from task metadata: #1888 depends on parent research task #1882; downstream execution tasks #1889-#1893 each depend on #1888, which is consistent with the documented sequencing where lifespan expansion is the gate for subsequent wiring work. | PASS |

- Blocking findings: none.

## Observations
- AC line 3 is slightly over-literal as written: #1888 is itself the lifespan task, so the concrete graph is `1882 -> 1888 -> {1889,1890,1891,1892,1893}` rather than every follow-up task depending on #1888. The implemented task set matches the apparent intent, so this is non-blocking.
- No test-proof review was required because architecture retargeted the task to a research deliverable and the proof bundle is `skip`.

[[2026-05-27T01:28:57+02:00]]
## Docs Gate

**Convention mapping:** Research-only deliverable. Changed artifacts: `.owlbear/research/mcp-knowledge-write-ops-wiring.md` + kanban tasks #1888–#1893. No `serve/{pkg}/src/**`, `setup/**`, or `share/**` files changed → no READMEs mapped.

| # | Item | Verdict | Evidence |
|---|------|---------|----------|
| 1 | README Verification | N/A | No source file changes; no convention-mapped README targets |
| 2 | External Attribution | N/A | All research doc sources are internal codebase files only |
| 3 | Research Doc | PASS | `.owlbear/research/mcp-knowledge-write-ops-wiring.md` exists and linked from task body (Builder Notes) |
| 4 | Deletion Detection | N/A | No files deleted |

**Files updated:** none
**Scratch cleanup:** no `1882-*` scratch files present

[[2026-05-27T01:33:15+02:00]]
## Audit
### Regression Detection
- No source code changes (research task, proof_bundle=skip); regression testing N/A.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (research doc in .owlbear/research/, follow-ups in kanban, all in knowledge domain)
- purpose match: PASS (doc addresses MCP write operations wiring strategy per task objective)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC rewritten to match actual research deliverable; specific and verifiable lines. Minor literal gap in AC3 noted by reviewer (over-literal phrasing, non-blocking). Good adaptation from original implementation-scope AC to research deliverable.

### Commit Integrity
- upstream commit presence: FAIL (research doc .owlbear/research/mcp-knowledge-write-ops-wiring.md is untracked; never committed by builder)
- Follow-up tasks #1888 to #1893 exist in kanban with correct dependency graph (#1888 gates all downstream)
- Process concern: builder advanced task without committing research doc. File exists on disk.

### Deduction Breakdown
- Uncommitted research doc: -.05 (evidence integrity concern)

### Confidence: .95
### Action: archive
