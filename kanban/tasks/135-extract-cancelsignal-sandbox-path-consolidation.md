---
id: 135
title: Extract CancelSignal, sandbox_path, consolidation, and evaluator into knowledge package
status: backlog
priority: nice-to-have
created: 2026-03-29T12:07:28.9585653+02:00
updated: 2026-03-29T16:14:41.4817144+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 143
class: standard
---

## Objective
Extract Group A modules from v1 that have no IngestPipeline dependency into packages/knowledge/.

## Acceptance Criteria
- [ ] `packages/knowledge/src/owlbear_knowledge/cancellation.py` contains:
  - `CancelSignal` -- `@runtime_checkable` Protocol with `is_set() -> bool`
  - `LinkedCancelSignal` -- composes `*sources: CancelSignal`, `is_set()` returns True when any source is set
- [ ] `packages/knowledge/src/owlbear_knowledge/_paths.py` contains:
  - `sandbox_path(root: Path, user_path: str | Path) -> Path` -- resolves user_path against root, raises PermissionError on null bytes or traversal outside root
  - Private module: NOT exported from `__init__.py`
- [ ] `packages/knowledge/src/owlbear_knowledge/consolidation.py` contains:
  - `TextCompletionFn = Callable[[str], Awaitable[str]]` type alias
  - `ConsolidationService.__init__(self, conn: sqlite3.Connection, llm_fn: TextCompletionFn)` -- no PydanticAI dependency
  - `consolidate(self, batch_size: int = 50) -> int` async -- reads unconsolidated chunks, calls llm_fn with concatenated content, stores insight in consolidations table, marks chunks consolidated=1, returns insight count (0 on empty or LLM failure)
  - `schedule_periodic(self, interval: int = 3600) -> None` async -- loop calling consolidate()
- [ ] `packages/knowledge/src/owlbear_knowledge/evaluator.py` contains:
  - `EvaluationResult` Pydantic model (frozen): relevance_score (0.0-1.0), tags (list[str]), summary (str), worth_ingesting (bool)
  - `EvaluateFn = Callable[[str], Awaitable[EvaluationResult]]` type alias
  - `SourceEvaluator.__init__(self, llm_fn: EvaluateFn)` -- no PydanticAI Agent, no UsageTracker
  - `evaluate(self, content: str, project_context: dict | None) -> EvaluationResult` async -- empty content returns score 0.0, None context returns neutral (no LLM call), valid input calls llm_fn, LLM exception returns neutral fallback
  - `_build_prompt`, `_default_result`, `MAX_CONTENT_LENGTH`, `EVALUATION_PROMPT` preserved from v1
- [ ] `__init__.py` adds to `__all__`: CancelSignal, LinkedCancelSignal, ConsolidationService, EvaluationResult, SourceEvaluator
- [ ] No PydanticAI imports in any extracted module
- [ ] All TDD RED tests from #143 pass (GREEN)
- [ ] `ruff check` clean on new files

## Architecture Notes
- LLM injection: async callable type aliases per module (TextCompletionFn, EvaluateFn). No shared _types.py -- YAGNI.
- CancelSignal: use v1 Protocol-args variant (not asyncio.Event variant). Matches v2 Protocol-first style.
- sandbox_path: copy v1 verbatim. Private module (_paths.py), not re-exported.
- Follow existing v2 patterns: Pydantic models with frozen ConfigDict, from __future__ import annotations.

## Context
Split from #130 (Group A -- no #33 dependency). See docs/research/extract-knowledge-secondary-features.md S3 and docs/research/extract-cancel-sandbox-consolidation-evaluator.md.

[[2026-03-29]] Sun 16:14
## Architecture Review
**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Extract CancelSignal + LinkedCancelSignal | Source verified (29 LOC), v1 Protocol-args variant is correct | Refined: specified @runtime_checkable, is_set signature |
| Extract sandbox_path | Source verified (14 LOC), pure copy | Refined: clarified private module, NOT in __init__.__all__ |
| Extract ConsolidationService with LLM injection | Vague -- missing target file, type alias, constructor sig | Refined: specified TextCompletionFn alias, constructor params, consolidate/schedule_periodic signatures |
| Extract SourceEvaluator + EvaluationResult | Vague -- missing type alias, what to drop/keep | Refined: specified EvaluateFn alias, EvaluationResult fields, preserved helpers, dropped UsageTracker |
| Unit tests for all extracted modules | Bundled with impl -- violates TDD | Split: created #143 (TDD RED test task), impl depends on #143 |
| Update __init__.py exports | Missing which names | Refined: explicit list of 5 exports |

### Architecture Notes
Existing v2 patterns verified:
- Protocol-first style (VectorStoreProtocol, EmbeddingProvider) -- CancelSignal fits
- Pydantic models with frozen ConfigDict -- EvaluationResult fits
- No PydanticAI in knowledge package -- async callable injection is KISS-compliant
- Schema v8 already has consolidations table + chunks.consolidated column
- No new dependencies needed in pyproject.toml

### Changes Made
- Created #143: Test: Extract CancelSignal, sandbox_path, consolidation, and evaluator (TDD RED)
- Rewrote #135 body with precise AC (target files, signatures, type aliases, exports)
- Added depends_on: #143

### Dependencies
- Added: #143 (TDD RED test task) -- must complete before #135
- Verified: No #33 dependency (Group A modules are IngestPipeline-free)
- Verified: Knowledge package infrastructure exists (schema v8, stores, __init__.py)
