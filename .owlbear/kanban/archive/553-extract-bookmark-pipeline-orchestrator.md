---
id: 553
title: Extract bookmark pipeline orchestrator
status: archived
priority: medium
created: 2026-04-02 16:06:30.320659+02:00
updated: 2026-04-03 06:07:12.042942+02:00
started: 2026-04-03 06:06:30.029075+02:00
completed: 2026-04-03 06:06:30.029075+02:00
tags:
- phase-1
- scope:knowledge
- type:build
depends_on:
- 552
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Extract bookmark_pipeline.py from v1 into the knowledge package. Orchestrates the full bookmark flow: dedup, extract content, evaluate relevance, conditionally ingest, store bookmark.

## Acceptance Criteria

### bookmark_pipeline.py
- [ ] BookmarkResult model (frozen Pydantic BaseModel): url (str), bookmark (Bookmark | None = None), evaluation (EvaluationResult | None = None), ingested (bool = False), skipped_reason (str | None = None)
- [ ] BookmarkPipeline class with __init__(bookmark_store: BookmarkStore, evaluator: SourceEvaluator, ingest_pipeline: IngestPipeline | None = None, web_read_fn: Callable[[str], Awaitable[str | None]] | None = None, ingest_threshold: float = 0.7)
- [ ] async process(url: str, reason: str | None = None, scope: str = global, project_context: dict[str, Any] | None = None, *, cancel: CancelSignal | None = None) returns BookmarkResult
- [ ] Pipeline stages in order: (1) dedup via BookmarkStore.get_by_url(url, scope) returns early with skipped_reason if bookmark exists, (2) content extraction via web_read_fn(url) with broad exception catch returning skipped_reason on failure, (3) evaluate via SourceEvaluator.evaluate(content or empty string, project_context), (4) conditional ingest when: ingest_pipeline is not None AND content is truthy AND evaluation.relevance_score >= ingest_threshold AND evaluation.worth_ingesting -- calls ingest_pipeline.ingest_text(content, metadata={url: url}, scope=scope), (5) create Bookmark with title=evaluation.summary[:120] (fallback to url), description=evaluation.summary, tags=list(evaluation.tags), relevance_score, reason, scope, document_id from ingest result; store via BookmarkStore.create
- [ ] CancelSignal checked between each stage (extract, evaluate, ingest, store); returns partial BookmarkResult with data from completed stages
- [ ] No default web reader implementation inside module; web_read_fn=None means extraction is skipped (no owlbear.web_extract or retry imports)
- [ ] Use existing CancelSignal from cancellation.py, Bookmark/BookmarkStore from bookmark_store.py, SourceEvaluator/EvaluationResult from evaluator.py, IngestPipeline/IngestResult from ingest.py
- [ ] Zero PydanticAI imports

### Package integration
- [ ] __init__.py re-exports: BookmarkPipeline, BookmarkResult added to __all__
- [ ] All tests from test task #552 pass
- [ ] ruff check passes

## Context
Split from #140. v1 source: v1/src/owlbear/memory/knowledge/bookmark_pipeline.py (264 LOC). Depends on test task #552 (TDD RED).

## Exclusions
- No default web reader (web_extract is external; caller provides web_read_fn)
- bookmark_toolset.py is a separate domain (MCP tool registration); separate task when needed

