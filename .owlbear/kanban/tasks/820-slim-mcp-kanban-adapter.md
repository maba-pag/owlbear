---
id: 820
title: Slim mcp-kanban adapter
status: backlog
priority: needed
created: '2026-04-10T21:22:41.393257+00:00'
updated: '2026-04-15T09:18:10.525644+00:00'
tags:
- phase-2
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 819
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- mcp-kanban `pyproject.toml` adds `owlbear-kanban` as dependency
- `server.py` imports from `owlbear_kanban` instead of local engine modules
- Engine modules removed from mcp-kanban source tree
- `models.py` retains `KanbanTask` (MCP boundary model)
- `__main__.py` retained
- #819 tests pass GREEN
- All 8 MCP tool tests pass (O4)

## Context

Phase 2, step 4. Depends on #819 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-15]]
## Research
- Research doc: .owlbear/research/slim-mcp-kanban-adapter-820.md
- Sources: 9 studied, 7 high-relevance (≥0.8)
- Recommendation: Verification-only pass — all AC lines already satisfied by #818 (confidence: 0.92)
- Key finding: #818 builder did both extraction AND slimming atomically; #820 is a no-op GREEN task
- Follow-up tasks created: none (task is self-contained)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — subagent not available in researcher mode
- Confidence in original: 0.92
- Key challenges: none (no alternative approaches — work is already done)
- Researcher response: N/A

## Builder Guidance
1. Run `uv run pytest tests/test_mcp_adapter_slimming_819.py -q --tb=short` — verify 19 GREEN
2. Run `uv run pytest tests/ -k "kanban" -q --tb=short` — verify O4
3. Confirm 4 files only in `serve/mcp-kanban/src/owlbear_mcp_kanban/`
4. Submit verification-only note — no code changes needed