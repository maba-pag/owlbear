# KB Data Loader Script and Sources Manifest

> **Owning task:** #176 — Build KB data loader script and sources manifest
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Task #176 requires a YAML manifest (`data/knowledge/general/sources.yaml`) and a loader script (`packages/knowledge/src/owlbear_knowledge/loader.py`) that reads the manifest and ingests documents via `IngestPipeline`. Key questions: (a) What manifest format best aligns with existing infrastructure? (b) Which ingestion API to use? (c) How to handle file glob resolution securely? (d) How to structure the CLI entry point?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| GraphRAG YAML config | microsoft.github.io/graphrag/config/yaml/ | .85 — `input` section with `file_pattern`, `type`, `base_dir` settings for document discovery |
| LightRAG insert API | github.com/HKUDS/LightRAG | .80 — `rag.insert(["TEXT1","TEXT2"])` batch pattern, `doc_status_storage` for delta detection |
| LlamaIndex SimpleDirectoryReader | developers.llamaindex.ai/.../simpledirectoryreader/ | .75 — `input_dir` + `recursive` + `required_exts` glob-based file discovery pattern |
| OwlBear IngestPipeline (local) | packages/knowledge/src/owlbear_knowledge/ingest.py | 1.0 — `ingest(IntakeResult)` with built-in delta detection |
| OwlBear intake module (local) | packages/knowledge/src/owlbear_knowledge/intake.py | 1.0 — `read_file()`, `read_url()`, `read_text()` producing IntakeResult |
| OwlBear models.py (local) | packages/knowledge/src/owlbear_knowledge/models.py | 1.0 — `KnowledgeSource`, `SourceType` enum: FILE_GLOB, URL_LIST, CRAWL |
| OwlBear general-kb-initial-data-load | docs/research/general-kb-initial-data-load.md | .95 — Parent research defining the loader concept and data sources |
| strictyaml docs | hitchdev.com/strictyaml/ | .80 — Already a project dependency, type-safe YAML parsing with schema validation |

## 3. Analysis

### 3.1 Manifest Format — Alignment with Existing Types

The `SourceType` enum already defines `FILE_GLOB`, `URL_LIST`, `CRAWL`. The `KnowledgeSource` model has `name`, `source_type`, `config`, `scope`, `enabled`, `priority`. The manifest should map directly to these types.

**Recommended manifest format (strictyaml-validated):**

```yaml
sources:
  - name: "Research docs (curated)"
    type: file_glob
    config:
      glob: "docs/research/*.md"
    scope: global
    enabled: true

  - name: "Skills"
    type: file_glob
    config:
      glob: "skills/*/SKILL.md"
    scope: global
    enabled: true

  - name: "Instructions"
    type: file_glob
    config:
      glob: "instructions/*.md"
    scope: global
    enabled: true
```

| Design aspect | GraphRAG approach | LightRAG approach | Recommended |
|---|---|---|---|
| File discovery | Regex `file_pattern` | Code-driven `rag.insert()` | File globs via `pathlib.Path.glob()` — simpler than regex, aligns with AC |
| Config format | YAML `settings.yml` | Python code / `.env` | YAML — already used for kanban config, strictyaml available |
| Delta detection | Cache-based (LLM response cache) | `doc_status_storage` hash | Built-in via `IngestPipeline.ingest()` — already implemented |
| Batch ingestion | `graphrag index` CLI command | `rag.insert([texts])` | Sequential per-file via `IngestPipeline.ingest()` |

### 3.2 Ingestion API — `ingest()` vs `ingest_text()`

The AC specifies `IngestPipeline.ingest_text()`, but the newer `IngestPipeline.ingest(IntakeResult)` method is superior:

| Feature | `ingest_text()` | `ingest(IntakeResult)` |
|---------|-----------------|----------------------|
| Delta detection | No (caller must check) | Built-in via `check_content_changed()` |
| Source tracking | No source metadata | Source URI from IntakeResult |
| Cancellation | No | Supports `cancel_signal` |
| Content hash update | No | Automatic via `update_content_hash()` |

**Recommendation (.90 confidence):** Use `IngestPipeline.ingest()` instead of `ingest_text()`. The loader creates `IntakeResult` via `intake.read_file()`, then passes it directly to `ingest()`. This eliminates the need for the loader to call StatusStore directly — the pipeline handles delta detection internally.

