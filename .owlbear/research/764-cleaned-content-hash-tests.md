# Cleaned-Content Hash + Replace-on-Change Cascade — Test Research

> **Owning task:** #764 — P1-11: Tests — Cleaned-content hash + replace-on-change cascade
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #764 is a RED-phase test task for four pipeline quality behaviors:
1. Delta detection hashes cleaned markdown, not raw HTML
2. Changed content → cascade-delete old doc + entities + edges before re-ingestion
3. Unchanged content hash → skip
4. No entity accumulation on refresh

The question: what tests are needed, what's already covered, and what patterns to follow?

## 2. Sources Studied

| # | Source | Location | Relevance | What |
|---|--------|----------|-----------|------|
| 1 | Existing content-hashing research (#253) | .owlbear/research/content-hashing.md | .90 | SHA-256 on normalized content, full re-ingest on change, LangChain/LightRAG prior art |
| 2 | HTML→MD cleaner research (#759) | .owlbear/research/759-html-markdown-cleaner.md | .90 | Idempotency for hashing: same HTML → same markdown; `compute_content_hash` on `content.strip()` |
| 3 | Existing delta detection tests | tests/test_knowledge_intake_docstore_ingest.py:780-830 | .85 | `TestFromAC_DeltaDetection`: skip on unchanged, mock-level |
| 4 | Existing cascade delete tests | tests/test_knowledge_intake_docstore_ingest.py:1035-1110 | .85 | `TestFromAC_DocumentStoreDeleteCascadeEntitiesEdges`: entity/edge removal at DB level |
| 5 | Replace-on-change tests (#775) | tests/test_authenticated_content_pipeline_775.py:545-709 | .80 | `TestFromAC_ReplaceOnChangeRefresh`: `delete_document_data` called, mock-level |
| 6 | `ingest()` implementation | serve/knowledge/src/owlbear_knowledge/ingest.py:160-213 | .95 | Current delta flow: `check_content_changed(source, intake.content, scope)` — hashes raw `intake.content` |
| 7 | `compute_content_hash` impl | serve/knowledge/src/owlbear_knowledge/status_store.py:40-52 | .95 | SHA-256 of `content.strip().encode()` — operates on whatever string is passed |

## 3. Analysis

### 3a. Coverage Gap Assessment

| AC | Existing Test Coverage | Gap for #764 |
|----|----------------------|--------------|
| AC1: Hash cleaned markdown | `compute_content_hash` tested on plain strings only. No test verifies cleaned vs raw HTML distinction | **FULL GAP** — no test asserts pipeline hashes cleaned content |
| AC2: Cascade delete on change | Mock-level (#775): verifies `delete_document_data` called. DB-level: verifies entity/edge rows removed | **PARTIAL** — no test combines cascade delete + re-ingest + entity count verification |
| AC3: Skip unchanged | Mock-level: `ingest()` returns `skipped` for unchanged content | **PARTIAL** — no test verifies skip when raw HTML differs but cleaned content matches |
| AC4: No entity accumulation | No test anywhere counts entities before/after refresh cycle | **FULL GAP** — no integration test for entity count stability |

### 3b. Architecture Constraint: Cleaner Not Yet Built

`owlbear_browser.cleaner` (tasks #783/#788) does not exist yet. `serve/browser/src/owlbear_browser/` contains only `cdp.py`, `edge_launcher.py`, `launcher.py`, `_errors.py`, `__init__.py`.

For AC1, tests must assert the contract without importing the cleaner. Two approaches:

| Approach | Complexity | RED validity | Recommendation |
|----------|-----------|-------------|----------------|
| A: Mock a `content_cleaner` param on ingest | Low | Clean RED — tests fail because param doesn't exist | **Yes (.85)** |
| B: Test that `ingest()` calls a cleaner before hashing | Low | Clean RED — sequence assertion fails | Yes (.80) |
| C: Import `owlbear_browser.cleaner` directly | Medium | Fails at import (ModuleNotFoundError) | No — couples test to browser package |

Approach A: `ingest()` accepts an optional `content_cleaner: Callable[[str], str]` parameter. When provided, content is cleaned before hashing. Tests pass a mock cleaner and verify the hash is computed on the cleaned output. The GREEN phase (#765) adds the parameter and wiring.

### 3c. Test Plan — 4 Test Classes

| Class | AC | Tests | Category |
|-------|-----|-------|----------|
| `TestFromAC_HashCleanedContent` | AC1 | 4 | 2 happy, 1 boundary, 1 edge |
| `TestFromAC_CascadeDeleteOnChange` | AC2 | 3 | 2 happy, 1 edge |
| `TestFromAC_SkipUnchangedCleanedContent` | AC3 | 2 | 1 happy, 1 boundary |
| `TestFromAC_NoEntityAccumulationOnRefresh` | AC4 | 3 | 2 happy, 1 edge |

**AC1 tests (hash on cleaned content):**
1. `ingest()` with `content_cleaner` param calls cleaner before hashing → fails (param doesn't exist)
2. Same raw HTML producing same cleaned markdown → skip (uses cleaner-based hash)
3. Different raw HTML producing different cleaned markdown → re-ingest
4. `content_cleaner=None` → behaves as today (hashes raw content)

**AC2 tests (cascade delete on change — integration):**
1. Ingest doc with entities+edges, re-ingest changed content → old entities removed from DB
2. Ingest doc with entities+edges, re-ingest changed content → old edges removed from DB
3. Cascade delete preserves unrelated documents' entities

**AC3 tests (skip unchanged cleaned content):**
1. Two different raw strings that produce the same cleaned output → second ingest skipped
2. Same cleaned content with whitespace differences → skip (normalization)

**AC4 tests (no entity accumulation):**
1. Ingest → N entities. Change content → re-ingest → still N entities (not 2N)
2. Multiple refresh cycles → entity count stable
3. Edge count stable across refresh cycles

### 3d. Test Infrastructure

Tests should use the existing DocumentStore/GraphStore with in-memory SQLite (pattern from `test_knowledge_intake_docstore_ingest.py`). Entity extraction can be mocked — the key assertion is entity/edge row counts in the DB, not extraction quality.

For AC1, the mock cleaner is a simple `lambda html: "cleaned markdown"` function.

## 4. Recommendation (confidence: .85)

Write 12 RED-phase tests in `tests/test_cleaned_content_hash_replace_on_change_764.py` across 4 classes.

**Key design decisions:**
- AC1: Introduce `content_cleaner` optional parameter contract on `ingest()` — cleanest way to test without coupling to the browser package
- AC2/AC4: Use real SQLite + DocumentStore/GraphStore (not mocks) — verify actual row counts in DB
- AC3: Test at the `check_content_changed` level with pre-cleaned content
- All tests FAIL in RED phase because: (1) `content_cleaner` param doesn't exist on `ingest()`, (2) current pipeline doesn't clean before hashing

**Risk:** If the GREEN phase (#765) takes a different wiring approach (e.g., cleaning in the refresh handler instead of `ingest()`), some AC1 tests may need adjustment. Mitigation: AC1 tests focus on the observable contract (hash is of cleaned content) rather than internal wiring.

Challenge: FALLBACK — challenger subagent not available. Self-challenge: main risk is coupling AC1 tests to a specific `content_cleaner` parameter that may not be the chosen approach. Alternative (testing at the refresh handler level) is less unit-testable and couples to the full refresh stack. The `content_cleaner` parameter approach is the most KISS-aligned.

## 5. Follow-up Tasks

None needed — #764 itself is the test-writing task (advances to backlog for test-writer). GREEN phase companion #765 already exists.

### Tier Classification

All findings are **T1 — Autonomous** (test-writing within existing patterns, no new capabilities or architecture changes).
