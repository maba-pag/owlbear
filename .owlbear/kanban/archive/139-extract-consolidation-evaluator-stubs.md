---
id: 139
title: Extract consolidation + evaluator stubs
status: archived
priority: medium
created: 2026-03-29 14:51:25.933119+02:00
updated: 2026-03-30 07:31:05.319189+02:00
started: 2026-03-29 14:51:55.863175+02:00
completed: 2026-03-30 07:30:17.425600+02:00
tags:
- phase-1
- ' scope:knowledge'
- ' type:build'
depends_on:
- 138
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
GREEN phase: extract consolidation service and source evaluator as stub modules following the extractor.py pattern.

## Acceptance Criteria

### packages/knowledge/src/owlbear_knowledge/consolidation.py
- [ ] ConsolidationInsight model (frozen Pydantic BaseModel): id (str), source_ids (list[str]), insight (str), created_at (str)
- [ ] ConsolidationService class with __init__(conn: sqlite3.Connection, graph_store: GraphStore | None = None, model: str | object = None)
- [ ] async consolidate(batch_size: int = 50) returns 0 (no-op stub, no LLM call)
- [ ] Zero PydanticAI imports
- [ ] Follows extractor.py stub pattern: schema + no-op implementation, docstring notes real LLM wired at application layer

### packages/knowledge/src/owlbear_knowledge/evaluator.py
- [ ] EvaluationResult model (frozen Pydantic BaseModel): relevance_score (float, ge=0.0, le=1.0), tags (list[str], default_factory=list), summary (str, default=""), worth_ingesting (bool, default=False)
- [ ] EVALUATION_PROMPT constant preserved from v1 for future LLM integration
- [ ] SourceEvaluator class with __init__(model: str | object = None)
- [ ] async evaluate(content: str, project_context: dict | None = None) returns EvaluationResult:
  - Empty/blank content returns relevance_score=0.0, worth_ingesting=False
  - project_context=None returns neutral fallback (relevance_score=0.5)
  - Otherwise returns neutral fallback (no LLM call in stub)
- [ ] Zero PydanticAI imports
- [ ] Follows extractor.py stub pattern

### Package integration
- [ ] __init__.py re-exports: ConsolidationService, ConsolidationInsight, SourceEvaluator, EvaluationResult
- [ ] All RED-phase tests from test task pass (GREEN)
- [ ] ruff check passes on new modules
- [ ] uv pip install -e packages/knowledge/ succeeds

## Architecture Notes
Pattern reference: packages/knowledge/src/owlbear_knowledge/extractor.py — schema models + no-op stub, zero PydanticAI deps. The _run_llm() internal from v1 consolidation.py and the Agent calls from v1 evaluator.py are replaced by stub returns.

## Context
Part of #130 split. Depends on test task #138.

[[2026-03-29]] Sun 16:12
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| ConsolidationInsight model (frozen, 4 fields) | Precise, verifiable. Intentionally omits DB summary/scope columns (stub phase). | Keep |
| ConsolidationService.__init__ signature | Optional params match stub pattern (v1 required them). Consistent with extractor.py. | Keep |
| consolidate() returns 0 no-op | Clear, testable. | Keep |
| Zero PydanticAI imports (consolidation) | Binary check. | Keep |
| Follows extractor.py stub pattern (consolidation) | Verifiable by comparison. | Keep |
| EvaluationResult model (frozen, 4 constrained fields) | Matches v1 exactly (ge/le, defaults). Precise. | Keep |
| EVALUATION_PROMPT preserved from v1 | v1 source exists at v1/src/owlbear/memory/knowledge/evaluator.py. Builder can reference. | Keep |
| SourceEvaluator.__init__(model optional) | Drops v1 tracker/provider (YAGNI). Good. | Keep |
| evaluate() three behaviors (empty/no-context/default) | Each has specific expected return values. Testable. | Keep |
| Zero PydanticAI imports (evaluator) | Binary check. | Keep |
| Follows extractor.py stub pattern (evaluator) | Verifiable by comparison. | Keep |
| __init__.py re-exports 4 symbols | Explicit list. Note: extractor.py exports are not in __init__.py currently, creating asymmetry. Non-blocking. | Keep |
| RED-phase tests pass (GREEN) | Testable via pytest. | Keep |
| ruff check passes | Testable. | Keep |
| uv pip install succeeds | Testable. | Keep |

