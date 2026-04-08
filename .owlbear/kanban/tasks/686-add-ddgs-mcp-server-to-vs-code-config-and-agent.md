---
id: 686
title: Add ddgs MCP server to VS Code config and agent tool allowlists
status: research
priority: important
created: 2026-04-08T20:54:21.8216945+02:00
updated: 2026-04-09T00:52:08.7146167+02:00
tags:
    - scope:tools
    - ' type:feature'
    - ' source:research-681'
depends_on:
    - 681
claimed_by: shore-dart
claimed_at: 2026-04-09T00:52:08.7130832+02:00
class: standard
---

## Context

Research #681 recommends using the ddgs built-in MCP server for web search. This task implements the integration.

## Acceptance Criteria

- [ ] AC1: `ddgs[mcp]` added as a dependency (setup guide or pyproject.toml dev group)
- [ ] AC2: `.vscode/mcp.json` configured with ddgs MCP server entry (`ddgs mcp` command)
- [ ] AC3: Researcher agent tools list updated with `'ddgs/search_text'` and `'ddgs/extract_content'`
- [ ] AC4: Ideator agent tools list updated with `'ddgs/search_text'`
- [ ] AC5: Smoke test confirms ddgs MCP server starts and tools are callable

## Files Affected

- `.vscode/mcp.json` (or equivalent MCP config)
- `share/agents/researcher.agent.md`
- `share/agents/ideator.agent.md`
- `setup/setup-guide.md` or `pyproject.toml`

## Notes

Needs decomposition: may need DR approval first (T3 — new capability). See research doc: `.owlbear/research/web-search-mcp-options.md`
