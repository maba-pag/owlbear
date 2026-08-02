---
id: 138
title: 'Test: Extract consolidation + evaluator stubs'
status: archived
priority: medium
created: 2026-03-29 14:51:11.332447+02:00
updated: 2026-03-30 04:53:08.547412+02:00
started: 2026-03-29 14:51:55.810237+02:00
completed: 2026-03-30 04:52:29.564444+02:00
tags:
- phase-1
- ' scope:knowledge'
- ' type:test'
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
RED phase: write failing tests for consolidation service and source evaluator stub extraction.

## Acceptance Criteria

### tests/test_consolidation.py
- [ ] ConsolidationService(conn) instantiates with sqlite3.Connection; optional graph_store and model params
- [ ] await consolidate(batch_size=50) returns 0 when no unconsolidated chunks exist
- [ ] ConsolidationInsight model validates required fields: id (str), source_ids (list[str]), insight (str), created_at (str)
- [ ] ConsolidationInsight is frozen (ConfigDict(frozen=True))

### tests/test_evaluator.py
- [ ] SourceEvaluator() instantiates with optional model parameter
- [ ] await evaluate(content='test', project_context=None) returns EvaluationResult with relevance_score=0.5, worth_ingesting=False (neutral fallback, no LLM)
- [ ] await evaluate(content='', project_context=None) returns EvaluationResult with relevance_score=0.0, worth_ingesting=False (empty content)
- [ ] await evaluate(content='test', project_context={'name': 'proj'}) returns EvaluationResult with relevance_score=0.5, worth_ingesting=False (stub neutral, no LLM call)
- [ ] EvaluationResult model validates: relevance_score (float, 0.0-1.0), tags (list[str]), summary (str), worth_ingesting (bool)
- [ ] EvaluationResult is frozen (ConfigDict(frozen=True))
- [ ] Default EvaluationResult().worth_ingesting is False

### Verification
- [ ] All tests fail (RED, modules not implemented yet)
- [ ] ruff check passes on test files

## Architecture Notes
Follow extractor.py stub pattern (packages/knowledge/src/owlbear_knowledge/extractor.py). Both modules become schema + no-op stubs with zero PydanticAI imports. Real LLM wiring happens at the application layer. Both consolidate() and evaluate() are async methods; tests must use pytest-asyncio (async def test_...).

## Context
Part of #130 split. v1 sources: v1/src/owlbear/memory/knowledge/consolidation.py (114 LOC), v1/src/owlbear/memory/knowledge/evaluator.py (166 LOC).

[[2026-03-29]] Sun 16:14
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| ConsolidationService(conn) instantiates | Precise signature, matches extractor.py pattern | Keep |
| await consolidate(batch_size=50) returns 0 | Async explicit, testable return value | Keep |
| ConsolidationInsight validates 4 fields | All types specified, verifiable | Keep |
| ConsolidationInsight is frozen | Binary check | Keep |
| SourceEvaluator() optional model | Matches stub pattern, YAGNI (no tracker) | Keep |
| await evaluate neutral fallback (0.5, worth_ingesting=False) | Explicit on both fields, removes v1 ambiguity | Refined |
| await evaluate empty content (0.0, worth_ingesting=False) | Clear, testable | Keep |
| await evaluate with-context stub (0.5, worth_ingesting=False) | Added: covers third codepath in stub | Added |
| EvaluationResult validates 4 constrained fields | ge/le, defaults explicit | Keep |
| EvaluationResult is frozen | Binary check | Keep |
| Default worth_ingesting is False | Confirms model default | Keep |
| All tests fail (RED) | Standard RED phase gate | Keep |
| ruff check passes | Standard quality gate | Keep |

### Architecture Notes
- **Pattern consistency confirmed:** extractor.py establishes the stub test pattern. Both new test files follow same import-and-verify approach as test_knowledge_engine_extraction.py.
- **Async explicit in AC:** Added 'await' prefix and pytest-asyncio note in Architecture Notes since both consolidate() and evaluate() are async per #139 AC. Prevents test-writer from writing sync tests.
- **worth_ingesting disambiguation:** v1 neutral fallback returned worth_ingesting=True (optimistic), but v2 stub model default is False. Aligned test AC to False since stub has no LLM to justify optimistic ingestion. Consistent with #139 model definition (default=False).
- **Third evaluate path added:** #139 specifies 3 evaluate behaviors (empty, None context, with context). Original AC only tested 2. Added with-context test to cover stub neutral return for all non-empty paths.
- **Module layering:** Tests import from owlbear_knowledge.consolidation and owlbear_knowledge.evaluator (leaf modules, no layering concern).