### 3.3 File Glob Resolution — Security

`intake.read_file()` already calls `sandbox_path()` to prevent path traversal. The loader should:

1. Resolve globs relative to the workspace root: `pathlib.Path(root).glob(pattern)`
2. Pass each resolved file through `intake.read_file(path, workspace_root=root)`
3. `sandbox_path()` validates each path stays within the workspace

No additional security work needed — the existing `_paths.py` sandboxing is sufficient.

### 3.4 CLI Entry Point

The AC specifies `uv run python -m owlbear_knowledge.loader --manifest path`. This requires a `__main__`-compatible module. Pattern: `loader.py` with an `async def main(manifest_path, workspace_root)` and an `argparse`-based CLI at module level.

| Approach | Pros | Cons |
|----------|------|------|
| `argparse` in `loader.py` | Simple, no extra deps | Must handle async (asyncio.run) |
| Click-based CLI | Nicer UX | Extra dep (click not in knowledge package) |

**Recommendation (.85):** `argparse` — KISS, no extra dependency. The knowledge package should stay lean.

### 3.5 Source Registration Flow

For each manifest entry:

1. Parse manifest with strictyaml schema validation
2. Create `KnowledgeSource` model instance
3. Register via `KnowledgeSourceStore.create()`
4. Resolve file globs → list of paths
5. For each file: `intake.read_file()` → `IngestPipeline.ingest()`
6. Log results (ok/skipped/failed counts)

**Note:** `KnowledgeSource.created_at` and `updated_at` are required `str` fields (not Optional). The loader must set these to ISO timestamps at creation time.

### 3.6 Testing Strategy

| Test category | What to test | Mock? |
|---|---|---|
| Manifest parsing | Valid/invalid YAML, missing fields, unknown types | No mocks needed |
| File glob resolution | Glob expansion, empty globs, nested dirs | Temp directory fixtures |
| Source registration | KnowledgeSourceStore.create() called per entry | In-memory SQLite |
| Delta detection | Skip unchanged files, re-ingest changed | In-memory SQLite + mock embedder |
| CLI entry point | argparse, --manifest flag, exit codes | Subprocess or monkeypatch |

**Key constraint:** Mock `EmbeddingProvider` to avoid FlagEmbedding (2.2 GB) dependency in tests. The existing test suite already uses mock embedders — follow that pattern.

### 3.7 strictyaml Schema

strictyaml provides compile-time schema validation. The manifest schema should enforce:

- `sources` as a sequence of mappings
- `name` as a non-empty string
- `type` restricted to `file_glob` | `url_list`
- `config` as a mapping with type-specific keys
- `scope` defaulting to `"global"`
- `enabled` defaulting to `true`

This catches misconfiguration at parse time rather than runtime — aligns with the project's "fail fast" philosophy.

## 4. Recommendation (.85 confidence)

Build the loader as a single module (`loader.py`) that:

1. Parses `sources.yaml` via strictyaml with a typed schema
2. Registers sources via `KnowledgeSourceStore.create()`
3. Resolves file globs using `pathlib.Path.glob()` relative to workspace root
4. Ingests via `IngestPipeline.ingest(IntakeResult)` (not `ingest_text()` — AC refinement)
5. Reports results per-source (ok/skipped/failed counts)

**AC refinement needed:** Change "Calls IngestPipeline.ingest_text()" to "Calls IngestPipeline.ingest()" — the newer API handles delta detection automatically. Similarly, "Checks content delta via StatusStore" can be simplified since `ingest()` handles this internally.

**Risk:** strictyaml is a root dependency but not in the knowledge package's own deps. The loader should import it with a clear error message if missing, or it should be added to knowledge package deps.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add strictyaml to knowledge package dependencies" --priority needed --status ideation --tags "phase-2,scope:knowledge,type:build" --body "## Objective\nAdd strictyaml to packages/knowledge pyproject.toml dependencies so the loader module can import it.\n\n## Acceptance Criteria\n- [ ] strictyaml>=1.7 added to [project.dependencies] in packages/knowledge/pyproject.toml\n- [ ] uv lock updated\n- [ ] Import works: python -c 'from owlbear_knowledge import loader'"
```
