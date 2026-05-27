---
id: 1895
title: 'Knowledge: rename MCP tools to match registry'
status: research
priority: important
created: 2026-05-27T11:05:45.483741+02:00
updated: 2026-05-27T11:05:45.483741+02:00
tags:
  - knowledge
  - layer-4
parent:
depends_on:
  - 1894
ac:
  - All MCP tool names match MCP_TOOL_ROUTING keys exactly
  - Agent configs updated to reference new tool names
  - KNOWLEDGE_TOOLS_EXCLUDE env var documentation updated if applicable
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Rename exposed MCP tool functions to match MCP_TOOL_ROUTING names in protocols/registry.py.

## Renames

| Current | Target |
|---------|--------|
| search_knowledge | knowledge_search |
| list_sources | knowledge_sources_list |
| (new) | knowledge_entity_lookup (already correct from #1894) |
| get_stats | knowledge_stats |

## Notes

This is a breaking change for MCP consumers. Requires coordinated agent tool-allowlist update across all agent configs that reference these tools.