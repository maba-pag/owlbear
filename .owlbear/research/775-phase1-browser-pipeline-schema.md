# Phase 1: Browser Package + Pipeline Quality + Schema — Research

> **Owning task:** #775 — Phase 1: Browser Package + Pipeline Quality + Schema
> **Date:** 2026-04-10  **Status:** Complete

## 1. Context and Question

Task #775 defines 10 scope items for Phase 1 of the Authenticated Content Pipeline (#751). This research validates each item against the current codebase (schema v8, 2 SourceTypes, 6 EntityTypes, 7 RelationTypes), maps inter-item dependencies, and provides decomposition guidance for the planner.

Parent research: `.owlbear/research/751-authenticated-content-pipeline.md` (validated brief approach, .82 confidence).
CDP spike research: `.owlbear/research/cdp-spike-752.md` (Chrome 136 constraint identified).

Key question: Are all 10 items technically feasible, and what is the correct task dependency graph for atomic TDD decomposition?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Parent research #751 | `.owlbear/research/751-authenticated-content-pipeline.md` | .95 |
| 2 | CDP spike research #752 | `.owlbear/research/cdp-spike-752.md` | .90 |
| 3 | Brief + voices | `.owlbear/briefs/draft-browser-knowledge-extraction/` | .95 |
| 4 | Schema v8 + migrations | `serve/knowledge/src/owlbear_knowledge/schema.py` | .95 |
| 5 | Models (enums) | `serve/knowledge/src/owlbear_knowledge/models.py` | .95 |
| 6 | IngestPipeline | `serve/knowledge/src/owlbear_knowledge/ingest.py` | .90 |
| 7 | RefreshOrchestrator | `serve/knowledge/src/owlbear_knowledge/refresh.py` | .90 |
| 8 | Protocol patterns | `serve/knowledge/src/owlbear_knowledge/protocol.py` | .85 |
| 9 | DocumentStore cascade | `serve/knowledge/src/owlbear_knowledge/document_store.py` | .85 |
| 10 | Package boundary tests | `tests/test_package_boundary.py` | .80 |
| 11 | trafilatura (PyPI) | pypi.org/project/trafilatura/ | .80 |
| 12 | Playwright CDP API | playwright.dev/python/docs/api/class-browsertype | .85 |

## 3. Analysis — Per-Item Feasibility

| # | Scope Item | Feasible | Complexity | Risk | Key Finding |
|---|-----------|----------|-----------|------|-------------|
| 1 | `owlbear_browser` core lib | Yes | High (~400 LOC) | Chrome 136 profile constraint | New pkg; no knowledge deps. trafilatura as dep. |
| 2 | `owlbear_mcp_browser` MCP server | Yes | Medium (~250 LOC) | Allowlist enforcement | Follows mcp-kanban/mcp-knowledge patterns |
| 3 | `AUTHENTICATED_WEB` source type | Yes | Low (~50 LOC) | None | StrEnum member + handler dispatch |
| 4 | `ContentFetcher` protocol | Yes | Low (~40 LOC) | None | Matches existing DI patterns (StructuredExtractor, EmbeddingProvider) |
| 5 | Schema v9 migration | Yes | Medium (~100 LOC) | FK on existing table | `ALTER TABLE documents ADD COLUMN source_id`; NULL for legacy docs |
| 6 | 5 entity types | Yes | Trivial (~5 LOC) | None | StrEnum additions auto-propagate to prompt |
| 7 | 2 relation types | Yes | Trivial (~3 LOC) | None | StrEnum additions auto-propagate to prompt |
| 8 | Content safety inversion | Yes | Low (~10 LOC) | Regression if predicate wrong | Change `== "url"` to `not in ("file", "text")` |
| 9 | `LLM_EXTRACTION_PROMPT` update | Yes | Low (~20 LOC) | Quality depends on examples | Must ship WITH items 6+7 or LLM collapses to CONCEPT |
| 10 | Replace-on-change refresh | Yes | Medium (~60 LOC) | Ghost doc cleanup | `delete_document_data()` exists; wire into changed-content path |

### 3a. Dependency Graph

