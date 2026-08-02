---
id: 523
title: Wire LLM callable injection into ConsolidationService and SourceEvaluator
status: archived
priority: medium
created: 2026-04-01 15:27:37.967271+02:00
updated: 2026-04-02 22:22:02.274762+02:00
started: 2026-04-02 22:21:59.456745+02:00
completed: 2026-04-02 22:21:59.456745+02:00
tags:
- phase-1
- scope:knowledge
- type:build
depends_on:
- 135
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Upgrade ConsolidationService and SourceEvaluator from no-op stubs to LLM-injectable implementations using async callable type aliases defined by #135.

## Acceptance Criteria

### ConsolidationService (consolidation.py)
- [ ] Constructor: `__init__(self, conn: sqlite3.Connection, llm_fn: TextCompletionFn)` -- `graph_store`, `model` params removed; no `_agent` field
- [ ] `consolidate(batch_size=50) -> int`:
  - Queries `SELECT id, content FROM chunks WHERE consolidated = 0 ORDER BY rowid LIMIT ?`
  - No rows: returns 0
  - Builds prompt: `"Chunk {idx+1}: {content}"` per chunk, joined by `\n\n` (v1 L76 pattern)
  - Calls `await llm_fn(prompt)`
  - Success: inserts into consolidations (id=uuid4, source_ids=JSON array of chunk IDs, insight=LLM output, created_at=UTC ISO); updates matching chunks `consolidated=1`; commits; returns 1
  - `llm_fn` exception: catches broadly (`except Exception`), logs `logger.warning(..., exc_info=True)`, returns 0
  - Note: schema columns `summary` and `scope` intentionally left NULL -- matches v1 parity; scope-aware consolidation is a follow-up concern
- [ ] `schedule_periodic(interval=3600) -> None`: async infinite loop calling `consolidate()`, sleeps `interval` seconds. Re-raises `asyncio.CancelledError`; catches + logs other exceptions (`exc_info=True`) and continues next cycle
- [ ] New stdlib imports: `asyncio`, `json`, `uuid`, `datetime` (UTC), `logging`. No PydanticAI.

### SourceEvaluator (evaluator.py)
- [ ] Constructor: `__init__(self, llm_fn: EvaluateFn)` -- `model` param removed; no `_agent`/tracker/provider fields
- [ ] `evaluate(content: str, project_context: dict | None = None) -> EvaluationResult`:
  - Empty/whitespace content: returns `EvaluationResult(relevance_score=0.0, tags=[], summary="Empty content -- nothing to evaluate.", worth_ingesting=False)` -- no LLM call
  - `project_context is None`: returns `_default_result()` -- no LLM call
  - Valid content + project_context: calls `_build_prompt(content, project_context)`, then `await llm_fn(prompt)`, returns result. On exception: `logger.warning(..., exc_info=True)` and returns `EvaluationResult(relevance_score=0.5, tags=[], summary="Evaluation failed -- returning neutral score.", worth_ingesting=False)`
- [ ] Module-level `MAX_CONTENT_LENGTH = 2000`
- [ ] Module-level `_build_prompt(content, project_context) -> str` -- truncates content to MAX_CONTENT_LENGTH chars, formats as `## Project Context\n{name/desc/goals}\n\n## Content Excerpt\n{excerpt}` per v1 L79-87
- [ ] Module-level `_default_result() -> EvaluationResult` -- returns `EvaluationResult(relevance_score=0.5, tags=[], summary="No project context available -- neutral evaluation.", worth_ingesting=True)` per v1 L62-69
- [ ] `EVALUATION_PROMPT` constant: already present, unchanged
- [ ] No PydanticAI imports, no UsageTracker, no record_agent_usage

### General
- [ ] No PydanticAI imports in any modified file
- [ ] `uv run pytest tests/test_consolidation.py tests/test_evaluator.py -q` -- all pass
- [ ] `uv run ruff check packages/knowledge/src/owlbear_knowledge/consolidation.py packages/knowledge/src/owlbear_knowledge/evaluator.py` -- clean

