---
id: 711
title: 'Smoke test: ddgs MCP server startup and tool discovery'
status: archived
priority: medium
created: 2026-04-09T02:40:53.1431314+02:00
updated: 2026-04-09T09:19:26.4955885+02:00
started: 2026-04-09T09:19:26.4955885+02:00
completed: 2026-04-09T09:19:26.4955885+02:00
tags:
    - scope:tools
    - ' type:test'
parent: 686
depends_on:
    - 710
    - 709
class: standard
---

## Context
Parent: #686. Integration verification — AC5.

## Acceptance Criteria
- [ ] Test marked with @pytest.mark.integration
- [ ] Test verifies `uv run ddgs mcp` process starts without error
- [ ] Test verifies ddgs tool list includes search_text and extract_content
- [ ] Test passes when run with `-m integration`

## Files Affected
- tests/test_ddgs_mcp_integration_686.py (appended)

[[2026-04-09]] Thu 09:30
## Builder Notes
Archived: Redundant -- deliverables completed by parent #686 pipeline
