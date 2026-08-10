# Context — Knowledge Engine Activation

## Problem Statement

The knowledge engine (`serve/knowledge/`) and its MCP server (`serve/mcp-knowledge/`) exist as implemented code but are not operationally usable. The MCP server starts but enters an infinite loop attempting GitHub Copilot device-flow OAuth when no `OWLBEAR_LLM_API_KEY` is configured — since the device-flow prompts are invisible to the user in a stdio MCP context, the server never completes initialization.

## Project Type

`existing-feature/refactor` — substantial code exists (~35 modules in the engine, full MCP server with 14 tools), but it has never been activated end-to-end in production use.

## Current State (verified from code)

- **Engine library:** 35+ modules including vector store (Qdrant), graph store (SQLite), embeddings (BGE-M3, ~2.3 GB model), entity extraction, ingest pipeline, query service, scope transfer, bookmarks, consolidation.
- **MCP server:** 14 tools registered. Lifespan initializes all services. Falls back to `copilot_auth.py` device-flow when no LLM API key is present.
- **Architecture decision (DR #616, approved):** Single-DB with scope params + import/export. Global DB at `store/knowledge/knowledge.db`, portable snapshots at `.owlbear/knowledge/knowledge.db`. Option C chosen over dual-stack.
- **Storage:** `store/knowledge/general/sources.yaml` exists with ~548 document references (research docs, skills, instructions). No actual `.db` file committed.
- **Blocking issue:** The `copilot_auth.py` fallback path calls `get_copilot_token()` which triggers interactive device-flow — invisible in stdio context → infinite poll loop.

## Affected User

The OwlBear pipeline agents (consumers of `search_knowledge`, `ingest_document`, etc.) and the human operator who wants to curate knowledge from external sources (Porsche Design System, Confluence, SharePoint, project-specific API docs).

## Cost of Inaction

The knowledge MCP server remains dead code. Agents cannot retrieve curated domain knowledge during tasks. All context must come from instruction files, skills, or inline in prompts — no vector-semantic retrieval available.

## User Intent

- **No API keys** — corporate policy. Only LLM access is Copilot subscription via VS Code agents.
- **External sources are core** — Porsche DS, Confluence (doc standards, policies, tools, processes, manuals), SharePoint (requirements), Jira (tickets), project-specific API docs.
- **Graph enrichment is core** — cross-source relationship mapping (requirements ↔ tickets ↔ standards ↔ policies). Vector search alone ≈ "doesn't work" for this use case.
- **Browser auth is interactive** — user triggers ingest manually, Edge SSO session handles authentication.
- **Enrichment via VS Code agents** — pull-based worker agents, no API keys, no CLI.

## Active Tensions

1. **MCP server must start without LLM.** Remove copilot_auth from lifespan. Vector search always works. Entity extraction degrades gracefully (skipped until enrichment workers run).
2. **Enrichment is agent-driven inside VS Code.** Pull-based worker agents call `get_next_batch` → extract entities inline using Copilot model → call `store_enrichment`. Model: gpt-5.4 mini (0.33x).
3. **Ingest + enrich are separable.** Ingest prompt offers enrichment after ingestion. Separate `/kb-enrich` prompt for bulk/catch-up. Per-source `enrich: true/false` flag in sources.yaml.
4. **DB is local state + rebuild.** Vector DBs + embeddings too large for GitHub. `sources.yaml` is source of truth; `/kb-rebuild` prompt handles bootstrap on new machines.
5. **Browser detection: HTTP-first with user validation.** Try HTTP → show preview → user confirms or rejects → browser fallback if needed → save correct method to manifest.
6. **Scope machinery: interfaces only, defer implementation.** DR #616 scope tools stay as interfaces until second consumer project needs them.
7. **LightRAG: keep custom engine.** Research concluded LightRAG wrapping not justified — custom engine's persistent SQLite graph is better for live query-time traversal.

## Outcomes (Final)

1. **MCP server starts cleanly** — no auth loop, copilot_auth removed from lifespan, vector search works on ingested content
2. **Ingest pipeline works end-to-end** — local files (loader.py), public URLs (fetcher.py), authenticated pages (browser module + Playwright + Edge SSO)
3. **Enrichment via VS Code prompt** — pull-based worker agents, gpt-5.4 mini, Phase 1 (entity extraction via `get_next_batch`/`store_enrichment`) + Phase 2 (cross-source consolidation via `get_consolidation_candidates`/`store_enrichment`)
4. **Graph-augmented retrieval works** — cross-source relationships surfaced via graph traversal when enrichment has been run
5. **DB is local state** — gitignored, rebuilt from sources.yaml via /kb-rebuild prompt
6. **MCP tool surface approved** — 8 active tools (3 agent-facing, 2 curation, 3 enrichment) + 4 deferred scope interfaces
7. **Browser detection** — HTTP-first with user validation, fetch_method saved to manifest
8. **Per-source enrichment flag** — sources.yaml `enrich: true/false` controls which sources get entity extraction
9. **Entity type schema** — Phase 2 research question (may need TICKET, COMPLIANCE_CONTROL, etc.)
10. **Agent model** — 2 functional roles: `knowledge-ingestor` (ingest, refresh, dispatch enrichment) and `knowledge-enricher` (Phase 1 extraction + Phase 2 consolidation)
