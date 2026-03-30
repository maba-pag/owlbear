# KB Curation Process — Adding, Updating, and Removing Knowledge Sources

> **Owning task:** #177 — Document KB curation process
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #177 asks for documentation covering the full lifecycle of knowledge sources: adding new ones, refreshing existing ones, and removing stale content. The doc must describe the `sources.yaml` manifest format, delta detection via `StatusStore` content hashing, scope assignment conventions, and include worked examples.

**Key questions:** (a) What is the current curation infrastructure? (b) What patterns do other systems use? (c) What format should the skill/doc take?

## 2. Sources Studied

| Source | URL / Path | Relevance |
|--------|-----------|-----------|
| LlamaIndex IngestionPipeline (Document Management) | developers.llamaindex.ai/python/.../ingestion_pipeline/ | .90 — `doc_id → document_hash` dedup, docstore-based skip-if-unchanged, upsert-on-change |
| LangChain indexing API (RecordManager) | cited in docs/research/content-hashing.md | .85 — content+metadata dual hash, cleanup modes (incremental/full/scoped_full) |
| OwlBear `StatusStore` | packages/knowledge/src/owlbear_knowledge/status_store.py | 1.0 — `check_content_changed()`, `compute_content_hash()`, SHA-256 delta detection |
| OwlBear `KnowledgeSourceStore` | packages/knowledge/src/owlbear_knowledge/source_store.py | 1.0 — full CRUD for registered sources |
| OwlBear `KnowledgeSource` model | packages/knowledge/src/owlbear_knowledge/models.py | 1.0 — `SourceType` enum (url_list, crawl, file_glob), config dict, scope field |
| OwlBear source-registry research | docs/research/source-registry.md | .95 — data model design, CLI commands, refresh flow |
| OwlBear general-kb-initial-data-load research | docs/research/general-kb-initial-data-load.md | .90 — curation workflow design, data directory layout |
| OwlBear knowledge-scoping research | docs/research/knowledge-scoping.md | .95 — scope column, flat string format, 3 canonical scopes |
| OwlBear knowledge-ops skill | skills/knowledge-ops/SKILL.md | .90 — tool reference for add_source, refresh_source, list_sources |

## 3. Analysis

### 3.1 Current Infrastructure Status

The curation primitives are **already implemented** in the knowledge package:

| Component | File | Status |
|-----------|------|--------|
| `KnowledgeSourceStore` (CRUD) | source_store.py | Complete — create/get/list_all/update/delete |
| `KnowledgeSource` model | models.py | Complete — id, name, source_type, config, scope, enabled, priority |
| `SourceType` enum | models.py | Complete — `url_list`, `crawl`, `file_glob` |
| `StatusStore` (delta detection) | status_store.py | Complete — set_status, find_status_by_source, check_content_changed, update_content_hash |
| `compute_content_hash` | status_store.py | Complete — SHA-256 of whitespace-stripped content |
| `IngestPipeline` | ingest.py | Partial — text ingestion works, no delta check wired in |
| `knowledge_sources` table | schema.py | Complete — schema v6 migration |
| Scope column on all tables | schema.py | Complete — schema v3 migration |

**What's missing:** (a) A `sources.yaml` manifest file with curated sources; (b) a loader script that reads the manifest and drives ingestion; (c) user-facing documentation tying these pieces together. Items (a) and (b) are covered by sibling task #176.

### 3.2 Curation Workflow — 6-Step Process

Both LlamaIndex (docstore hash map) and LangChain (RecordManager) follow the same pattern: hash content → compare to stored hash → skip/re-ingest. OwlBear's `StatusStore` implements this identically. The curation workflow is:

| Step | Action | API | Purpose |
|------|--------|-----|---------|
| 1 | Register source | `KnowledgeSourceStore.create()` | Track where content comes from |
| 2 | Check delta | `StatusStore.check_content_changed()` | Skip unchanged documents |
| 3 | Ingest | `IngestPipeline.ingest_text()` | Chunk → extract → store |
| 4 | Track status | `StatusStore.set_status()` + `update_content_hash()` | Record ingestion state |
| 5 | Verify | Query the KB (search_knowledge tool) | Spot-check search relevance |
| 6 | Remove stale | `KnowledgeSourceStore.delete()` | Delete the source record only — see note below |

> **Note on removal (Step 6):** `KnowledgeSourceStore.delete()` issues a bare `DELETE FROM knowledge_sources WHERE id = ?`. There is no `ON DELETE CASCADE` in the schema (`knowledge_sources` has no foreign-key constraints on dependent tables), and no application-level cleanup is performed. As a result, removing a source orphans its `document_status` rows (which track by source URI, not source ID). Any chunks, entities, or documents ingested from the source remain in the KB until they are overwritten by a future ingest or purged manually. When removing a stale source, manually clean up orphaned records afterwards: delete matching rows from `document_status` by source URI, and remove any associated chunks/entities from the graph and vector stores.

