---
id: 1528
title: 'P2-01: MCP integration test for start_work guidance passthrough (AC4)'
status: research
priority: needed
created: 2026-05-13T12:18:01.416962+00:00
updated: 2026-05-13T12:18:01.416962+00:00
tags:
  - phase-2
  - scope:mcp-kanban
  - test
parent: 1525
depends_on:
  - 1527
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Summary

Write MCP integration test in `serve/mcp-kanban/tests/` verifying that dep-status guidance from `agent_view.start_work()` passes through the MCP `start_work` tool handler verbatim.

Brief: see parent #1525

## Acceptance Criteria

- AC4: MCP `start_work` tool response contains the exact guidance string returned by `agent_view.start_work()` (exact-value assertion, not substring)

## Scope

- In scope: MCP-layer integration test in `serve/mcp-kanban/tests/` for guidance passthrough
- Out of scope: agent_view unit tests (covered by #1526), consolidation tests

## Context

- MCP handler at `server.py` L520 calls `agent_view().start_work(resolved_id)` and maps result via `_to_single_task_response()`
- Current handler has `collect_guidance("start_work", ...)` fallback when `result.guidance` is empty — dep guidance will be non-empty so this path is skipped for blocked deps

Proof bundle: behavioral