### Changes Made
- Refined AC: added await prefix to async method tests
- Refined AC: added explicit worth_ingesting=False to neutral fallback test
- Added AC line: evaluate with non-None project_context (third codepath)
- Added Architecture Notes: pytest-asyncio requirement for async tests

### Dependencies
- Verified: #139 depends_on #138 (correct TDD ordering)
- No other dependencies needed (test-only task)

[[2026-03-29]] Sun 18:59
## Test-Writer Notes
- Test files: tests/test_consolidation.py, tests/test_evaluator.py
- Classes: TestFromAC_ConsolidationService, TestFromAC_ConsolidationInsight, TestFromAC_SourceEvaluator, TestFromAC_EvaluationResult
- Tests per category: happy 18, edge 2, error 5, boundary 8
- Total: 33 tests, all FAIL (ModuleNotFoundError - modules not yet implemented) âœ“
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| ConsolidationService(conn) instantiates | test_instantiates_with_sqlite_connection | happy |
| optional graph_store param | test_accepts_optional_graph_store_param | happy |
| optional model param | test_accepts_optional_model_param | happy |
| await consolidate(batch_size=50) returns 0 | test_consolidate_returns_zero_when_no_chunks | happy |
| ConsolidationInsight required fields | test_instantiates_with_required_fields, test_id_field_is_required, test_source_ids_field_is_required, test_insight_field_is_required, test_created_at_field_is_required | happy, error |
| ConsolidationInsight is frozen | test_is_frozen_cannot_mutate_id, test_is_frozen_cannot_mutate_insight | boundary |
| SourceEvaluator() optional model | test_instantiates_with_no_args, test_instantiates_with_model_param | happy |
| evaluate neutral fallback (0.5, False) | test_evaluate_neutral_fallback_no_llm | happy |
| evaluate empty content (0.0, False) | test_evaluate_empty_content_returns_zero_score | edge |
| evaluate with project_context (0.5, False) | test_evaluate_with_project_context_returns_stub_neutral | happy |
| EvaluationResult relevance_score float 0-1 | test_relevance_score_must_be_float, test_relevance_score_below_zero_is_invalid, test_relevance_score_above_one_is_invalid, test_relevance_score_boundary_zero_is_valid, test_relevance_score_boundary_one_is_valid | error, boundary |
| EvaluationResult tags list[str] | test_tags_is_list_of_str | happy |
| EvaluationResult summary str | test_summary_is_str | happy |
| EvaluationResult worth_ingesting bool | test_worth_ingesting_is_bool | happy |
| EvaluationResult is frozen | test_is_frozen_cannot_mutate_relevance_score, test_is_frozen_cannot_mutate_worth_ingesting | boundary |
| Default worth_ingesting is False | test_default_worth_ingesting_is_false | boundary |

[[2026-03-29]] Sun 21:06
## Builder Notes
- Files changed: packages/knowledge/src/owlbear_knowledge/consolidation.py (new), packages/knowledge/src/owlbear_knowledge/evaluator.py (new)
- Tests: 33 passed, coverage 100% on both modules
- Lint: ruff clean
- Evidence: 33 passed in 0.22s; consolidation.py 16 stmts 0 missed; evaluator.py 15 stmts 0 missed
- Fixes applied: moved sqlite3 import to TYPE_CHECKING block; replaced Any with object; added noqa ARG002 for intentionally unused stub params (batch_size, project_context)

[[2026-03-30]] Mon 03:39
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Stub modules add no behavior or convention change |
| 2 | Docstrings | Yes | Pass | consolidation.py and evaluator.py both have full module, class, and method docstrings |
| 3 | docs/sources/overview.md | No | N/A | v1/consolidation.py and v1/evaluator.py already in sources table from prior entries |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No new research doc produced (research was from task 135) |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-30]] Mon 04:53
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3264edc | chore | kanban/tasks/138-*.md, activity.jsonl | #138 |
