# P1-02: Schema Extensions — Implementation Research

> **Owning task:** #757 — P1-02: Impl — Schema extensions
> **Date:** 2026-04-10  **Status:** Complete

## 1. Context and Question

Task #757 is the GREEN phase for schema extensions required by the Authenticated Content Pipeline (#751). Sibling task #754 (RED phase) defines the tests. This research validates the implementation approach, identifies affected files, and flags one test conflict that must be resolved.

Key questions: (1) Which files need changes? (2) Do additive enum values break existing consumers? (3) What migration pattern fits v8→v9? (4) Are there test conflicts?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| models.py — current enums + models | `serve/knowledge/src/owlbear_knowledge/models.py` | .95 |
| schema.py — DDL + v1-v8 migrations | `serve/knowledge/src/owlbear_knowledge/schema.py` | .95 |
| document_store.py — cascade delete | `serve/knowledge/src/owlbear_knowledge/document_store.py` L241-265 | .90 |
| graph_store.py — insert_document | `serve/knowledge/src/owlbear_knowledge/graph_store.py` L359-395 | .85 |
| llm_extractor.py — dynamic enum prompt | `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` L16-17 | .80 |
| refresh.py — source type dispatch | `serve/knowledge/src/owlbear_knowledge/refresh.py` L84-92 | .85 |
| test_remove_crawl_stubs_703.py — exact SourceType guard | `tests/test_remove_crawl_stubs_703.py` L36-39 | .95 |
| Brief — schema section | `.owlbear/briefs/draft-browser-knowledge-extraction/brief.md` | .90 |
| Parent research — #751 | `.owlbear/research/751-authenticated-content-pipeline.md` | .85 |

## 3. Analysis

### 3a. Enum Extensions — Consumer Impact

| Consumer | How it uses enums | Break risk |
|----------|-------------------|------------|
| `llm_extractor.py` L16–17 | Builds prompt via `", ".join(e.value for e in EntityType/RelationType)` | None — new values auto-included |
| `refresh.py` L84–92 | `if/elif/else raise ValueError` dispatch | Safe — AUTHENTICATED_WEB hits `else` ValueError until handler added (separate task scope) |
| `source_store.py` L46 | `SourceType(row[2])` deserialization | None — additive; new value round-trips |
| `loader.py` L172 | `SourceType(entry.type)` from config | None — additive |
| MCP server L335–337 | `EntityType(entity_type)` validation | None — new values auto-valid |
| `test_remove_crawl_stubs_703.py` L36–39 | **Hardcoded: `expected = {"url_list", "file_glob"}`** | **BREAKS** — must be updated |

### 3b. Files to Modify (6 files)

| File | Change | LOC est. |
|------|--------|----------|
| `models.py` | Add `AUTHENTICATED_WEB` to SourceType; 5 EntityType members; 2 RelationType members; `PageStatus` StrEnum; `SourcePage` model; `source_id` field on Document | ~35 |
| `schema.py` | `_CREATE_SOURCE_PAGES` DDL; v8→v9 migration (source_pages table + source_id FK + indexes); bump `_SCHEMA_VERSION` to 9 | ~40 |
| `__init__.py` | Export `SourcePage` (and `PageStatus` if public) | ~2 |
| `document_store.py` | `delete_source_cascade()` method; update `insert_document` new-API path to persist `source_id` | ~25 |
| `graph_store.py` | Update `insert_document` / `get_document` / `list_documents` to handle `source_id` column | ~10 |
| `test_remove_crawl_stubs_703.py` | Relax `test_source_type_valid_values_only` to include `authenticated_web` | ~2 |

### 3c. Migration Pattern — v8→v9

Follows established pattern (see v5→v6, v7→v8):

```
_migrate_v8_to_v9:
  1. CREATE TABLE IF NOT EXISTS source_pages (...)
  2. ALTER TABLE documents ADD COLUMN source_id TEXT  (suppress OperationalError)
  3. CREATE INDEX idx_source_pages_source_id ON source_pages(source_id)
  4. CREATE INDEX idx_documents_source_id ON documents(source_id)
  5. UPDATE schema_version SET version=9
```

No FK enforcement via DDL (SQLite FK enforcement is at connection level via PRAGMA, already enabled in `init_db`). The FK relationship is logical — cascade delete is implemented in application code, matching the existing pattern in `delete_document_data`.

### 3d. SourcePage Model Design

From brief + #754 AC:

| Field | Type | Notes |
|-------|------|-------|
| id | str (uuid hex) | PK, default factory |
| source_id | str | FK to knowledge_sources.id |
| url | str | The page URL |
| status | PageStatus | discovered / approved / rejected / ingested / stale |
| extraction_hash | str or None | Hash of last extracted content |
| last_extracted | str or None | ISO timestamp |
| created_at | str | |
| updated_at | str | |

### 3e. Cascade Delete Chain

Brief specifies: source → pages → documents → entities → edges.

Implementation approach: new `delete_source_cascade(source_id)` on DocumentStore:
1. Find all `source_pages` with `source_id`
2. Find all `documents` with `source_id`
3. For each document: call existing `delete_document_data(doc_id)` (handles entities→edges→chunks→status→doc)
4. Delete all `source_pages` with `source_id`
5. Delete `knowledge_sources` row with `source_id`
6. Commit

Reuses existing `delete_document_data` — no duplication.

### 3f. Test Conflict Detail

`test_remove_crawl_stubs_703.py::test_source_type_valid_values_only` (line 38):
```python
expected = {"url_list", "file_glob"}
actual = {e.value for e in SourceType}
assert actual == expected
```
This assertion is a removal guard from #703, not a schema contract test. After #757 adds `AUTHENTICATED_WEB`, this test correctly fails. The fix: either relax the assertion to check CRAWL is absent (original intent) or update the expected set. The #754 test-writer should write the authoritative schema contract test; #757 builder updates the #703 guard.

## 4. Recommendation

**Proceed with implementation as specified.** Confidence: .88

All changes are additive, follow established codebase patterns, and have clear prior art in the existing migration chain (v1→v8). No architecture changes. Low risk.

One implementation note: the `source_id` FK on documents is logically enforced only — SQLite FK constraints via PRAGMA are already enabled, but the column addition via ALTER TABLE doesn't add the REFERENCES clause (SQLite limitation for ALTER TABLE). Application-level cascade delete handles integrity.

**Tier: T1** — additive enum values, new model/table, FK column, cascade delete method. All follow established patterns. No new capability, no architecture change, no security implications.

**Challenge: FALLBACK** — challenger subagent not available. Self-challenge: considered whether source_id FK should use DB-level CASCADE DELETE instead of application logic. Rejected — existing codebase uses application-level cascade exclusively (document_store.py L241-265, graph_store.py L176-192). Switching to DB-level CASCADE would be inconsistent and harder to test.

## 5. Follow-up Tasks

No new follow-up tasks needed — #757 itself is the implementation task. One note for the task body:
- #754 test-writer must account for `test_remove_crawl_stubs_703.py` conflict
- #757 builder must update `test_remove_crawl_stubs_703.py` as part of GREEN phase
