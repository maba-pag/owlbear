# Research: MCP start_work Guidance Passthrough Test

> **Owning task:** #1528 — P2-01: MCP integration test for start_work guidance passthrough (AC4)
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1528 requires an MCP-layer integration test verifying that dep-status guidance from `agent_view.start_work()` passes through the MCP `start_work` tool handler verbatim. The parent feature (#1525) added dep-status guidance to the view layer (#1527); this test locks the contract at the MCP boundary.

**Research question:** What test structure, mocking strategy, and assertions are needed for AC4 (exact-value guidance passthrough)?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` L100-265 | Existing start_work adapter tests, mock fixtures | 1.0 |
| 2 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L559-581 | MCP start_work handler — guidance passthrough logic | 1.0 |
| 3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L319-334 | `_to_single_task_response()` — polymorphic normalizer | 0.9 |
| 4 | `serve/kanban/src/owlbear_kanban/agent_view.py` L962-1047 | `AgentView.start_work()` — guidance computation | 0.9 |
| 5 | `serve/kanban/src/owlbear_kanban/models.py` L674-682 | `SingleTaskResponse.guidance` field (default `[]`) | 0.8 |
| 6 | `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` L22-115 | `collect_guidance()` fallback dispatcher | 0.7 |

## 3. Analysis

### Guidance Flow Through MCP Handler

```
AgentView.start_work() → SingleTaskResponse(guidance=["⚠️ ..."])
    ↓
_to_single_task_response(record)  # isinstance(SingleTaskResponse) → pass-through
    ↓
if not result.guidance: ...        # non-empty → fallback SKIPPED
    ↓
return result                      # guidance preserved verbatim
```

Three mechanisms preserve guidance:
1. `_to_single_task_response()` returns `SingleTaskResponse` as-is (L320 isinstance check)
2. `if not result.guidance:` guard (L576) skips `collect_guidance()` when non-empty
3. No field transformation occurs between view return and MCP response

### Test Approach Comparison

| Approach | Complexity | Isolation | Notes |
|----------|-----------|-----------|-------|
| A: Mock `mock_av.start_work` → SingleTaskResponse w/ guidance | Low | High | Follows existing pattern in `TestFromAC_StartWorkAdapter` |
| B: Full engine integration w/ filesystem deps | High | Low | Overkill — tests view+MCP together, not just passthrough |
| C: Parametrize multiple guidance values | Medium | High | Covers edge cases (single, multi, empty-string) |

**Recommended: A** (single test, exact-value assertion). Add to existing `TestFromAC_StartWorkAdapter` class in `test_mcp_lifecycle_tools.py`.

### Risk Analysis

| Risk | Probability | Mitigation |
|------|------------|------------|
| `_to_single_task_response()` changes to always re-validate via `model_dump()` | Low | `model_dump()` preserves `guidance` field; test catches if field is dropped |
| `collect_guidance()` fallback overwrites non-empty guidance | Very Low | `if not result.guidance:` guard; test proves guard works |
| Guidance field renamed/removed from SingleTaskResponse | Low | Test compilation fails immediately — good regression signal |

### Test Structure

```python
@pytest.mark.asyncio
async def test_start_work_preserves_guidance_from_agent_view(self, ctx: MagicMock, mock_av: MagicMock) -> None:
    """AC4: guidance from AgentView.start_work() passes through verbatim."""
    expected_guidance = [
        "⚠️ This task has unresolved dependencies (IDs: 99). "
        "Review and confirm with the user that starting this work is intentional."
    ]
    resp = _make_response()
    resp.guidance = expected_guidance
    mock_av.start_work.return_value = resp

    result = await start_work(ctx, id="42")

    assert result.guidance == expected_guidance  # exact value, not substring
```

Key design decisions:
- Uses `_make_response()` helper + guidance override (minimal diff from existing tests)
- Uses the **exact format string** from `agent_view.py` L1008-1012 for realistic data
- `==` assertion (exact-value match per AC4 requirement)
- Single guidance entry matches the dep-blocked happy path

## 4. Recommendation (confidence: 0.92)

Add one test method to `TestFromAC_StartWorkAdapter` in `test_mcp_lifecycle_tools.py`. Single test, exact-value assertion, mock-based. No new test file needed.

**Challenge:** FALLBACK — trivial T1 test-structure research, challenger overkill.

## 5. Follow-up Tasks

Task #1528 itself advances to backlog — the test-writer will implement AC4 from this research.