[[2026-04-03]] Fri 02:40
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A (not research-driven, split from #140)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| BookmarkResult model (frozen, 5 fields) | Precise, testable | Keep |
| BookmarkPipeline constructor (5 params, optionals, defaults) | Precise, testable | Keep |
| async process() signature | Precise; note: AC specifies cancel as keyword-only (after *) | Keep |
| Stage 1: dedup via get_by_url(url, scope) | Precise; EXISTING IMPL BUG: calls get_by_url(url) without scope -- builder must fix | Keep |
| Stage 2: content extraction via web_read_fn | Precise, testable | Keep |
| Stage 3: evaluate via SourceEvaluator.evaluate | Precise, testable | Keep |
| Stage 4: conditional ingest (4-condition gate) | Precise; EXISTING IMPL BUG: calls ingest_text(content) without metadata/scope -- builder must fix | Keep |
| Stage 5: create Bookmark with field mapping | Precise; EXISTING IMPL BUG: missing description=evaluation.summary -- builder must fix | Keep |
| CancelSignal checked between stages | Precise, testable | Keep |
| No default web reader | Precise, testable | Keep |
| Use existing modules | Precise, testable | Keep |
| Zero PydanticAI imports | Precise, testable | Keep |
| __init__.py re-exports | Already satisfied | Keep |
| All tests from #552 pass | Testable gate | Keep |
| ruff check passes | Standard gate | Keep |

### Architecture Notes
Module already exists (built during #552's builder phase) but has 3 deviations from AC:
1. get_by_url(url) missing scope param -- AC requires get_by_url(url, scope). This is a correctness bug: bookmarks in non-global scopes would not dedup correctly (BookmarkStore.get_by_url queries WHERE url=? AND scope=?; default scope=global misses other scopes).
2. ingest_text(content) missing metadata and scope -- AC requires ingest_text(content, metadata={url: url}, scope=scope). IngestPipeline.ingest_text accepts these kwargs.
3. Bookmark constructor missing description=evaluation.summary -- AC specifies it; Bookmark model has description field (defaults to None).

Builder expectations:
- Fix all 3 deviations per AC
- Add builder-discovered test assertions for: (a) store.get_by_url called with (url, scope), (b) ingest_text called with content, metadata, scope kwargs, (c) bookmark.description == evaluation.summary
- Verify cancel parameter is keyword-only per AC signature

Patterns to follow: RefreshOrchestrator (refresh.py) for async pipeline with DI and CancelSignal. Frozen Pydantic models (IngestResult, RefreshResult) for result types.

Module layering: bookmark_pipeline.py imports only from within owlbear_knowledge (TYPE_CHECKING for protocols/stores, runtime for Bookmark, EvaluationResult). Correct.

### Changes Made
- Verified AC line-by-line (all pass/fail testable)
- No AC changes needed (already precise)
- status: archived to todo

### Dependencies
- Verified: #552 (test task) at done
- No additional dependencies needed

### Challenge Results
- Challenger: reconsider (confidence 0.72)
- Key challenges: (1) 3 AC deviations have no test coverage from #552 (MagicMock accepts any args), (2) cancel param not keyword-only, (3) stage ordering differs from AC numbering, (4) scope-unaware dedup is correctness bug
- Architect response: Accept challenges 1, 2, 4 as valid observations. Override to APPROVE. The AC already specifies the correct behavior precisely; deviations are implementation bugs, not AC gaps. Builder is contractually bound to AC and expected to add builder-discovered tests. Reviewer (2nd line) independently verifies AC compliance. Challenge 3 (stage ordering): the AC lists document_id from ingest result in bookmark creation -- implementation correctly ingests first to get document_id, which is the only sensible order. Added explicit notes for builder awareness. Confidence in override: .82.

[[2026-04-03]] Fri 03:54
## Test-Writer Notes
- Test file: tests/test_bookmark_pipeline_553.py
- Classes: TestFromAC_DedupeScope, TestFromAC_IngestKwargs, TestFromAC_BookmarkDescription, TestFromAC_CancelKeywordOnly
- Tests per category: happy 4, edge 3, error 2, boundary 3
- Total: 12 tests, all FAIL checked
- ruff: clean
- AC coverage:
  Stage 1 dedup get_by_url(url, scope): test_dedup_called_with_scope_default_global, test_dedup_called_with_custom_scope, test_dedup_scope_not_hardcoded
  Stage 4 ingest_text metadata+scope: test_ingest_text_called_with_url_in_metadata, test_ingest_text_called_with_scope_kwarg_default, test_ingest_text_called_with_custom_scope, test_ingest_text_full_call_signature
  Stage 5 bookmark.description: test_bookmark_description_equals_evaluation_summary, test_bookmark_description_full_not_truncated, test_bookmark_description_not_none
  cancel keyword-only: test_cancel_param_is_keyword_only_in_signature, test_cancel_positional_arg_raises_type_error
- Note: All 4 bugs flagged by architect (dedup scope, ingest kwargs, description field, cancel kwarg-only) now have specific failing tests. Existing #552 tests cover all other AC lines.

[[2026-04-03]] Fri 05:20
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Package already described as 'Knowledge engine (graph + vector)'; no behavior change at project level |
| 2 | Docstrings | Yes | Pass | BookmarkResult, BookmarkPipeline, process(): all have accurate docstrings with Args/Returns |
| 3 | docs/sources/overview.md | No | N/A | Internal v1 extraction; prior external sources (Karakeep, Pinboard, cancellation) already attributed |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/553-* files found)

[[2026-04-03]] Fri 06:06
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| BookmarkResult frozen BaseModel (5 fields) | bookmark_pipeline.py L32-41: ConfigDict(frozen=True), url/bookmark/evaluation/ingested/skipped_reason | PASS |
| BookmarkPipeline constructor (5 params) | L55-73: keyword-only init with store, evaluator, ingest_pipeline, web_read_fn, ingest_threshold=0.7 | PASS |
| async process() signature with cancel kwarg-only | L75-92: cancel after * separator; test_cancel_param_is_keyword_only passes | PASS |
| Stage 1 dedup via get_by_url(url, scope) | L107: self._store.get_by_url(url, scope); 3 tests confirm scope forwarding | PASS |
| Stage 2 content extraction via web_read_fn | L114-122: broad except, returns skipped_reason on failure | PASS |
| Stage 3 evaluate via SourceEvaluator.evaluate | L128-130: evaluate(content, project_context=project_context) | PASS |
| Stage 4 conditional ingest (4-condition gate) | L136-143: pipeline not None AND content AND score >= threshold AND worth_ingesting | PASS |
| Stage 4 ingest_text with metadata and scope kwargs | L149-150: ingest_text(content, metadata=url, scope=scope); 4 tests verify | PASS |
| Stage 5 Bookmark with description=evaluation.summary | L163: description=evaluation.summary; 3 tests verify | PASS |
| CancelSignal checked between stages | L112, L125, L133: three cancel checks | PASS |
| No default web reader | L114: if self._web_read_fn is not None guard | PASS |
| Use existing modules (CancelSignal, Bookmark, etc.) | TYPE_CHECKING imports from cancellation, bookmark_store, evaluator, ingest | PASS |
| Zero PydanticAI imports | No pydantic_ai import in file | PASS |
| __init__.py re-exports BookmarkPipeline, BookmarkResult | Both in __all__ and import line | PASS |
| All tests from #552 pass | 58 passed (46 from #552 + 12 from #553) | PASS |
| ruff check passes | All checks passed | PASS |

### Test Results
- pytest (task-scoped): 58 passed, 0 failed
- pytest (full suite): 232 failures, all from other tasks (quality-runner wiring, rename, voice, etc.); 0 failures in task scope
- ruff: clean

### Upstream Commits
- 63a3f0c test: add failing tests for bookmark pipeline AC deviations (#553, test-writer)
- 790884b fix: bookmark_pipeline dedup scope, ingest kwargs, description, cancel kwarg-only (#553, builder)

### AC Quality (Architect)
Score: 5/5. AC was exceptionally precise: exact signatures, field mappings, stage ordering, 4-condition gate, and identified 3 implementation bugs from #552 builder. No improvisation needed.

### Deduction breakdown
- Missing Review Evidence section in task body: -.02
### Confidence: .98
### Action: archive

## Commits
eb3b39e chore: archive task #553 (kanban board files)
