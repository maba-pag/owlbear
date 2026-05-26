---
id: 1890
title: 'Knowledge: MCP add register_source tool'
status: research
priority: needed
created: 2026-05-27T01:00:59.214408+02:00
updated: 2026-05-27T01:00:59.214408+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - knowledge_register_source tool registered with readOnlyHint=False, 
    destructiveHint=False
  - Pydantic validation errors returned as MCP ToolError with detail
  - SourceRegistration constructed from tool params and passed to 
    SqliteSourceStore.register_source
  - Returns serialized SourceRecord (id, name, state, kind, scope)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Create new `knowledge_register_source` MCP tool. Accepts name, kind, fetch_method, config, scope, enrich, refreshable, priority, metadata. Validates typed SourceConfig discriminated union via Pydantic. Delegates to SqliteSourceStore.register_source(SourceRegistration).

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`