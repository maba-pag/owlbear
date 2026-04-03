---
id: 555
title: Extract refresh orchestrator
status: todo
priority: nice-to-have
created: 2026-04-02T16:07:24.5297504+02:00
updated: 2026-04-03T06:54:49.4404265+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:build
depends_on:
    - 554
class: standard
---

## Objective
Extract refresh.py from v1 into the knowledge package. Dispatches source refresh operations by SourceType (url_list, crawl, file_glob), collecting per-item ingest results.

## Acceptance Criteria

### refresh.py
- [ ] RefreshResult model (frozen Pydantic BaseModel): source_id (str), refreshed (int), skipped (int), failed (int), errors (list[str] = [])
- [ ] CrawlHandler type alias at module level: Callable[..., Awaitable[list[IngestResult]]]
- [ ] RefreshOrchestrator class with __init__(store: KnowledgeSourceStore, pipeline: IngestPipeline, crawl_handler: CrawlHandler | None = None, workspace_root: Path | None = None)
- [ ] workspace_root defaults to Path.cwd() when None
- [ ] async refresh(source: KnowledgeSource, *, cancel: CancelSignal | None = None) returns RefreshResult; raises ValueError if source.enabled is False; dispatches to handler by source.source_type
- [ ] async refresh_all(scope: str | None = None, *, cancel: CancelSignal | None = None) returns list[RefreshResult]; gets sources via KnowledgeSourceStore.list_all(scope) then filters enabled=True (no list_enabled method exists); iterates by priority descending; stops on cancel
- [ ] Handler url_list: reads config[urls] list; for each URL creates IntakeResult via intake.read_url(url) then calls pipeline.ingest(intake_result, scope=source.scope); per-item exception caught, counted as failed
- [ ] Handler crawl: delegates to crawl_handler(config); raises ValueError if crawl_handler is None; counts refreshed/skipped from IngestResult.status field
- [ ] Handler file_glob: resolves config[pattern] under config[base_dir] (validated via _paths.sandbox_path) or workspace_root; validates each glob result with _paths.sandbox_path; for valid paths creates IntakeResult via intake.read_file(path, workspace_root=workspace_root) then calls pipeline.ingest; sandbox PermissionError counted as failure (not raised)
- [ ] _update_source_record: persists refresh outcome via store.update(source.model_copy(update={last_refreshed_at: now_iso, last_error: error_summary or None, updated_at: now_iso}))
- [ ] CancelSignal checked between items in ingest loop and between sources in refresh_all
- [ ] IngestResult.status == skipped counted as skipped; status == ok counted as refreshed
- [ ] Use existing SourceType/KnowledgeSource from models.py, sandbox_path from _paths.py, CancelSignal from cancellation.py, IngestPipeline/IngestResult from ingest.py, intake.read_url/intake.read_file from intake.py, KnowledgeSourceStore from source_store.py
- [ ] Zero PydanticAI imports

### Package integration
- [ ] __init__.py re-exports: RefreshOrchestrator, RefreshResult added to __all__
- [ ] All tests from test task #554 pass
- [ ] ruff check passes

## Context
Split from #140. v1 source: v1/src/owlbear/memory/knowledge/refresh.py (331 LOC). Depends on test task #554 (TDD RED).

## v2 Adaptation Notes
- KnowledgeSourceStore has list_all(scope) not list_enabled(scope): filter enabled=True in refresh_all
- IngestPipeline.ingest(intake_result: IntakeResult) takes IntakeResult not str: use intake.read_url/read_file to create IntakeResult before calling pipeline.ingest
- IngestResult.status is Literal[ok,failed,skipped,cancelled]: check status field, not a .skipped property

