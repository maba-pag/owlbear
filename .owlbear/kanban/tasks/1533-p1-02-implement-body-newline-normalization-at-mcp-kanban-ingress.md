---
id: 1533
title: 'P1-02: Implement body newline normalization at MCP kanban ingress'
status: research
priority: critical
created: 2026-05-13T12:29:21.909969+00:00
updated: 2026-05-13T12:29:21.909969+00:00
tags:
  - phase-1
  - scope:mcp-kanban
  - type:feature
parent: 1531
depends_on:
  - 1532
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Summary

GREEN phase: implement the normalization helper and wire it into all 5 MCP kanban tool call sites.

Brief: see parent #1531

## Scope

**In scope:**
- `_normalize_escaped_newlines()` helper function (alongside `_coerce_to_str()`)
- Call-site wiring in create_task, edit_task (body + append_body), end_work (note), create_dr (body)
- Guidance append after existing guidance block in each tool
- `create_dr` response dict: optional `guidance` key
- Tool description/docstring updates documenting normalization + escape convention

**Out of scope:**
- Engine changes, storage changes, archive remediation
- New dependencies
- `\r\n` handling, non-body parameters

## Implementation Reference

See `.owlbear/briefs/draft-body-newline-normalization/brief.md` for the exact helper code, guidance message text, and positional ordering constraints.