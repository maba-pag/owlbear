# Pipeline Quality: Hash on Cleaned Content + Replace-on-Change

> **Owning task:** #765 — P1-12: Impl — Pipeline quality: hash on cleaned content + replace-on-change
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #765 is the GREEN-phase implementation for pipeline quality improvements: (1) delta detection hashes cleaned markdown instead of raw HTML, and (2) replace-on-change with cascade-delete before re-ingestion. The companion RED-phase task is #764 (at `todo` — tests not yet written).

Key question: what is the minimal, correct implementation approach to wire cleaned-content hashing into the existing `IngestPipeline.ingest()` flow?

## 2. Sources Studied

| # | Source | Location | Relevance | What |
|---|--------|----------|-----------|------|
| 1 | Content-hashing research (#253) | .owlbear/research/content-hashing.md | .90 | SHA-256 on normalized content; full re-ingest on change; LangChain/LightRAG prior art |
| 2 | RED-phase research (#764) | .owlbear/research/764-cleaned-content-hash-tests.md | .95 | `content_cleaner` param contract on `ingest()`; 12 tests across 4 classes; test plan defines the GREEN-phase interface |
| 3 | `IngestPipeline.ingest()` impl | serve/knowledge/src/owlbear_knowledge/ingest.py:131-225 | .95 | Current flow: `check_content_changed(source, intake.content, scope)` hashes raw content |
| 4 | `StatusStore` methods | serve/knowledge/src/owlbear_knowledge/status_store.py:40-128 | .95 | `compute_content_hash` / `check_content_changed` / `update_content_hash` — SHA-256 on `content.strip()` |
| 5 | `DocumentStore.delete_document_data` | serve/knowledge/src/owlbear_knowledge/document_store.py:244-265 | .90 | Full cascade: entities, edges, chunks, document_status, documents |
| 6 | `owlbear_browser.cleaner.clean` | serve/browser/src/owlbear_browser/cleaner.py:183-189 | .90 | `strip_noise(html)` then `html_to_markdown()` — available as `Callable[[str], str]` |
| 7 | Replace-on-change tests (#775) | tests/test_replace_on_change_775.py | .80 | Confirms `delete_document_data(existing_id)` wiring already exists and is tested |

## 3. Analysis

### 3a. Current Flow

```
ingest(intake) ->
  check_content_changed(source, intake.content, scope)  # hashes raw content
  if changed and existing_id: delete_document_data(existing_id)  # cascade delete
  ... chunk, extract, embed ...
  update_content_hash(doc_id, intake.content)  # stores hash of raw content
```

**Gap:** Both hash operations use raw `intake.content`. For authenticated web content (HTML), cosmetic HTML changes (e.g. timestamp in footer, ad rotation) produce different hashes, triggering unnecessary re-ingestion.

### 3b. Implementation Approach Comparison

| Approach | LOC | Testability | RED-phase compat | KISS | Rec |
|----------|-----|-------------|------------------|------|-----|
| A: `content_cleaner` param on `ingest()` | ~5 | High — mock cleaner in tests | Yes — matches #764 test design | High | **.85** |
| B: Clean in RefreshOrchestrator handler | ~8 | Medium — requires refresh stack | No — tests expect param on ingest | Medium | .50 |
| C: Cleaner in StatusStore | ~5 | Low — too rigid; all sources cleaned | No — wrong layer | Low | .30 |

**Approach A details:** Add `content_cleaner: Callable[[str], str] | None = None` to `ingest()`. Before hash operations, compute `hash_content = content_cleaner(intake.content) if content_cleaner else intake.content`. Use `hash_content` in both `check_content_changed` and `update_content_hash`. No changes to StatusStore, DocumentStore, or any other module.

### 3c. Replace-on-Change: Already Implemented

The cascade-delete flow exists in `ingest()` at lines 175-176:
```python
if existing_id is not None:
    self._docs.delete_document_data(existing_id)
```
This cascades through entities, edges, chunks, document_status, and documents. Confirmed by `test_replace_on_change_775.py` (3 tests passing). No additional implementation needed.

### 3d. Affected Files

| File | Change | Risk |
|------|--------|------|
| `serve/knowledge/src/owlbear_knowledge/ingest.py` | Add `content_cleaner` param; compute `hash_content`; use in 2 call sites | Low — additive, backward-compatible |

No changes to: `status_store.py`, `document_store.py`, `schema.py`, `refresh.py`.

### 3e. Dependency: #764 Must Complete First

Task #764 (RED-phase tests) is at `todo`. The test file `tests/test_cleaned_content_hash_replace_on_change_764.py` does not exist yet. #765 cannot enter GREEN until #764's tests are written and confirmed failing.

## 4. Recommendation (confidence: .88)

Add `content_cleaner: Callable[[str], str] | None = None` parameter to `IngestPipeline.ingest()`. Apply it before both hash operations. No other modules require changes.

**Implementation (~5 LOC in ingest.py):**
1. Add `Callable` to TYPE_CHECKING imports
2. Add `content_cleaner` param to `ingest()` signature
3. Add `hash_content = content_cleaner(intake.content) if content_cleaner else intake.content`
4. Replace `intake.content` with `hash_content` in `check_content_changed` call
5. Replace `intake.content` with `hash_content` in `update_content_hash` call

Challenge: FALLBACK — challenger subagent not available. Self-challenge: (1) Should the chunker also receive cleaned content? No — chunking raw vs cleaned is a separate concern for Phase 2 wiring. (2) Should `ingest_text()` also get the param? No — `ingest_text()` has no delta detection. (3) Performance concern? No — `clean()` is lxml-based, sub-millisecond per page.

## 5. Follow-up Tasks

None needed. #765 itself is the implementation task. #764 (RED tests) already exists at `todo`.

### Tier Classification

**T1 — Autonomous.** Modifies existing function signature with backward-compatible optional parameter. No new capability, no architecture change, no security surface change.
