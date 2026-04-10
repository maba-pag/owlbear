---
id: 816
title: Fix timestamp sort
status: research
priority: needed
created: '2026-04-10T21:22:13.158053+00:00'
updated: '2026-04-10T21:22:13.158053+00:00'
tags:
- phase-1
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 815
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Sort by `created`/`updated` parses timestamps to `datetime` for comparison using `datetime.fromisoformat()`
- Handles both Go 7-digit nanosecond format (`2026-04-09T03:24:26.6974428+02:00`) and Python format
- Stored format unchanged — string round-trip fidelity preserved
- Correct ordering across mixed timezone offsets
- #815 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #815 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`