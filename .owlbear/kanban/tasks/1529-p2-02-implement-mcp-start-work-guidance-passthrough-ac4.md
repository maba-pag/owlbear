---
id: 1529
title: 'P2-02: implement MCP start_work guidance passthrough (AC4)'
status: research
priority: needed
created: 2026-05-13T12:18:10.756634+00:00
updated: 2026-05-13T12:18:10.756634+00:00
tags:
  - phase-2
  - scope:mcp-kanban
  - feature
parent: 1525
depends_on:
  - 1528
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Summary

Ensure MCP `start_work` tool handler passes dep-status guidance through verbatim. Verify existing handler logic already satisfies this — if `_to_single_task_response()` preserves guidance, no code change is needed; if not, fix the mapping.

Brief: see parent #1525

## Acceptance Criteria

- AC4: The MCP `start_work` tool handler returns the exact guidance list from `agent_view.start_work()` without mutation or loss

## Scope

- In scope: MCP handler at `server.py` — verify/fix guidance passthrough in `_to_single_task_response()` and `collect_guidance` fallback logic
- Out of scope: agent_view implementation (covered by #1527), unit tests

## Context

- `collect_guidance("start_work", None, result)` only fires when `result.guidance` is falsy — dep guidance will be non-empty for blocked tasks, so the fallback is skipped
- `_to_single_task_response()` must preserve the guidance list from the `SingleTaskResponse`

Proof bundle: behavioral