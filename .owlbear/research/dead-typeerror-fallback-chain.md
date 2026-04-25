# Remove dead try/except TypeError fallback chains in MCP server

> **Owning task:** #1126 — Remove dead try/except TypeError fallback chain in MCP server end_work
> **Date:** 2026-04-25 **Status:** Complete

## 1. Context and Question

The MCP kanban server (`serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`) contains try/except TypeError fallback chains in two tools: `end_work` (lines 421-432) and `move_task` (lines 285-288). These chains progressively strip parameters from the AgentView call on TypeError, as a backwards-compatibility shim for when AgentView's method signature was still evolving.

**Question:** Are these fallback chains still reachable, and can they be safely removed?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `server.py:393-468` — MCP end_work tool | Code | 1.0 |
| 2 | `server.py:264-310` — MCP move_task tool | Code | 1.0 |
| 3 | `engine.py:2764-2950` — AgentView.end_work | Code | 1.0 |
| 4 | `engine.py:2677-2720` — AgentView.move_task | Code | 1.0 |
| 5 | `.owlbear/research/reconcile-end-work-outcome-contract.md` (#1124) | Research | 0.9 |
| 6 | `test_mcp_lifecycle_tools.py` — MCP tool tests | Tests | 0.8 |
| 7 | `test_mcp_guidance_1089.py` — RED phase guidance tests | Tests | 0.7 |

## 3. Analysis

### Parameter alignment: MCP primary call vs AgentView signature

| Tool | MCP primary call params | AgentView method params | Match? |
|------|------------------------|------------------------|--------|
| end_work | outcome, move_to, note, block_reason, archival_reason, archival_refs | outcome, note, move_to, block_reason, archival_reason, archival_refs | YES |
| move_task | task_id, status, archival_reason, archival_refs | task_id, status, archival_reason, archival_refs | YES |

Both primary calls pass exactly the parameters AgentView accepts. TypeError cannot occur.

### Fallback chain structure

| Tool | Level 1 (primary) | Level 2 (1st fallback) | Level 3 (2nd fallback) |
|------|-------------------|----------------------|----------------------|
| end_work | All 6 kwargs | Drops archival_reason, archival_refs | Drops move_to, block_reason too |
| move_task | status + archival kwargs | Drops archival kwargs | — |

### Risk assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| AgentView signature changes again | Low | Contract now stabilised by #1124; signature is tested |
| Test doubles with incomplete signatures | None | `_agent_view_for` scores mock candidates; MagicMock accepts any kwargs |
| Raw engine fallback path removed | N/A | Not removing it — only the TypeError shims within the AgentView block |

## 4. Recommendation (confidence: 0.92)

**Remove both try/except TypeError chains.** Keep the primary AgentView call, the KanbanError handler, and the NotImplementedError passthrough. The raw engine fallback below remains unchanged.

Challenge: FALLBACK — trivial cleanup, no trade-off to challenge.

### Implementation scope

| File | Change |
|------|--------|
| `server.py` end_work (lines 421-432) | Remove 3-level TypeError fallback; keep primary try + KanbanError + NotImplementedError |
| `server.py` move_task (lines 285-288) | Remove 2-level TypeError fallback; keep primary try + KanbanError + NotImplementedError |
| `test_mcp_guidance_1089.py` | Audit RED phase tests referencing TypeError fallback — update or remove if they assume fallback exists |

No doc changes needed. No protocol or skill changes.

## 5. Follow-up Tasks

- **T1 implementation:** Remove both TypeError fallback chains from server.py end_work and move_task; audit related test expectations.
