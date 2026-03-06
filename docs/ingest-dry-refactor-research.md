# Refactor ingest() to Delegate to _ingest_from_intake()

> **Owning task:** #464 — Refactor ingest() to delegate to _ingest_from_intake()
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`IngestPipeline.ingest()` (L259–369) reimplements ~55 lines of pipeline steps that are identical to `_ingest_from_intake()` (L431–493). The method `ingest_text()` already correctly delegates to `_ingest_from_intake()` after its own intake + delta-check phase. Should `ingest()` follow the same pattern?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Refactoring.Guru — Extract Method | <https://refactoring.guru/extract-method> | .95 | Canonical refactoring pattern: replace duplicated code fragment with call to extracted method |
| SourceMaking — Extract Method | <https://sourcemaking.com/refactoring/extract-method> | .90 | Same pattern, independent reference: "Less code duplication. Replace duplicates with calls to your new method." |
| OwlBear `ingest_text()` (internal) | `src/owlbear/memory/knowledge/ingest.py` L370–428 | 1.0 | Existing codebase prior art — already delegates to `_ingest_from_intake()` after delta-check |
| OwlBear software-design-audit DRY-10 | `docs/software-design-audit.md` L165–180 | 1.0 | Original audit finding documenting the duplication |

## 3. Analysis

### 3.1 Duplication Confirmation

Side-by-side of `ingest()` steps 3–9 vs `_ingest_from_intake()`:

| Step | `ingest()` L308–362 | `_ingest_from_intake()` L436–493 | Identical? |
|------|---------------------|----------------------------------|------------|
| Create document_id | `uuid4().hex` | `uuid4().hex` | Yes |
| Set pending status | `_set_status(…, "pending", source=…)` | `_set_status(…, "pending", source=…)` | Yes |
| Set processing status | `_set_status(…, "processing")` | `_set_status(…, "processing")` | Yes |
| Chunk content | `_chunker.chunk(…)` | `_chunker.chunk(…)` | Yes |
| Insert document + store chunks | `_insert_document()` + `_store_chunks()` | `_insert_document()` + `_store_chunks()` | Yes |
| Parallel embed + extract | `asyncio.gather(…)` | `asyncio.gather(…)` | Yes |
| Process results | `_process_results(…)` | `_process_results(…)` | Yes |
| Update hash | `_update_content_hash(…)` | `_update_content_hash(…)` | Yes |
| Schedule enrichment | `_schedule_graph_enrichment()` + `_schedule_inter_doc_enrichment()` | Same | Yes |
| Return IngestResult | Same fields | Same fields | Yes |
| Error handler | Sets "failed" (creates doc_id if None) | Sets "failed" (doc_id always known) | Minor diff |

**Duplicated LOC:** ~55 lines (steps 3–9 + error handling + return).

### 3.2 Key Difference: Error Handling

In `ingest()`, the outer `try/except` wraps intake (step 1) + delta-check (step 2) + the pipeline. If intake fails _before_ `document_id` is assigned, the except block creates a new `document_id` to record the failure. In `_ingest_from_intake()`, `document_id` is always created at entry.

**After refactoring:** `ingest()` keeps its own try/except for intake + delta-check. On success, it calls `_ingest_from_intake()` (which has its own try/except). On intake failure, `ingest()` still creates a `document_id` and returns a "failed" `IngestResult`.

### 3.3 Trade-off Matrix

| Criterion | Keep duplicated (status quo) | Delegate to _ingest_from_intake() |
|-----------|------------------------------|-----------------------------------|
| DRY | Violates — 55 duplicated lines | Compliant — single source of truth |
| KISS | Two copies to mentally track | One pipeline path, simpler mental model |
| Risk of drift | High — pipeline change must be applied twice | Low — change in one place |
| Error semantics | Intake failure handled inline | Intake failure handled in `ingest()`, pipeline failure in helper |
| Test impact | 20+ existing tests cover `ingest()` | Existing tests continue to pass (behavior-preserving) |
| Breaking changes | N/A | None — public API unchanged |

## 4. Recommendation (.95 confidence)

**Delegate.** Refactor `ingest()` to call `_ingest_from_intake()` after intake + delta-check, exactly as `ingest_text()` already does. This is a textbook Extract Method refactoring (Fowler) applied in reverse — the extracted method already exists, `ingest()` just needs to call it.

**Risk:** Minimal. The refactoring is behavior-preserving. The only nuance is error handling for intake failures, which stays in `ingest()`. All 20+ existing tests should pass without modification.

**Implementation sketch for `ingest()`:**

```python
async def ingest(self, source, *, scope="global") -> IngestResult:
    source_str = str(source)
    try:
        intake_result = await self._read_source(source)
        changed, existing_doc_id = self.check_content_changed(source_str, intake_result.content, scope)
        if not changed:
            return IngestResult(…, status="skipped", skipped=True)
        if existing_doc_id is not None:
            self.delete_document_data(existing_doc_id)
        return await self._ingest_from_intake(intake_result, scope=scope)
    except Exception as exc:
        # Intake failure — no document_id yet
        document_id = uuid4().hex
        self._set_status(document_id, "pending", source=source_str, scope=scope)
        self._set_status(document_id, "failed", error=str(exc), scope=scope)
        return IngestResult(…, status="failed")
```

Net reduction: ~45 lines removed from `ingest()`.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement ingest() delegation to _ingest_from_intake()" --priority needed --tags "dry,refactor,knowledge,phase-10" --description "Refactor ingest() to call _ingest_from_intake() after intake+delta-check. Follow ingest_text() pattern. See docs/ingest-dry-refactor-research.md. AC: (1) ingest() delegates post-intake steps to _ingest_from_intake(). (2) No duplicated pipeline code between ingest() and _ingest_from_intake(). (3) All existing ingest tests pass. (4) Intake failure still produces a 'failed' IngestResult with document_id."
```

No additional tasks needed — this is a single atomic refactor with clear AC.
