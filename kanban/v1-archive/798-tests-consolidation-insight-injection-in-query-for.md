---
id: 798
title: 'Tests: consolidation insight injection in query_for_context (#790)'
status: archived
priority: nice-to-have
created: 2026-03-14T03:00:48.7859795+01:00
updated: 2026-03-14T12:09:21.7313414+01:00
started: 2026-03-14T12:09:02.55103+01:00
completed: 2026-03-14T12:09:02.55103+01:00
tags:
    - scope:core
    - memory
    - knowledge
    - type:test
depends_on:
    - 790
class: standard
---

## Goal

RED-phase tests for #790: consolidation insight injection in KnowledgeQueryService.query_for_context().

## AC

- [ ] Test file: tests/test_knowledge_query_service_consolidation.py
- [ ] Uses TestFromAC_ class naming per convention
- [ ] Tests consolidation_conn=None skips insight query (no regression)
- [ ] Tests consolidation_conn with rows appends insights after RAG output
- [ ] Tests insights respect max_tokens budget (budget exhausted by RAG = no insights)
- [ ] Tests partial insight truncation at word boundary
- [ ] Tests empty consolidations table = output unchanged
- [ ] Tests consolidation query exception caught + logged (graceful degradation)
- [ ] Tests insight format: header + bullets
- [ ] Tests bootstrap wiring: consolidation_enabled=True passes conn, False passes None
- [ ] All tests FAIL before #790 implementation (RED phase)
- [ ] Ruff clean

## Pattern references

- tests/test_knowledge_query_service.py (fixture patterns: mock_vector_store, mock_graph_store, mock_embedding_provider)
- tests/test_consolidation.py (consolidation table setup patterns)

## Dependencies

- #790 (impl task)

[[2026-03-14]] Sat 04:05

## Test-Writer Notes

- Test file: tests/test_knowledge_query_service_consolidation.py (ALREADY EXISTS)
- Written in commit 21239ae for task #800 (same AC)
- Classes: TestFromAC_ConsolidationConnNone, TestFromAC_InsightsAppendedAfterRAG, TestFromAC_TokenBudget, TestFromAC_EmptyTable, TestFromAC_ExceptionHandling, TestFromAC_InsightFormat, TestFromAC_BootstrapWiring
- Tests per category: happy 4, edge 2, error 3, boundary 3, config 3, format 4
- Total: 19 tests, all covered by existing file
- Implementation (#790) already complete; tests PASS (19/19)
- ruff: clean
- Duplicate work  identical test file already committed.

[[2026-03-14]] Sat

## Builder Notes

- Non-implementation task: tests and implementation already exist
- Test file committed in 21239ae for #800, impl from #790
- Tests: 19/19 passed (7 TestFromAC classes)
- Lint: ruff clean
- No code changes needed (duplicate task)

-t

[[2026-03-14]] Sat 11:05

## Review Evidence

See docs/scratch/798-reviewer.md for full evidence.

[[2026-03-14]] Sat 11:26

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only task, no behavior change. ConsolidationService already documented. |
| 2 | Docstrings | No | N/A | No source code changed. Test file only. |
| 3 | sources/overview.md | No | N/A | No external patterns adopted. |
| 4 | README.md | No | N/A | No CLI changes. |
| 5 | Research doc | No | N/A | No research phase for this test task. |
| 6 | No impact | Yes | Pass | Test-only duplicate task (#800 archived). No docs impact. |

### Files Updated

- None

### Scratch Files Cleaned

- Deleted docs/scratch/798-reviewer.md

[[2026-03-14]] Sat 12:08

## Audit

### AC Verification

| AC | Evidence | Status |
|-----|----------|--------|
| 1. Test file exists | tests/test_knowledge_query_service_consolidation.py (373 lines, 19 tests) | PASS |
| 2. TestFromAC_ naming | 7 classes: ConsolidationConnNone, InsightsAppendedAfterRAG, TokenBudget, EmptyTable, ExceptionHandling, InsightFormat, BootstrapWiring | PASS |
| 3. conn=None skips | 2 tests: no insight section + matches baseline | PASS |
| 4. Rows append after RAG | 2 tests: insight_pos > rag_pos + RAG content present | PASS |
| 5. Token budget respected | 3 tests: within budget, exhausted=no insights, partial truncation | PASS |
| 6. Partial truncation at word boundary | test_partial_insights_truncated_at_word_boundary (L163) | PASS |
| 7. Empty table unchanged | 2 tests: no insight header + matches None-conn output | PASS |
| 8. Exception caught+logged | 3 tests: RAG still returned, WARNING logged, no insight section | PASS |
| 9. Insight format header+bullets | 4 tests: header, bullets, text in bullets, max 3 | PASS |
| 10. Bootstrap wiring | 3 tests: enabled=conn, disabled=None, default=None | PASS |
| 11. RED phase | Duplicate task (tests from #800 commit 21239ae); original RED confirmed | PASS |
| 12. Ruff clean | All checks passed! | PASS |

### Test Results

- Task-scoped: 19/19 passed
- Full suite: 3346 passed, 34 failed (pre-existing: inter_doc_pipeline, expansion wiring, role policies)
- Ruff: clean

### Commits Verified

- 21239ae: test: add failing tests for consolidation insight injection (#800, test-writer)
- Note: duplicate task, all work attributed to #800

### Confidence: .96

### Action: archive