### Architecture Notes
- **Pattern reference confirmed:** extractor.py (50 LOC) establishes the stub pattern: frozen Pydantic models, no-op async methods, zero PydanticAI, str | object type hint for model param. Both new modules follow this exactly.
- **and in title evaluated:** consolidation + evaluator are both knowledge-domain stub extractions from the same v1 migration (#130), same pattern, ~50 LOC each. Splitting into 4 tasks (2 test + 2 impl) for ~100 LOC total would violate KISS. Keeping together is justified.
- **DB schema note:** ConsolidationInsight omits summary and scope columns from the consolidations table. Acceptable for stub phase; model can be expanded when real implementation is wired.
- **v1 sources available:** v1/src/owlbear/memory/knowledge/evaluator.py (166 LOC) and consolidation.py (114 LOC) exist in workspace for builder reference.
- **Module layering:** Both are leaf modules in owlbear_knowledge. GraphStore type hint in consolidation constructor should use TYPE_CHECKING import (follows existing pattern in extractor.py).
- **__init__.py asymmetry:** extractor.py exports (ExtractionResult, EntityExtractor) are not in __init__.py. The AC adds consolidation/evaluator exports but not extractor. Non-blocking; separate concern.

### Dependencies
- Verified: #138 (test task) exists in backlog, correct TDD ordering via depends_on
- No missing dependencies identified
- No circular dependency risk (leaf modules)

### Failure Mode Map
N/A - no-op stubs with no external I/O or failure-prone codepaths.

[[2026-03-30]] Mon 05:38
## Test-Writer Notes
- Test file: tests/test_knowledge_consolidation_evaluator_init.py
- Classes: TestFromAC_PackageInit, TestFromAC_EvaluationPrompt, TestFromAC_EvaluatorBlankContent, TestFromAC_EvaluationResultDefaults
- Tests per category: happy 5, edge 2, error 2, boundary 2
- Total: 11 tests, all FAIL
- ruff: clean
- AC coverage:
  - __init__.py re-exports 4 symbols -> test_consolidation_service_importable_from_package, test_consolidation_insight_importable_from_package, test_source_evaluator_importable_from_package, test_evaluation_result_importable_from_package, test_all_exports_listed_in_dunder_all (happy)
  - EVALUATION_PROMPT constant preserved -> test_evaluation_prompt_constant_exists, test_evaluation_prompt_is_non_empty_string (happy)
  - blank/whitespace content returns 0.0 -> test_evaluate_spaces_only_returns_zero_score, test_evaluate_newline_tab_returns_zero_score (edge)
  - EvaluationResult.summary default='' -> test_summary_defaults_to_empty_string, test_all_defaults_applied_when_only_score_given (boundary)

[[2026-03-30]] Mon 06:42
## Builder Notes
- Files changed: evaluator.py (added EVALUATION_PROMPT, fixed summary default, fixed blank-content strip check), __init__.py (added 4 re-exports + __all__ entries), consolidation.py (line endings only)
- Tests: 44 passed (11 from this task + 33 from #138 test files)
- Coverage: consolidation.py 100%, evaluator.py 100%, __init__.py 100%
- Lint: ruff clean
- Fixes applied: EVALUATION_PROMPT constant added from v1; EvaluationResult.summary default changed from required to empty string; blank/whitespace content check uses content.strip(); package re-exports added for all 4 symbols

[[2026-03-30]] Mon 07:11
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal leaf modules; no behavior or API change |
| 2 | Docstrings complete | Yes | Pass | consolidation.py + evaluator.py + __init__.py all have accurate module/class/method docstrings |
| 3 | docs/sources/overview.md | No | N/A | v1 sources already in Task #143 section; no new external patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc; AC references extractor.py (internal) |
| 6 | Scratch files | None | Pass | No docs/scratch/139-* found |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-30]] Mon 07:31
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a74ce15 | chore | kanban/tasks/139-*.md | #139 |
