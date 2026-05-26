---
id: 1889
title: 'Knowledge: MCP wire remove_source to IngestCoordinator.delete_source'
status: research
priority: needed
created: 2026-05-27T01:00:59.181782+02:00
updated: 2026-05-27T01:00:59.181782+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - remove_source tool calls IngestCoordinator.delete_source(source_id)
  - PurgeResult fields (status, completed_steps, sub-results) surfaced in 
    response dict
  - Partial failure (PurgeStatus.PARTIAL) returns structured error, does not 
    raise ToolError
  - Old manual SQL + vector deletion code removed
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Replace manual vector deletion + delete_cascade in the `remove_source` tool with delegation to IngestCoordinator.delete_source(). Return PurgeResult summary to caller. Handle partial failures per PurgeStatus.

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`