---
id: 1654
title: 'P1-02: Expose source health in list_sources'
status: research
priority: needed
created: 2026-05-18T03:11:18.823946+02:00
updated: 2026-05-18T03:11:18.823946+02:00
tags:
  - scope:mcp-knowledge
  - mcp-tools
parent: 1650
depends_on:
  - 1651
ac:
  - 'AC-1: `SourceInfo` TypedDict includes keys `last_refreshed_at: str | None`, `last_checked_at:
    str | None`, `last_error: str | None`, `enabled: bool`, `fetch_method: str`'
  - 'AC-2: `list_sources` response dict maps the 5 new fields from the corresponding
    `KnowledgeSource` model attributes for each source returned'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Expand `SourceInfo` TypedDict and `list_sources` MCP tool response with 5 health fields.

**Out-of-scope:** `config` field (URL/endpoint leak risk per brief). `enrich` field (processing config, not health per brief D5). Refresh logic (O2). Source removal (O4).

## Context

Current `SourceInfo` has 4 keys: `id`, `name`, `source_type`, `scope`. Needs 5 additional keys from `KnowledgeSource`: `last_refreshed_at`, `last_checked_at`, `last_error`, `enabled`, `fetch_method`.

`list_sources` currently builds response dicts with only the 4 existing keys. Must add the 5 new keys mapping from `KnowledgeSource` attributes.

Depends on #1651 because `last_checked_at` must exist in the model before it can be exposed.