---
id: 492
title: Add outputSchema and tool annotations to knowledge and project MCP servers
status: ideation
priority: important
created: 2026-03-31T06:37:12.6171658+02:00
updated: 2026-03-31T06:37:12.6171658+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
class: standard
---

## Objective\n\nApply the same MCP best practices designed for mcp-kanban to the other two MCP servers.\n\n## Acceptance Criteria\n\n### mcp-knowledge server\n- [ ] Add outputSchema to all 5 tools (search_knowledge, ingest_document, list_entities, list_sources, get_stats)\n- [ ] Complete tool annotations: readOnlyHint already on 3/5 tools — add to search_knowledge (readOnly=true), verify ingest_document has readOnly=false\n- [ ] Add idempotentHint=true to search_knowledge, list_entities, list_sources, get_stats\n\n### mcp-project server\n- [ ] Add tool annotations to all 4 tools: readOnlyHint=true on project_info, project_list, project_readme, project_structure (all are read-only)\n- [ ] Add idempotentHint=true to all 4 tools\n- [ ] Add outputSchema to project_info (dict), project_list (array of dicts), project_readme (string), project_structure (string)\n\n### Cross-server\n- [ ] Verify all servers declare tools capability with listChanged=true\n- [ ] Update knowledge-ops SKILL.md if any tool signatures change\n\n## Design Notes\n\n- mcp-knowledge already has partial annotations — this completes the coverage\n- mcp-project has zero annotations — everything is read-only, easy win\n- outputSchema follows the same structured content pattern planned for kanban (#472-477)
