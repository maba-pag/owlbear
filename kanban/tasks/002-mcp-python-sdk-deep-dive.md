---
id: 2
title: MCP Python SDK deep-dive
status: ideation
priority: needed
created: 2026-03-26T17:18:16.5978974+01:00
updated: 2026-03-26T17:18:16.5978974+01:00
tags:
    - research
    - phase-1
    - scope:mcp
class: standard
---

## Objective
Research the MCP Python SDK and build a hello-world MCP server that registers in VS Code and handles tool calls.

## Acceptance Criteria
- [ ] Read MCP specification and Python SDK docs (mcp-python on GitHub)
- [ ] Document the 3 primitives: Tools, Resources, Prompts
- [ ] Build minimal MCP server in Python with one tool (e.g. echo)
- [ ] Register server in .vscode/mcp.json and verify VS Code discovers it
- [ ] Test tool invocation from Copilot Chat
- [ ] Document stdio vs HTTP transport trade-offs
- [ ] Document server lifecycle (start, shutdown, error recovery)
- [ ] Write findings to docs/research/mcp-python-sdk.md
- [ ] Create follow-up tasks for any gaps discovered

## Context
MCP servers are how we expose owlbear-specific capabilities (kanban, knowledge, project metadata) to Copilot CLI agents. We need 3-4 custom servers.