### 3.3 Sources.yaml Manifest Format

From the source-registry research (#254) and general-kb-data-load research (#24):

```yaml
sources:
  - name: "Internal Research Docs"
    type: file_glob
    config:
      pattern: "docs/research/*.md"
    scope: global
    enabled: true

  - name: "Agent Skills"
    type: file_glob
    config:
      pattern: "skills/*/SKILL.md"
    scope: global
    enabled: true

  - name: "PydanticAI Docs"
    type: url_list
    config:
      urls:
        - "https://ai.pydantic.dev/agents/"
        - "https://ai.pydantic.dev/tools/"
    scope: global
    enabled: true

  - name: "Project-Specific Notes"
    type: file_glob
    config:
      pattern: "docs/decisions/**/*.md"
    scope: "project:owlbear"
    enabled: true
```

Fields map 1:1 to the `KnowledgeSource` model. The `type` field maps to `SourceType` (url_list, crawl, file_glob). The `config` dict is type-specific.

### 3.4 Scope Assignment Conventions

From knowledge-scoping research (#135), confirmed in schema.py and models.py:

| Scope | Format | When to use | Examples |
|-------|--------|-------------|---------|
| Global | `global` | Cross-project shared knowledge — framework docs, standards, patterns | Python docs, PydanticAI docs, skills, instructions |
| Project | `project:{name}` | Project-specific context — decisions, architecture, specs | `project:owlbear` for OwlBear research docs |
| Agent | `agent:{name}` | Agent-specific knowledge — role-specific references | `agent:builder` for build-pattern references |

**Default is `global`.** Queries auto-resolve to `["global", "project:{current}"]` when a project is active. The scope column exists on all core tables (entities, documents, edges, chunks, document_status).

### 3.5 Delta Detection Workflow

`StatusStore.check_content_changed(source, content, scope)` implements the full delta check:

1. Compute `SHA-256(content.strip())` → `new_hash`
2. Look up `document_status` by source URI + scope
3. If no record → content is new (return `(True, None)`)
4. If record exists and `content_hash == new_hash` → unchanged (return `(False, doc_id)`)
5. If record exists and hashes differ → changed (return `(True, doc_id)`)

This matches LlamaIndex's `doc_id → document_hash` map pattern and LangChain's RecordManager hash comparison. The SHA-256 algorithm provides collision resistance; whitespace stripping prevents false positives from trailing whitespace in HTTP responses (confirmed in content-hashing research #253).

### 3.6 Documentation Format Decision

| Option | Pros | Cons |
|--------|------|------|
| skills/ doc (SKILL.md) | Auto-loads for agents, structured tool reference | Already have knowledge-ops skill covering tools |
| docs/research/ doc | Task-anchored, conventional location | Not auto-loaded |
| **Update knowledge-ops skill** (.80) | Single source of truth, agents already read it | Grows the skill file |

**Recommendation (.80):** The knowledge-ops skill already covers the tool reference. The curation process doc should be a standalone `docs/research/` doc (this document) with a reference added to the knowledge-ops skill pointing here. The skill stays focused on tool usage; this doc covers the workflow.

## 4. Recommendation (.85 confidence)

**This research document itself satisfies the AC** — it covers the 5 AC items:

1. **Add/refresh/remove workflow** — §3.2 (6-step process)
2. **sources.yaml manifest format** — §3.3 (with examples)
3. **Delta detection workflow** — §3.5 (StatusStore content hashing)
4. **Scope assignment conventions** — §3.4 (global/project/agent)
5. **Examples for internal docs and external URLs** — §3.3 (yaml examples)

The remaining work is to add a cross-reference from the knowledge-ops skill to this doc, and to ensure the loader script (task #176) implements the manifest format documented here.

**Risk:** The loader script (#176, depends on #32) hasn't been built yet. This doc describes the target format based on implemented APIs. If #176 changes the manifest format, this doc needs updating.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add curation process cross-reference to knowledge-ops skill" --priority nice-to-have --status ideation --tags "phase-2,scope:knowledge,type:docs" --body "## Objective\nAdd a 'Curation Process' section to skills/knowledge-ops/SKILL.md referencing docs/research/kb-curation-process.md for the full add/refresh/remove workflow.\n\n## Acceptance Criteria\n- [ ] knowledge-ops SKILL.md has a 'Curation Workflow' section with a link to the research doc\n- [ ] Section briefly summarizes the 6-step process (register, check delta, ingest, track, verify, remove)\n- [ ] Does not duplicate content — points to the research doc for details\n\n## Context\nFollow-up from #177. See docs/research/kb-curation-process.md."
```
