---
id: 16
title: Build mcp-knowledge server
status: ideation
priority: needed
created: 2026-03-26T17:21:28.0951097+01:00
updated: 2026-03-26T17:25:18.3263412+01:00
tags:
    - phase-1
    - scope:mcp
    - type:build
depends_on:
    - 2
    - 15
class: standard
---

## Objective
Build an MCP server that wraps the knowledge engine, exposing search, ingest, and management as MCP tools.

## Acceptance Criteria
- [ ] MCP server in packages/mcp-knowledge/ using Python MCP SDK
- [ ] Tool: knowledge_search - hybrid search (graph + vector) with query
- [ ] Tool: knowledge_ingest - ingest a document or URL into the KB
- [ ] Tool: knowledge_list_sources - list registered knowledge sources
- [ ] Resource: knowledge://stats - read-only KB statistics
- [ ] Server accepts config for KB location (general vs project)
- [ ] Server communicates via stdio transport
- [ ] Imports from packages/knowledge/ (owlbear_knowledge)
- [ ] Register in .vscode/mcp.json and verify tool calls from VS Code
- [ ] SKILL.md with usage instructions for agents

## Context
Depends on R2 (MCP SDK) and M2 (extracted knowledge engine). This server makes the knowledge base accessible to all Copilot agents via MCP tools.
