# Context — Knowledge Source Lifecycle Ownership

## Problem Statement

The knowledge module has a fully modeled source entity (`KnowledgeSource`) with scope, fetch method, enabled state, priority, enrichment flags, and error tracking — but no coherent user-facing workflow for managing sources over their lifetime. Sources are currently created through three disconnected paths:

1. **Manifest loader** (`kb-load` CLI) — YAML file with source entries, batch ingestion
2. **Direct ingest** (`ingest_document` MCP tool with `source_url`) — auto-creates source records as a side effect
3. **Refresh orchestrator** — operates on existing sources but doesn't create or manage them

There is no unified way for the operator to: register a new source, edit its fetch method, toggle enrichment, inspect health, remove bad data, or understand which sources are active vs. stale vs. broken.

The CRUD layer exists in `KnowledgeSourceStore` (create, get, list, update, delete, delete_cascade), but it's not wired to any user-facing surface beyond `list_sources` (read-only, minimal fields) and `refresh_source`.

## Project Type

Existing-feature/refactor — the data model and persistence layer exist; this is about deciding which surface(s) own the user-facing lifecycle operations.

## Affected Users

- **Primary:** The operator (human user) managing knowledge sources through VS Code
- **Secondary:** Pipeline agents consuming knowledge through `search_knowledge`

## User's Core Value Proposition

Connecting internal corporate docs (behind SSO) with external public docs, keeping them current, and surfacing cross-source relationships. Public-only sources would be solved by existing services (e.g. context7); the unique value is the authenticated + public mix and cross-source mapping.

Expected scale: 10–50 sources across a few domains. Mixed refresh cadence (some stable reference material, some pages changing weekly).

## Active Tensions

- No unified source creation workflow — user wants to declare sources (file or MCP), agents should execute ingestion
- Direct-ingest auto-creates source records with config shapes incompatible with refresh
- `list_sources` returns only (id, name, type, scope) — no health, error, or freshness info
- Authenticated/browser sources silently no-op on refresh when browser fetcher isn't wired, and `_update_source_record` still marks them as refreshed
- Source health data exists in the model (`last_error`, `last_refreshed_at`) but isn't surfaced in `list_sources`

## Outcomes (Revised After Early Challenge)

**O1 — Expose source health in `list_sources`.** Add `last_refreshed_at`, `last_error`, `enabled`, and `fetch_method` to the `list_sources` MCP tool response. Agents and the operator can see what's healthy, broken, or stale using existing data.

**O2 — Fix refresh honesty.** Authenticated web refresh must fail explicitly when the browser fetcher isn't wired. `_update_source_record` must not mark a source as refreshed when refresh actually did nothing. The `refresh_source` tool must surface the failure reason.

**O3 — Clean direct-ingest source semantics.** Direct-ingest source records (created by `ingest_document(source_url=...)`) must be explicitly classified: are they one-shot provenance, or managed/refreshable? Config shapes must be consistent per source type so `refresh_source` doesn't silently no-op.

**O4 — Add `remove_source` MCP tool.** Wire `KnowledgeSourceStore.delete_cascade` as an MCP tool so agents can remove a source and all its downstream data.

**Scope boundary:** This ideation decides the fix/improvement targets. Implementation becomes follow-up build tasks. No new management system, manifest format, or Cockpit UI in this scope.

## Already Resolved

- `refresh_source` MCP tool now returns `errors` and `warnings` in its response dict
- Both dependency tasks (#1556, #1557) are archived/completed
- Direct-ingest config shape concern partially resolved: `_configured_urls` already handles both `url` (singular) and `urls` (plural)