```
WS-A: Foundation          WS-B: Quality       WS-C: Browser       WS-D: Integration
─────────────────         ────────────────     ─────────────       ──────────────────
(5) Schema v9 ──┐         (8) Safety inv.      (1) Browser lib     (3) AUTH_WEB type
(6) EntityTypes ─┼──→     (9) Prompt update    (2) MCP server      (4) ContentFetcher
(7) RelationTypes┘        ↑ depends on 6,7     ↑ depends on 1      (10) Replace-on-change
                                                                    ↑ depends on 3,5
```

**Critical path:** WS-A (5,6,7) → WS-B (8,9) and WS-C (1→2) can run parallel. WS-D (3,4,10) requires WS-A+C complete. Item 10 also needs item 5 (source_id FK).

### 3b. Key Technical Findings

**F1: Ghost document bug (item 10).** `ingest.py` line 156–174: when `check_content_changed()` returns `changed=True`, the code inserts a NEW document but never deletes the old one (`existing_id` is unused in the changed branch). Old docs, entities, edges, and chunks accumulate. Fix: call `delete_document_data(existing_id)` before re-insert. `DocumentStore.delete_document_data()` already exists (line 243) and handles the full cascade (entities → edges → chunks → status → document).

**F2: Schema v9 — NULL source_id for legacy docs.** SQLite `ALTER TABLE ADD COLUMN` doesn't enforce NOT NULL on existing rows. `source_id TEXT REFERENCES knowledge_sources(id)` with DEFAULT NULL is correct — legacy docs have no source association. No backfill needed.

**F3: Entity/relation/prompt coupling.** Items 6, 7, 9 MUST ship atomically. `LLM_EXTRACTION_PROMPT` uses `", ".join(e.value for e in EntityType)` — new enum members appear in the type list automatically, but without explicit prompt guidance (item 9), the LLM will collapse corporate types into CONCEPT. The parent research (#751) confirmed this risk.

**F4: Content safety inversion scope.** Current predicate: `_meta.get("source_type") == "url"`. Only `URL_LIST` and `FILE_GLOB` sources exist today, so `FILE_GLOB` content is NOT wrapped. Inverting to `not in ("file", "text", "file_glob")` wraps all future source types by default (defense-in-depth). This is a safety improvement even without browser content.

**F5: Package boundary registration.** `ALLOWED_IMPORTS` in `test_package_boundary.py` needs: `"owlbear_browser": set()` (no cross-deps), `"owlbear_mcp_browser": {"owlbear_browser"}`. The boundary manifest guard test will fail until these are added. Browser should NOT depend on knowledge — clean separation per the brief's architecture.

**F6: `source_pages` table enables scope-based URL management.** The table tracks individual URL lifecycle (discovered → approved → ingested → stale) within a source. This is Phase 2 functionality (source management agent), but the schema must ship in Phase 1 to avoid a v10 migration. The table DDL should include: `source_id TEXT REFERENCES knowledge_sources(id)`, `url TEXT NOT NULL`, `status TEXT NOT NULL`, `content_hash TEXT`, `approved_at TEXT`, `last_extracted_at TEXT`.

## 4. Recommendation

**Proceed with all 10 items. Confidence: .85.**

The scope is sound and architecturally aligned. No items need removal or deferral. The planner should decompose into ~8-10 atomic TDD tasks across 4 workstreams with the dependency graph from §3a.

Specific guidance for the planner:
- Items 6+7+9 must be a single task (atomic entity model + prompt update)
- Item 8 (safety inversion) is independent and should be its own task
- Item 10 (replace-on-change) depends on item 5 (source_id FK) for source-level cascade
- Items 1+2 (browser packages) are the largest and may need 3-4 subtasks each
- Package boundary test updates should be part of the package creation tasks

Challenge: FALLBACK — decomposition research has no controversial recommendation to challenge. All items validated against existing codebase patterns.

**Tier: T1** — This task was itself created as a T3 follow-up from #751 research. The T3 decision gate is the Phase 0 go/no-go (#774). Phase 1 research validates implementation approach within the already-approved architecture direction.

## 5. Follow-up Tasks

No new research tasks needed. Task #775 already says "Needs decomposition" — the planner will create atomic TDD subtasks using this research's dependency graph and findings.

**Dependency correction needed:** #775 has `depends_on: [752]` but should be `depends_on: [774]`. #774 is the Phase 0 spike task; #752 is the research-only task that produced #774 and #776. The architect review on #751 already flagged this.
