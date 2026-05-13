# Research: MCP start_work Guidance Passthrough Implementation

> **Owning task:** #1529 — P2-02: implement MCP start_work guidance passthrough (AC4)
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1529 asks: does the MCP `start_work` tool handler pass dep-status guidance from `agent_view.start_work()` through verbatim, or does it need a code change?

AC4: "The MCP `start_work` tool handler returns the exact guidance list from `agent_view.start_work()` without mutation or loss."

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L319-334 | `_to_single_task_response()` — isinstance pass-through | 1.0 |
| 2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L559-582 | MCP `start_work` handler — guidance fallback guard | 1.0 |
| 3 | `serve/kanban/src/owlbear_kanban/agent_view.py` L962-1047 | `AgentView.start_work()` — returns `SingleTaskResponse` w/ guidance | 0.9 |
| 4 | `serve/mcp-kanban/tests/test_guidance.py` L1278-1294 | Sentinel passthrough test (existing proof) | 0.9 |
| 5 | `serve/mcp-kanban/tests/test_guidance.py` L1440-1467 | Non-overwrite guard test (existing proof) | 0.9 |
| 6 | `serve/kanban/src/owlbear_kanban/models.py` L674-682 | `SingleTaskResponse.guidance` field definition | 0.8 |

## 3. Analysis

### Data Flow (server.py L559-582)

```
agent_view().start_work(resolved_id) → SingleTaskResponse(guidance=["⚠️ ..."])
    ↓
_to_single_task_response(record)     # isinstance(SingleTaskResponse) → identity return
    ↓
if not result.guidance:              # non-empty → fallback SKIPPED
    result.guidance = collect_guidance(...)
    ↓
return result                        # guidance preserved verbatim
```

### Three Preservation Mechanisms

| # | Mechanism | Location | What it protects |
|---|-----------|----------|------------------|
| 1 | isinstance pass-through | `server.py:320-321` | `SingleTaskResponse` returned as-is — no `model_dump()` round-trip | 
| 2 | Falsy-guard on fallback | `server.py:576-578` | `collect_guidance()` only fires when `result.guidance` is empty |
| 3 | No field transformation | `server.py:559-582` | No code between view return and MCP response mutates guidance |

### Verdict: No Code Change Needed

The current implementation already satisfies AC4. The MCP handler:
- Receives `SingleTaskResponse` with guidance from `agent_view.start_work()`
- Passes it through `_to_single_task_response()` unchanged (isinstance identity)
- Skips `collect_guidance()` fallback when guidance is non-empty
- Returns the response with guidance preserved verbatim

### Existing Test Coverage

| Test | File | What it proves |
|------|------|----------------|
| `test_start_work_guidance_sentinel_passthrough` | `test_guidance.py:1278` | Adapter doesn't strip/transform guidance field |
| `test_start_work_agentview_guidance_not_overwritten_by_collect_guidance` | `test_guidance.py:1440` | Fallback doesn't overwrite non-empty guidance |

Both tests use exact-value equality (`== sentinel`), matching AC4's "without mutation or loss" requirement.

### Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Future refactor breaks isinstance check | Low | Medium | Existing tests catch immediately |
| `collect_guidance()` guard condition changed | Low | Medium | Non-overwrite test catches this |
| `SingleTaskResponse` removes guidance field | Very Low | High | Both tests fail at compilation |

## 4. Recommendation (confidence: 0.95)

**No code change required.** The builder should verify existing tests pass and confirm AC4 is satisfied by the current implementation. Proof bundle type: `existing` (de-escalate from `behavioral`).

Challenge: FALLBACK — trivial T1 verify-only research, challenger adds no value for a "confirm current code works" finding.

## 5. Follow-up Tasks

No follow-up tasks needed — the builder for #1529 simply verifies existing behavior and existing tests.
