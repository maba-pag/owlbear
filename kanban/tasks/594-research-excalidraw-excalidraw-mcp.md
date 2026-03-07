---
id: 594
title: 'Research: excalidraw/excalidraw-mcp'
status: backlog
priority: important
created: 2026-03-05T23:51:52.2436534+01:00
updated: 2026-03-06T21:51:44.6508358+01:00
started: 2026-03-06T21:44:36.7644475+01:00
tags:
    - research
    - phase-research
    - scope:copilot
parent: 582
class: standard
---

**Source:** https://github.com/excalidraw/excalidraw-mcp
Analyze for Excalidraw MCP server implementation, tool definitions, and integration patterns.

**Research:** See docs/excalidraw-mcp-research.md

**Findings:**
- MCP Apps is an official MCP extension for interactive HTML UIs (iframe) in chat hosts (Claude, VS Code, ChatGPT)
- excalidraw-mcp implements 5 tools (2 model-visible, 3 app-only) with dual transport (stdio + StreamableHTTP)
- Key pattern: cheat-sheet companion tool (read_me) pre-loads domain context into model before main tool call
- Architecture mismatch with OwlBear: MCP Apps need HTML-capable host; OwlBear channels (CLI, Slack) cannot render iframes
- Recommendation: Do not adopt MCP Apps rendering (YAGNI). One adoptable pattern: cheat-sheet tool for complex toolsets

**Research checklist:**
- [x] Theoretical validity -- MCP Apps are sound, official spec, 6+ supported hosts
- [x] Prior art -- 20+ examples in ext-apps repo, excalidraw is flagship
- [x] Technical feasibility -- Python SDK exists but requires HTML host; OwlBear is not an MCP host
- [x] Architecture fit -- Low fit; OwlBear consumes MCP tools, does not render HTML iframes
- [x] Implementation approach -- Cheat-sheet tool pattern is adoptable; MCP Apps rendering is not
