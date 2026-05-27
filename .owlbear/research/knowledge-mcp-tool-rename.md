# Knowledge MCP Tool Rename — Registry Alignment

> **Owning task:** #1895 — Knowledge: rename MCP tools to match registry
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

The `MCP_TOOL_ROUTING` registry in `serve/knowledge/src/owlbear_knowledge/protocols/registry.py` defines authoritative tool names. The MCP server in `serve/mcp-knowledge/` exposes tools under different (legacy) names. Task asks: what's the full rename surface, what breaks, and what coordination is needed?

## 2. Sources Studied

| Source | Relevance |
|--------|-----------|
| `serve/knowledge/src/owlbear_knowledge/protocols/registry.py` L76–87 | Authoritative target names (0.95) |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` (all `@mcp.tool`) | Current exposed names (0.95) |
| `share/agents/knowledge-enricher.agent.md` L9 | Allowlist consumer (0.90) |
| `share/agents/knowledge-ingestor.agent.md` L8 | Allowlist consumer (0.90) |
| `share/skills/h-knowledge-ops/SKILL.md` L244 | KNOWLEDGE_TOOLS_EXCLUDE docs (0.85) |
| `setup/setup-guide.md` L182 | KNOWLEDGE_TOOLS_EXCLUDE example (0.80) |
| `serve/mcp-knowledge/README.md` L18–32 | Tool table docs (0.85) |

## 3. Analysis

### Full Rename Matrix (registry tools)

| Current function name | Registry target | In task body? |
|---|---|---|
| `search_knowledge` | `knowledge_search` | Yes |
| `list_sources` | `knowledge_sources_list` | Yes |
| `get_stats` | `knowledge_stats` | Yes |
| `ingest_document` | `knowledge_ingest` | **No** |
| `knowledge_register_source` | `knowledge_sources_register` | **No** |
| `remove_source` | `knowledge_sources_delete` | **No** |
| `refresh_source` | `knowledge_sources_refresh` | **No** |

**7 renames needed**, not 3. The task body is incomplete.

### Enrichment tools (NOT in registry)

| Tool | Notes |
|------|-------|
| `get_next_batch` | Enrichment internal |
| `get_consolidation_candidates` | Enrichment internal |
| `store_enrichment` | Enrichment internal |
| `retry_failed_enrichment` | Enrichment internal |

These 4 tools are absent from `MCP_TOOL_ROUTING`. AC says "match registry keys exactly" — tools not in registry are out of scope but create naming inconsistency (no `knowledge_` prefix).

### Impact surface

| File | Changes needed |
|------|----------------|
| `server.py` | 7 function renames |
| `knowledge-enricher.agent.md` | `get_stats` → `knowledge_stats`, `search_knowledge` → `knowledge_search` |
| `knowledge-ingestor.agent.md` | 5 tool refs: `get_stats`, `ingest_document`, `list_sources`, `refresh_source`, `search_knowledge` |
| `serve/mcp-knowledge/README.md` | Tool table (7 name updates) |
| `h-knowledge-ops/SKILL.md` | KNOWLEDGE_TOOLS_EXCLUDE example list |
| `setup/setup-guide.md` | Example env value `ingest_document` → `knowledge_ingest` |

### Risk

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking change for consumers with `KNOWLEDGE_TOOLS_EXCLUDE` set | Medium | Doc update + old names silently ignored (existing behavior) |
| Agent allowlists out of sync during rollout | High | Atomic commit: rename + allowlist update together |
| Enrichment tools naming inconsistency | Low | Separate follow-up; doesn't affect AC |

## 4. Recommendation

**Proceed with all 7 renames** in a single atomic commit. Confidence: **0.90**.

The task body table should be expanded to include the 4 missing renames. The enrichment tools (`get_next_batch`, `get_consolidation_candidates`, `store_enrichment`, `retry_failed_enrichment`) are out of AC scope — they should be addressed in a separate follow-up to add them to the registry with `knowledge_enrichment_*` prefix.

Challenge: FALLBACK — trivial rename research, no contested design decision.

## 5. Follow-up Tasks

1. **#1895 scope correction** — update task body to reflect all 7 renames (done via edit below)
2. **New task** — Add enrichment tools to MCP_TOOL_ROUTING with `knowledge_enrichment_*` prefix and rename
