---
id: 496
title: Standardize error handling, return types, and exports across MCP servers
status: ideation
priority: important
created: 2026-03-31T06:52:31.0748128+02:00
updated: 2026-03-31T06:52:31.0748128+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
class: standard
---

## Objective\n\nEstablish consistent patterns across all three MCP servers (kanban, knowledge, project).\n\n## Acceptance Criteria\n\n### Error handling\n- [ ] All tool errors return strings with `error: ` prefix (kanban already does this)\n- [ ] mcp-knowledge ingest_document: change `Ingestion failed: {exc}` to `error: ingestion failed: {exc}`\n- [ ] mcp-project: add error returns where appropriate (e.g., file read failures)\n\n### Return types\n- [ ] Move toward structured returns (dict/list) for data, `str` for messages/errors\n- [ ] mcp-knowledge: search results, entity lists, source lists return structured data (not formatted bullet strings)\n- [ ] Verify mcp-project already uses structured returns (it does) — no change needed\n\n### Module exports\n- [ ] Add `__all__` to mcp-knowledge server.py listing all public symbols\n\n### Documentation\n- [ ] Add a brief `MCP server conventions` section to copilot-instructions.md or a new instructions/mcp-servers.instructions.md covering: error prefix convention, annotation requirements, return type guideline, lifespan pattern\n\n## Design Notes\n\n- Error prefix `error: ` is a simple string convention that callers can detect with startswith()\n- Structured returns enable outputSchema (already tasked in #492)\n- This is a consistency pass, not a redesign — each change is small
