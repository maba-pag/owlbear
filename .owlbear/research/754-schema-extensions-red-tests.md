# Schema Extensions RED Tests — Research

> **Owning task:** #754 — P1-01: Tests — Schema: source type, entity/relation types, source_pages, source_id FK
> **Date:** 2026-04-10  **Status:** Complete

## 1. Context and Question

Task #754 is the RED phase for schema extensions required by the Authenticated Content Pipeline (#751). Six test areas: (1) `AUTHENTICATED_WEB` in SourceType, (2) corporate EntityType values, (3) corporate RelationType values, (4) SourcePage model, (5) source_id FK on documents, (6) cascade delete source → pages → documents → entities → edges. All tests must fail against the current codebase.

Key question: What test patterns, fixtures, and assertions should the RED tests use to validate these schema extensions while matching project conventions?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/knowledge/src/owlbear_knowledge/models.py` — current enums & models | Internal | .95 |
| `serve/knowledge/src/owlbear_knowledge/schema.py` — DDL, migrations v1-v8 | Internal | .95 |
| `serve/knowledge/src/owlbear_knowledge/source_store.py` — source CRUD | Internal | .90 |
| `serve/knowledge/src/owlbear_knowledge/document_store.py` — cascade delete logic | Internal | .90 |
| `tests/test_knowledge_foundation.py` — model/schema test patterns | Internal | .95 |
| `tests/test_knowledge_intake_docstore_ingest.py` — cascade delete test patterns | Internal | .90 |
| Parent research: `.owlbear/research/751-authenticated-content-pipeline.md` | Internal | .85 |

## 3. Analysis

### 3a. Current State vs. Required Extensions

| Item | Current | Required Addition | Gap |
|------|---------|-------------------|-----|
| `SourceType` | `URL_LIST`, `FILE_GLOB` | `AUTHENTICATED_WEB` | 1 new member |
| `EntityType` | FILE, FUNCTION, CLASS_, DECISION, PATTERN, CONCEPT | REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | 5 new members |
| `RelationType` | DEFINES, IMPORTS, DEPENDS_ON, RELATED_TO, IMPLEMENTS, DOCUMENTS, GOVERNED_BY | GOVERNS, SUPERSEDES_VERSION | 2 new members |
| `SourcePage` model | Does not exist | Full Pydantic model + DDL | New table, new model |
| `source_id` FK on documents | Not present | FK column on documents table | ALTER TABLE + migration |
| Source cascade delete | Only document-level cascade exists | source → pages → documents → entities → edges | New chain |

### 3b. Test Pattern Comparison

| Pattern | Existing Convention | Recommendation |
|---------|-------------------|----------------|
| DB fixture | `_make_db()` → `:memory:` + `init_db()` | Reuse pattern |
| Test class naming | `TestFromAC_{Description}` | Follow convention |
| Enum assertion | `hasattr(Enum, "MEMBER")` or construct with value | Import + assert value equality |
| Schema version | `conn.execute("SELECT version FROM schema_version")` | Assert v9 after migration |
| Cascade verification | Insert chain, delete root, assert children gone | Match `test_knowledge_intake_docstore_ingest.py` |
| FK enforcement | `PRAGMA foreign_keys = ON` in `init_db()` | Already enabled—tests inherit |

### 3c. SourcePage Status Enum Design

| Option | Approach | KISS | Extensibility |
|--------|----------|------|---------------|
| A: StrEnum class | `PageStatus(StrEnum)` with 5 members | ✅ | ✅ |
| B: Literal type | `Literal["discovered", ...]` on model field | ✅ | ❌ |
| C: TEXT column, no validation | Plain string, validate at app layer | ✅ | ❌ |

**Recommendation**: Option A — matches project convention (SourceType, EntityType, RelationType are all StrEnum). Confidence: .90.

### 3d. Cascade Delete Implementation Approach

| Option | Mechanism | KISS | Safety | Consistency |
|--------|-----------|------|--------|-------------|
| A: Application-level cascade | Python method iterating source → pages → docs → entities → edges | ✅ | ✅ | Matches `delete_document_data()` pattern |
| B: DB-level `ON DELETE CASCADE` | FK constraints with CASCADE | ✅ | ⚠️ Silent deletes | Diverges from existing manual pattern |
| C: Hybrid | FK CASCADE on new tables + app code for entities/edges | ❌ | ⚠️ Mixed | Inconsistent |

**Recommendation**: Option A — application-level cascade. Matches existing `DocumentStore.delete_document_data()` pattern. The test should verify the full chain by inserting a source → pages → documents → entities → edges, deleting the source, and asserting all rows are gone. Confidence: .85.

## 4. Recommendation

**Proceed — write RED tests using established project conventions.** Confidence: .85.

Six test classes, one per AC item in the task body. Use `:memory:` SQLite + `init_db()`. Assert against model imports, enum membership, schema introspection, and cascade row counts.

Schema version should be v9 (one migration covering all additions: `source_pages` table, `source_id` column on documents, PageStatus enum).

Challenge: FALLBACK — challenger subagent not available.

**Tier: T1** — tests for schema extensions already approved in parent feature (#751). No architecture decisions, no security implications, no new capability in the tests themselves.

## 5. Follow-up Tasks

None needed — task #754 is itself the follow-up from #751 research. The GREEN phase implementation will be tracked separately (P1-02 or sibling tasks under #751).