[[2026-04-03]] Fri 05:46
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- not research-driven (split from #140, no research doc reference)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| RefreshResult model (frozen, all fields) | Precise: types, defaults, frozen constraint all specified | Keep |
| CrawlHandler type alias Callable[..., Awaitable[list[IngestResult]]] | Clear, matches v1 intent | Keep |
| RefreshOrchestrator.__init__(store, pipeline, crawl_handler, workspace_root) | All params typed, optional defaults specified | Keep |
| workspace_root defaults to Path.cwd() when None | Verifiable | Keep |
| refresh() ValueError if disabled, dispatch by source_type | Clear contract with 3 dispatch targets | Keep |
| refresh_all() list_all + filter + priority desc + cancel | Correctly uses list_all (v2 adaptation), filter/sort/cancel all specified | Keep |
| url_list: intake.read_url then pipeline.ingest(intake_result, scope=source.scope) | Scope forwarding explicitly required -- critical for multi-scope isolation | Keep |
| crawl: crawl_handler(config), ValueError if None | Matches v1 pattern, config dict not full source | Keep |
| file_glob: sandbox_path + intake.read_file + pipeline.ingest | Scope forwarding missing (see Architecture Notes) | Note |
| _update_source_record: store.update with timestamps | Clear persistence contract | Keep |
| CancelSignal between items and sources | Two cancellation checkpoints specified | Keep |
| IngestResult status counting (ok=refreshed, skipped=skipped) | Verifiable counting rules | Keep |
| __init__.py re-exports | RefreshOrchestrator, RefreshResult in __all__ | Keep |
| All tests from #554 pass, ruff clean | Standard gates | Keep |

### Architecture Notes
Interfaces verified in codebase:
- SourceType (models.py): URL_LIST, CRAWL, FILE_GLOB
- KnowledgeSourceStore.list_all(scope) (source_store.py line 100)
- IngestPipeline.ingest(intake: IntakeResult, scope=global) (ingest.py line 127)
- IntakeResult (intake.py), intake.read_url, intake.read_file
- sandbox_path (paths.py), CancelSignal Protocol (cancellation.py)

**Builder notes:**
1. file_glob handler AC omits scope=source.scope on pipeline.ingest. Follow the url_list pattern: pass scope=source.scope to pipeline.ingest in all handlers.
2. crawl_handler receives config dict (source.config), not the full KnowledgeSource.
3. An implementation already exists from #554 pipeline. It has discrepancies vs this AC (missing scope forwarding, passes source instead of config to crawl handler). Implement from AC, not from existing code.
4. refresh_all should continue on per-source exceptions (log and skip), not abort.

**Deliberate v2 simplifications:**
- v1 _supports_cancel_kwarg introspection removed. IngestPipeline uses constructor-injected cancel_signal. Crawl handler manages own cancellation.
- _update_source_record records errors whenever any exist (v1 only recorded when ALL items failed). This is a better UX for partial failures.

### Changes Made
- Approved: AC is precise, architecture sound, all interfaces verified
- No AC modifications needed (minor scope gap noted for builder)

### Dependencies
- Verified: #554 (test) at done status
- No additional dependencies needed

### Challenge Results
- Challenger: block (confidence: .45)
- Key challenges: scope forwarding gap in file_glob AC, crawl handler source-vs-config mismatch, cancel propagation to crawl handler
- Architect response: Rebutted. Scope forwarding IS specified in url_list AC (line 7) and gap in file_glob noted for builder. Crawl handler arg correctly specified as config in AC (line 8). Cancel simplification is deliberate v2 design. Challenger concerns target existing implementation discrepancies, not AC quality.
- Confidence in original: .88

[[2026-04-03]] Fri 06:31
## Test-Writer Notes
- Test file: tests/test_refresh_555.py
- Classes: TestFromAC_UrlListScopeForwarding, TestFromAC_CrawlHandlerReceivesConfig
- Total: 2 tests, all FAIL (AssertionError) OK
- ruff: clean
- Gap 1: url_list must call pipeline.ingest(intake_result, scope=source.scope). Current impl omits scope kwarg.
- Gap 2: crawl handler must receive source.config dict, not the full KnowledgeSource. Current impl passes source.

[[2026-04-03]] Fri 06:44
## Builder Notes
- Files changed: packages/knowledge/src/owlbear_knowledge/refresh.py
- Tests: 44 passed (test_refresh_555.py + test_refresh_orchestrator.py), 100% coverage on refresh.py
- Lint: ruff clean
- Evidence: 2 TestFromAC tests went RED then GREEN
- Fixes applied: (1) pipeline.ingest now receives scope=source.scope in url_list handler; (2) crawl_handler now receives source.config dict instead of full KnowledgeSource
