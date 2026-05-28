---
id: 1911
title: 'Knowledge: Wire SourceFetcher in MCP server and replace refresh handler'
status: in-progress
priority: needed
created: 2026-05-28T01:41:45.877792+02:00
updated: 2026-05-28T05:04:52.799015+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent: 1904
depends_on:
  - 1909
  - 1910
ac:
  - 'AC1: app_lifespan constructs CompositeSourceFetcher(workspace_root=Path.cwd(),
    content_fetcher_factory=select_content_fetcher) and passes it as fetcher= to IngestCoordinator
    constructor'
  - 'AC2: knowledge_sources_refresh calls ingest_coordinator.refresh(RefreshRequest(source_ids=(source_id,)))
    and returns a dict with keys source_id (str, echoed input), sources_refreshed
    (int from RefreshResult), and errors (list of dicts each with source_id, error,
    timestamp keys from RefreshError)'
  - 'AC3: AppContext dataclass has no refresh_orchestrator field and no source_store
    field'
  - 'AC4: server.py contains no imports of KnowledgeSourceStore, RefreshOrchestrator,
    or IngestPipeline (including TYPE_CHECKING blocks)'
  - 'AC5: knowledge_sources_refresh raises ToolError when source_store_v2.get_source(source_id)
    returns None; returns error dict when source.state is not SourceState.ACTIVE'
  - 'AC6: All MCP knowledge tests pass after updating tests/test_mcp_knowledge_legacy_removal_1900.py
    B2b-retention assertions (source_store, refresh_orchestrator) to assert absence'
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Wire CompositeSourceFetcher in the MCP server lifespan and replace the refresh handler to use IngestCoordinator.

## Details
- In `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` app_lifespan:
  - Create CompositeSourceFetcher(workspace_root=Path.cwd(), content_fetcher_factory=select_content_fetcher)
  - Pass fetcher= to IngestCoordinator constructor
- Replace knowledge_sources_refresh handler body:
  - Validate source exists via source_store_v2.get_source(source_id), raise ToolError if not found
  - Check source.state is ACTIVE, return error if not
  - Call ingest_coordinator.refresh(RefreshRequest(source_ids=(source_id,)))
  - Map RefreshResult to response dict
- Remove refresh_orchestrator and source_store fields from AppContext
- Remove legacy imports (KnowledgeSourceStore, RefreshOrchestrator, IngestPipeline, select_content_fetcher usage in handler)
- Depends on: #1909 (CompositeSourceFetcher) and #1910 (error propagation)
- Research: .owlbear/research/source-fetcher-adapter-b2b.md §3.4

[[2026-05-28T04:59:10+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single logical change: wire fetcher + replace handler + remove legacy fields |
| Interface clarity | PASS | After refinement — AC1-AC6 name exact constructors, method calls, response keys, and error observables |
| Dependency correctness | PASS | #1909 (archived), #1910 (archived) — both completed |
| Module layering | PASS | All within mcp-knowledge package consuming owlbear_knowledge public APIs; no upward imports |
| TDD compliance | PASS | Test-writer creates tests at todo |
| KISS/YAGNI | PASS | Minimal wiring + deletion. Deletion test: removing the fetcher wiring means IngestCoordinator.refresh() returns empty results (no-op) — feature is broken |
| Premise challenge | PASS | CompositeSourceFetcher built in #1909 exists for this exact purpose. IngestCoordinator already accepts fetcher=. Current handler uses None fields that never work |
| Pattern consistency | PASS | Follows knowledge_sources_delete pattern (source_store_v2.get_source → validate → coordinator call → serialize result) |
| Security surface | PASS | No new system boundaries. Validation tightens (ACTIVE check added) |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| source_store_v2.get_source() | Source not found | ToolError | Yes (AC5) | Clear error to agent |
| source.state check | Non-ACTIVE source | Error dict return | Yes (AC5) | Informative error |
| ingest_coordinator.refresh() | Fetcher returns item errors | RefreshResult.errors | Yes (via #1910) | Partial results reported in response |
| CompositeSourceFetcher.fetch_source() | Network/IO failure | FetchError (never raises) | Yes (#1909 AC7) | Captured in errors list |

### Design Diverge
- Trigger: skipped — single clear approach, no competing designs. CompositeSourceFetcher → IngestCoordinator → handler is the only viable wiring path.

### Challenge Results
- Challenger: reconsider (0.34)
- Findings: (1) false-green no-fetcher path — ACCEPTED, split AC1 to require explicit fetcher= wiring proof; (2) test baseline conflict with #1900 retention assertions — ACCEPTED, added AC6 requiring test updates; (3) handler-level proof gap — ACCEPTED, AC2 now requires handler-level test with response shape; (4) consolidation-test gap — REBUTTED: #1911 IS the integration point, its handler tests exercise the full wiring path; (5) AC quality — ACCEPTED, refined all AC lines for named targets and observables
- Architect response: accepted 4 of 6 findings, refined AC1→AC6 to address all valid concerns

### Proof-Bundle Validation
- Planner assignment: null
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED
- Rationale: Core fetcher behavior proven in #1909 (behavioral), error propagation proven in #1910 (smoke). This task is wiring + structural removal. Handler-level smoke tests verify correct integration without re-proving lower-layer logic.

### Verdict: APPROVE
### Action Taken: Refined AC from 5 to 6 lines addressing challenger false-green and test-conflict findings. Set proof_bundle=smoke. Advanced to todo.

[[2026-05-28T05:04:52+02:00]]
## Test-Writer Notes
- Test file: tests/test_mcp_knowledge_server_1911.py
- Classes: TestFromAC_SourceFetcherWiring
- Tests per category: happy (smoke) 6, edge 0, error 0, boundary 0
- Total: 6 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Test | Failure reason |
|----|------|----------------|
| AC1 | test_app_lifespan_constructs_composite_fetcher_wired_to_coordinator | CompositeSourceFetcher not in lifespan source |
| AC2 | test_refresh_handler_returns_response_with_expected_keys | ToolError "source store not available" (old path) |
| AC3 | test_appcontext_has_no_source_store_or_refresh_orchestrator | refresh_orchestrator still in AppContext |
| AC4 | test_server_py_has_no_legacy_class_imports | KnowledgeSourceStore still imported |
| AC5 | test_refresh_raises_toolerror_when_source_not_found | ToolError message "source store not available" doesn't match "not found" |
| AC6 | test_legacy_removal_1900_b2b_tests_assert_absence_not_presence | 1900 test file still has retention assertions |
