---
id: 539
title: Add null safety and fix __all__ in mcp-knowledge server
status: archived
priority: medium
created: 2026-04-02 05:59:31.026470+02:00
updated: 2026-04-02 15:48:51.141734+02:00
started: 2026-04-02 15:48:44.723558+02:00
completed: 2026-04-02 15:48:44.723558+02:00
tags:
- scope:mcp
- type:build
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## AC
- [ ] list_sources: if app_ctx.source_store is None, early-return "error: source store not available". Update return type annotation to list[dict[str, str]] | str
- [ ] list_entities: if app_ctx.graph_store is None, early-return "error: graph store not available" before entity_type validation. Return type already list[dict[str, Any]] | str
- [ ] get_stats: if app_ctx.graph_store is None, early-return "error: graph store not available". Update return type annotation to dict[str, int] | str
- [ ] ingest_document: if app_ctx.ingest_pipeline is None, early-return "error: ingest pipeline not available" before the try block. Existing try/except remains for runtime ingest failures. (Changes error message for None case from "error: ingestion failed: ..." to explicit message)
- [ ] Add "get_stats" to __all__ list in server.py (alphabetical order)
- [ ] Tests: for each of the 4 null-safety tools, add a test in packages/mcp-knowledge/tests/ that mocks AppContext with the relevant field as None and asserts the correct error string. Follow mock pattern in test_ingest_graph_tools.py (_make_app_context + _make_mcp_ctx) or test_list_sources.py (_make_ctx)

## Context
See docs/research/mcp-server-error-return-standardization.md S3a
AppContext types all fields as T | None but only search_knowledge checks.
Pattern: follow search_knowledge existing None-check guard in server.py.
File: packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
Out of scope: knowledge_stats/knowledge_stats_resource helpers (not MCP tools); search_knowledge error message format (pre-existing inconsistency).

[[2026-04-02]] Thu 07:41
## Architecture Review
**Verdict:** Approve
**DR Verification:** N/A -- T1 autonomous (research doc classifies as consistency refactor, no design decisions)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| list_sources None check | Clear, follows search_knowledge pattern. Return type needs union with str. | Approved as refined |
| list_entities None check | Clear, return type already includes str union. Guard before entity_type validation. | Approved as refined |
| get_stats None check | Clear, return type needs union with str. | Approved as refined |
| ingest_document None check | Clear. Explicit None guard before try block. Behavioral note: changes error message for None case. | Approved as refined |
| get_stats in __all__ | Verifiable, single missing export. | Approved |
| Tests for null-safety | Refined to specify mock pattern (test_ingest_graph_tools.py, test_list_sources.py), not test_search_knowledge.py. | Approved as refined |

### Architecture Notes
Single file change in packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py. Follows established null-safety pattern from search_knowledge (early return with "error: " prefix). AppContext dataclass intentionally types fields as T | None; defensive guards at MCP tool boundary are correct.

knowledge_stats() and knowledge_stats_resource() are helper functions, not MCP tools -- out of scope. search_knowledge error message format ("Knowledge service not available." with capital/period) is a pre-existing inconsistency, not in scope for this task.

### Changes Made
- Refined AC: added return type annotation requirements, specified mock pattern reference, noted ingest_document behavioral change
- Replaced vague test AC with specific mock pattern references

### Dependencies
- None. Task is self-contained within mcp-knowledge package.

### Challenge Results
- Challenger: reconsider (confidence 0.72)
- Key challenges: C1 error message format inconsistency with search_knowledge (accepted, noted as pre-existing out of scope); C4 wrong test mock reference (accepted, fixed in refined AC); C5 unguarded helpers (rebutted, not MCP tools)
- Architect response: Accepted C1/C4 (refined AC accordingly). Rebutted C5 (helpers out of scope). Rebutted "narrow types" alternative (scope creep, different design decision). Confidence in verdict maintained.

[[2026-04-02]] Thu 10:37
## Test-Writer Notes
- Test file: packages/mcp-knowledge/tests/test_null_safety_539.py
- Classes: TestFromAC_NullSafetyGuards, TestFromAC_DunderAll
- Tests per category: happy 0, edge 2, error 4, boundary 2
- Total: 8 tests, all FAIL (7 FAILED + previously-passing sorted test replaced with position test)
- ruff: clean
- AC coverage:
  - list_sources None check: test_list_sources_returns_error_when_source_store_is_none (error)
  - list_entities None check: test_list_entities_returns_error_when_graph_store_is_none (error)
  - list_entities check before validation: test_list_entities_null_check_fires_before_entity_type_validation (edge)
  - get_stats None check: test_get_stats_returns_error_when_graph_store_is_none (error)
  - ingest_document None check: test_ingest_document_returns_error_when_ingest_pipeline_is_none (error)
  - ingest_document error string distinct: test_ingest_document_pipeline_none_does_not_return_ingestion_failed (edge)
  - get_stats in __all__: test_get_stats_is_in_dunder_all (boundary)
  - alphabetical order: test_get_stats_is_before_ingest_document_in_dunder_all (boundary)

[[2026-04-02]] Thu 10:51
## Builder Notes\n- Files changed: packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py\n- Tests: 8 passed, coverage 46% on server.py\n- Lint: ruff clean\n- Evidence: 8/8 TestFromAC tests GREEN; RED confirmed before implementation\n- Fixes applied: None

[[2026-04-02]] Thu 12:13
## Review Evidence
See docs/scratch/539-reviewer.md for full evidence.

[[2026-04-02]] Thu 14:43
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal consistency fix; null-safety guards follow pre-existing MCP error conventions |
| 2 | Docstrings complete | Yes | Pass | All 4 modified tools have docstrings (list_sources, list_entities, get_stats, ingest_document) |
| 3 | sources/overview.md | No | N/A | Internal pattern reuse; no external repos or articles |
| 4 | README.md | No | N/A | No CLI commands changed |
| 5 | Research doc linked | Yes | Pass | docs/research/mcp-server-error-return-standardization.md exists and referenced in task Context |
### Files Updated
- None
### Scratch Files Cleaned
- docs/scratch/539-reviewer.md referenced in Review Evidence but does not exist -- nothing to delete
