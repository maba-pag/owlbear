# Supporting Context for Knowledge Source Lifecycle Ideation

## Dependency Status

- **#1556 (source identity fix):** Archived/completed. Source identity is now resolved by URL/path in `ingest_document`.
- **#1557 (enrichment graph persistence):** Archived/completed. Graph persistence contract for manual enrichment is fixed.

Both blockers are resolved.

## Existing Source Model (from `serve/knowledge/src/owlbear_knowledge/models.py`)

```python
class SourceType(StrEnum):
    URL_LIST = "url_list"
    FILE_GLOB = "file_glob"
    AUTHENTICATED_WEB = "authenticated_web"

class KnowledgeSource(BaseModel):
    id: str
    name: str
    source_type: SourceType
    fetch_method: str = ""
    enrich: bool = False
    config: dict[str, Any]
    scope: str = "global"
    enabled: bool = True
    priority: int = 0
    last_refreshed_at: str | None = None
    last_error: str | None = None
    created_at: str
    updated_at: str
```

## Existing MCP Tool Surface (5 tools + 1 deferred)

| Tool | Description |
|------|-------------|
| `search_knowledge` | Search KB (read-only) |
| `list_sources` | List registered sources (returns id, name, source_type, scope) |
| `ingest_document` | Ingest text; auto-creates source record if source_url provided |
| `refresh_source` | Re-ingest a source by ID |
| `get_stats` | KB summary statistics |
| *`list_entities`* | *Deferred — internal helper pending thread-safety review* |

## Existing Source Store CRUD (`source_store.py`)

Full CRUD: `create`, `get`, `list_all`, `update`, `delete`, `delete_cascade`, `resolve_by_url`, `resolve_by_path`, `list_enabled`.

`delete_cascade` removes source → source_pages → documents → entities, edges, chunks, document_status.

## Manifest Loader (`loader.py`)

A `parse_manifest` function reads YAML manifests with `sources:` entries (name, type, config, scope, enabled). `load_manifest_file` registers sources and ingests matching files. This is a CLI tool (`kb-load`), not an MCP tool.

## Prior Briefs

### Knowledge Activation Brief
- Agent-driven enrichment via VS Code Copilot subagents
- 8 active MCP tools planned (currently 5 shipped)
- Per-source `enrich` flag controls enrichment queue entry
- Enrichment worker system: `get_next_batch`, `store_enrichment`, `get_consolidation_candidates`

### Browser Knowledge Extraction Brief
- Authenticated content via Edge CDP
- Source pages lifecycle: discovered → approved/rejected → ingested → stale
- URL domain allowlist at tool level
- Replace-on-change refresh semantics
- User-triggered refresh (requires active Edge session)

## Design Constraints from Task Audit Amendments

1. **Authenticated source support:** Ownership decision must cover where `fetch_method` is stored/edited, HTTP-first browser fallback, which agent/tool drives browser automation, and refresh behavior for browser sources.

2. **Silent success on unwired refresh:** `_handle_authenticated_web` used to return zero-count with no error when content_fetcher was missing. Needs explicit lifecycle state (failed/skipped/disabled/unsupported).

3. **Error visibility:** `refresh_source` MCP tool now returns errors and warnings, but `list_sources` does not surface health status. Decision needed on where source health is visible.

4. **Direct-ingest source records:** `ingest_document(source_url=...)` auto-creates sources with potentially incompatible config shapes for refresh. Need to decide if these are one-shot provenance records, refreshable sources, or candidates requiring conversion.