## Architecture Notes
- Type aliases `TextCompletionFn` and `EvaluateFn` already defined in their modules by #135
- Constructor migration is a breaking change: all existing tests in test_consolidation.py (~10) and test_evaluator.py (~8) use old signatures and must be updated by test-writer to use AsyncMock for llm_fn
- `llm_fn` is intentionally REQUIRED (not optional with None default) -- explicit wiring over implicit stub behavior
- `EvaluateFn = Callable[[str], Awaitable[EvaluationResult]]` takes a single prompt string. The service builds the prompt internally via `_build_prompt()` -- callers of `evaluate()` still pass `(content, project_context)` through the public API
- DB consolidations table has `summary` and `scope` columns not used by this task -- matches v1 behavior. Scope-aware consolidation is a separate concern (YAGNI)
- `ConsolidationInsight` model does NOT include `summary`/`scope` fields -- it represents the service output, not a full DB row
- Downstream: #136 BookmarkPipeline receives `evaluator: SourceEvaluator` as a pre-constructed instance, so constructor changes here do not directly break #136 code. However, #136 tests that construct SourceEvaluator directly will need the new signature. Functional evaluator (this task) is needed before #136's ingest_threshold=0.7 works in practice.
- Follow v1 patterns: consolidation.py L60-114, evaluator.py L100-166

## Context
Follow-up from #135 (extraction). LLM injection was descoped from #135 because #138 built stubs with different constructors. See docs/research/extract-cancel-sandbox-consolidation-evaluator.md for the research recommending callable injection.

[[2026-04-02]] Thu 00:36
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** N/A -- T1 implementation task; research was for parent #135

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| ConsolidationService constructor (conn, llm_fn) | Clear, testable, removes unused graph_store/model | Refined: added prompt format, return value semantics, exception logging |
| consolidate() reads/calls/stores/marks/returns | v1 L60-114 pattern. Return ambiguous ("insight count" vs 0-or-1) | Refined: "returns 1 on success, 0 on failure". Schema summary/scope NULL documented |
| schedule_periodic(interval=3600) | Matches v1 exactly | Refined: added CancelledError re-raise, exc_info=True logging |
| SourceEvaluator constructor (llm_fn) | Clear, testable | Refined: explicit no tracker/provider |
| evaluate() three paths | Matches v1. Missing project_context=None path | Refined: explicit _default_result() path for project_context=None |
| _build_prompt, _default_result, MAX_CONTENT_LENGTH | Vague "preserved from v1" | Refined: full signatures, return values, v1 line refs |
| Tests updated | Breaks TDD model (bundling test changes with impl) | Refined: removed -- test-writer handles test updates in RED phase |
| No PydanticAI imports | Clear | Kept |
| All tests pass, ruff clean | Clear | Kept |

### Architecture Notes
Single domain (knowledge package, memory layer). Both modules in packages/knowledge/src/owlbear_knowledge/. Module layering clean -- no upward imports. Pattern follows v1 with PydanticAI Agent replaced by typed callables (Protocol-first v2 style). EvaluateFn single-string signature correct: service builds prompt internally via _build_prompt(). graph_store only used in tests (grep verified) -- safe to remove. DB consolidations.summary/scope left NULL per v1 parity. llm_fn REQUIRED for explicit wiring. Downstream #136 receives pre-constructed SourceEvaluator instance -- not broken by constructor change.

### Changes Made
- Rewrote task body with refined AC (3 sections, 17 verifiable sub-criteria)
- Specified consolidate() prompt format (v1 "Chunk N:" pattern)
- Specified consolidate() return semantics (1 on success, 0 on failure)
- Added explicit evaluate() path for project_context=None
- Added full _build_prompt, _default_result, MAX_CONTENT_LENGTH specs
- Removed "tests updated" AC line (test-writer handles RED phase)
- Documented schema summary/scope NULL decision
- Documented EvaluateFn single-string calling convention

### Dependencies
- Verified: #135 (done) -- type aliases TextCompletionFn and EvaluateFn exist in modules
- Downstream: #136 (todo) -- receives pre-constructed SourceEvaluator, not directly broken

### Challenge Results
- Challenger: reconsider (6 challenges, 5 blind spots)
- Confidence in original: .70
- Key challenges: (1) EvaluateFn signature vs evaluate() API (2) consolidations.summary/scope unused (3) #136 missing depends_on (4) breaking change scope (5) return value ambiguity (6) type alias exports
- Architect response: revised AC. (1) EvaluateFn correct -- service builds prompt internally, documented. (2) summary/scope NULL per v1, documented. (3) #136 receives pre-constructed instance, not broken. (4) Breaking change intentional, test-writer handles. (5) Return clarified 1/0. (6) Type aliases stay in submodules.

