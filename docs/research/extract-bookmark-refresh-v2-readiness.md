# Extract bookmark pipeline + refresh orchestrator — v2 readiness

> **Owning task:** #140 — Extract bookmark pipeline + refresh orchestrator
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Task #140 asks to extract `bookmark_pipeline.py` (264 LOC) and `refresh.py` (331 LOC)
from v1 into `packages/knowledge/`. Dependencies #33, #139, and #158 are all archived.
The question: are all v2 interfaces ready, and what API adaptations are needed?

Secondary finding: #136 covers identical core scope with architect-reviewed AC. This
doc merges the research into #136 and archives #140.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | v1 bookmark_pipeline.py | `v1/src/owlbear/memory/knowledge/bookmark_pipeline.py` | 1.0 |
| 2 | v1 refresh.py | `v1/src/owlbear/memory/knowledge/refresh.py` | 1.0 |
| 3 | v2 knowledge package | `packages/knowledge/src/owlbear_knowledge/` | 1.0 |
| 4 | Task #136 (architect-reviewed) | kanban task with tightened AC | 1.0 |
| 5 | Task #158 (intake + ingest pipeline) | archived — defined v2 IngestPipeline API | 0.9 |
| 6 | extract-knowledge-engine-v1.md | `docs/research/extract-knowledge-engine-v1.md` | 0.8 |
| 7 | bookmark-pipeline-extract-content.md | `docs/research/bookmark-pipeline-extract-content.md` | 0.7 |

## 3. Analysis

### 3.1 v2 Dependency Readiness

All required v2 modules exist and are functional:

| v1 Import | v2 Equivalent | Status |
|-----------|---------------|--------|
| `bookmark.Bookmark` | `bookmark_store.Bookmark` | Exists |
| `bookmark.BookmarkStore` | `bookmark_store.BookmarkStore` | Exists |
| `evaluator.SourceEvaluator` | `evaluator.SourceEvaluator` | Exists (stub) |
| `evaluator.EvaluationResult` | `evaluator.EvaluationResult` | Exists |
| `cancellation.CancelSignal` | `cancellation.CancelSignal` | Exists |
| `ingest.IngestPipeline` | `ingest.IngestPipeline` | Exists |
| `ingest.IngestResult` | `ingest.IngestResult` | Exists |
| `models.SourceType` | `models.SourceType` | Exists |
| `models.KnowledgeSource` | `models.KnowledgeSource` | Exists |
| `source_store.KnowledgeSourceStore` | `source_store.KnowledgeSourceStore` | Exists |
| `owlbear.paths.sandbox_path` | `_paths.sandbox_path` | Exists |

### 3.2 API Mismatches Requiring Adaptation

**A. IngestPipeline.ingest() signature change**

v1 `refresh.py` calls `self._pipeline.ingest(item)` where `item` is a `str` (URL or
file path). v2's `IngestPipeline.ingest()` takes an `IntakeResult`, not a string.

The v2 RefreshOrchestrator must construct IntakeResult before calling ingest:
- URL items: `await intake.read_url(url)` then `pipeline.ingest(result)`
- File items: `await intake.read_file(path, workspace_root=...)` then `pipeline.ingest(result)`
- Crawl items: handler already returns IngestResults

**B. IngestResult.skipped property absent**

v1 uses `result.skipped` as a boolean property. v2 `IngestResult` has
`status: Literal["ok", "failed", "skipped", "cancelled"]` — no `.skipped` attribute.
Adapt to `result.status == "skipped"`.

**C. KnowledgeSourceStore.list_enabled() missing**

v1 `refresh_all()` calls `self._store.list_enabled(scope)`. v2 only has `list_all(scope)`.
Must add `list_enabled(scope)` returning enabled sources ordered by priority DESC.
(Already captured in #136 AC.)

**D. _default_web_read removal**

v1's `_default_web_read` uses `owlbear.web_extract.extract_markdown` and
`owlbear.core.retry.TRANSIENT_RETRY` — both v1-only dependencies. Per #136's AC,
`web_read_fn` becomes REQUIRED (no default). Correct decision: knowledge package
should not own HTTP fetching.

**E. _supports_cancel_kwarg duplication**

Both v1 files contain identical `_supports_cancel_kwarg` static methods. DRY: extract
to `cancellation.py` as a module-level utility alongside CancelSignal. Minor, builder
can decide placement.

### 3.3 Task #136 vs #140 Overlap

| Aspect | #136 (todo) | #140 (ideation) |
|--------|-------------|-----------------|
| Core scope | BookmarkPipeline + RefreshOrchestrator | Same |
| MCP tools | Included (bookmark_source, list_bookmarks) | Explicitly excluded |
| list_enabled() | Included in AC | Not in AC |
| __init__.py exports | Included | Not in AC |
| Architect review | Done (tightened AC) | "AC will be refined" |
| Dependencies | #33 (done), #135 (in-progress) | #33 (done), #139 (done) |

#136 is a strict superset of #140's implementation scope with tighter AC. #140's
unique contribution — the MCP-exclusion rationale — is a valid architectural signal
("MCP tool registration is a separate domain requiring a design decision") that should
be preserved in #136's notes.

#140's exclusion rationale for MCP tools merits attention: the FunctionToolset-vs-MCP
design choice hasn't been formally evaluated. #136's architect called MCP tools
"ancillary (2 thin wrappers)" and included them, which is pragmatic but doesn't address
#140's concern. This is a minor risk — if MCP tool patterns change, the tools are small
enough to refactor. Not worth blocking.

### 3.4 Evaluator Stub Limitation

#135's architecture review notes: "BookmarkPipeline uses SourceEvaluator with
ingest_threshold=0.7 but stub always returns 0.5." This means the bookmark pipeline
will never actually trigger ingestion until the LLM injection follow-up is complete
(tracked as task #523). Functional but non-ingesting. Not a blocker for extraction.

## 4. Recommendation (.90 confidence)

**Archive #140 as DONE.** Merge findings into #136's task body:
1. Document the `ingest(str)` to `ingest(IntakeResult)` API adaptation in #136
2. Preserve MCP-exclusion rationale as an architecture note
3. Note the evaluator stub limitation

No new follow-up tasks needed — #136 already covers the full implementation scope.

Challenge: reconsider — confidence in original: .65. Challenger flagged loss of API
mismatch knowledge and MCP separation signal. Revised from "close as duplicate" (.95)
to "archive as DONE with findings merged" (.90). Both signals now preserved in #136.

## 5. Actions Taken

No new `kanban-md create` commands — #136 covers all implementation scope.
Research findings merged into #136 via Channel B (task body append).