[[2026-04-02]] Thu 02:05
## Test-Writer Notes
- Test files: tests/test_consolidation.py, tests/test_evaluator.py
- Classes: TestFromAC_ConsolidationService, TestFromAC_ConsolidationService_SchedulePeriodic, TestFromAC_SourceEvaluator, TestFromAC_SourceEvaluatorModuleFunctions
- Tests per category: happy 13, edge 6, error 8, boundary 5
- Total: 46 new tests, all FAIL; 20 pre-existing schema tests preserved (still pass)
- ruff: clean
- AC coverage: all 17 ConsolidationService AC lines mapped; all SourceEvaluator constructor, evaluate() paths (empty/none-context/valid/exception), and module-level helpers (MAX_CONTENT_LENGTH, _build_prompt, _default_result)

[[2026-04-02]] Thu 04:47
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal API change (constructor signatures); high-level knowledge package description needs no update |
| 2 | Docstrings complete | Yes | Pass | consolidation.py: module, ConsolidationInsight, ConsolidationService, consolidate(), schedule_periodic() -- all accurate. evaluator.py: module, EvaluationResult, _default_result(), _build_prompt(), SourceEvaluator, evaluate() -- all accurate including all three evaluate() paths |
| 3 | docs/sources/overview.md | No | N/A | v1 consolidation.py and evaluator.py patterns already documented (lines 582-583, task 143 research). No new external sources used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/extract-cancel-sandbox-consolidation-evaluator.md exists; linked from task body Context section |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/523-* files found)

[[2026-04-02]] Thu 22:21
## Audit
### AC Verification (spot-check, 3rd-line)
All 17+ AC sub-criteria verified by code inspection:

**ConsolidationService** (consolidation.py):
- Constructor(conn, llm_fn): L48-50 PASS
- consolidate(batch_size=50) returns int: L52 PASS
- SQL query matches AC: L59-62 PASS
- Prompt format Chunk N: L67-69 PASS
- await llm_fn(prompt): L72 PASS
- Success path (uuid4, JSON source_ids, UTC ISO, commit, return 1): L77-90 PASS
- Exception handling (broad catch, warning, exc_info, return 0): L73-75 PASS
- No rows returns 0: L64-65 PASS
- schedule_periodic(interval=3600): L92-103 PASS
- CancelledError re-raise: L99-100 PASS
- Imports (asyncio, json, uuid, datetime UTC, logging): L10-16 PASS
- summary/scope NULL (not in INSERT): L82-84 PASS

**SourceEvaluator** (evaluator.py):
- Constructor(llm_fn: EvaluateFn): L95 PASS
- No model/_agent/tracker/provider: PASS
- evaluate() empty/whitespace path: L107-112 PASS
- evaluate() project_context=None path: L114-115 PASS
- evaluate() valid path with _build_prompt: L117-119 PASS
- evaluate() exception handling (warning, exc_info, neutral result): L120-126 PASS
- MAX_CONTENT_LENGTH = 2000: L16 PASS
- _build_prompt truncation and format: L75-85 PASS
- _default_result values: L66-72 PASS
- EVALUATION_PROMPT constant: L18 PASS
- No PydanticAI imports: PASS (grep verified)

### Test Results
- pytest (task-scoped): 66 passed, 0 failed
- pytest (full suite): 2937 passed, 376 failed (all failures in other tasks' RED-phase tests)
- ruff: All checks passed

### Upstream Commits
- dd50309 test: add failing tests for LLM callable injection (#523, test-writer)
- 2354c51 feat: wire LLM callable injection (#523, builder)

### AC Quality Score: 5/5
AC was exceptionally specific (exact signatures, SQL, prompt format, return values, exception patterns, v1 line refs). Edge cases covered. Design direction productive.

### Deduction breakdown
- Start: 1.00
- Missing Review Evidence section in task body: -.02
- All other criteria clean (tests pass, ruff clean, AC quality 5)

### Confidence: .98
### Action: archive
