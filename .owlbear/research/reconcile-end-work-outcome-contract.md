# Reconcile MCP end_work outcome contract with AgentView validation

> **Owning task:** #1124 — B-XX: Reconcile MCP end_work outcome contract with AgentView validation
> **Date:** 2026-04-25 **Status:** Complete

## 1. Context and Question

Task #1077 introduced AgentView.end_work validation that accepts 4 outcomes: `success`, `reject`, `block`, `release` — explicitly rejecting `fail` as ERR_INVALID_OUTCOME. However, `fail` is actively used in the pipeline protocol (3 references) and agent instructions (2 agents). The #1077 reviewer flagged 5 regression failures in sibling tests; the architect acknowledged MCP drift and created #1124 for reconciliation.

**Core question:** Should `fail` be restored to AgentView, or should the pipeline docs align to the 4-outcome contract?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/engine.py:2764-2950` (AgentView.end_work) | Code | 1.0 |
| 2 | `serve/kanban/src/owlbear_kanban/engine.py:1355-1450` (KanbanEngine.end_work) | Code | 1.0 |
| 3 | `serve/kanban/src/owlbear_kanban/engine.py:1259-1295` (release_task) | Code | 0.9 |
| 4 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:393-468` (MCP end_work) | Code | 1.0 |
| 5 | `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py:110-121` (EndWorkParams) | Code | 0.9 |
| 6 | `share/skills/r-pipeline-protocol/SKILL.md` lines 74, 201, 260 | Protocol | 1.0 |
| 7 | `share/agents/builder.agent.md` line 55, `test-writer.agent.md` line 55 | Instructions | 0.9 |
| 8 | `share/skills/h-mcp-kanban/SKILL.md` lines 60-67 | Skill doc | 0.9 |
| 9 | Task #1077 body (architect, reviewer, builder notes) | Decision trail | 1.0 |

## 3. Analysis

### Current outcome contract per layer

| Layer | success | fail | reject | block | release |
|-------|---------|------|--------|-------|---------|
| r-pipeline-protocol (authoritative) | ✅ | ✅ (3 refs) | ✅ | ✅ | — |
| Agent instructions (builder, test-writer) | ✅ | ✅ | ✅ | ✅ | — |
| h-mcp-kanban skill | ✅ | ✅ | ✅ | ✅ | — |
| MCP server.py Literal | ✅ | ✅ | ✅ | ✅ | ✅ |
| EndWorkParams model | ✅ | ❌ | ✅ | ✅ | ✅ |
| AgentView.end_work | ✅ | ❌ (ERR) | ✅ | ✅ | ✅ |
| KanbanEngine.end_work | ✅ | ✅ | ✅ | ✅ | — |

### Semantic difference: `fail` vs `release`

| Behaviour | `fail` (raw engine) | `release` (AgentView → release_task) |
|-----------|---------------------|--------------------------------------|
| Appends timestamped note | YES | NO |
| Changes status | NO | NO |
| Releases claim | YES | YES |
| Idempotent on unclaimed | — (not in AgentView) | YES (no-op) |
| Activity log event | "outcome=fail" | "released by agent" |

**Critical finding:** `release` does NOT append notes. The pipeline protocol's 3 `fail` use cases all require note appending:
- TOOL_UNAVAILABLE: agent appends diagnostic note before unclaiming
- Prerequisite work: agent appends dep reasoning before unclaiming
- Handoff: agent appends `## Handoff` section before unclaiming

Using `release` instead of `fail` would silently drop agent notes — a data loss bug.

### Option trade-off matrix

| Option | Description | Diff size | Risk | KISS score |
|--------|-------------|-----------|------|------------|
| A — Restore `fail` to AgentView | Add `fail` to valid_outcomes, delegate to engine | Small (5 files) | Low — raw engine already handles `fail` | 0.90 |
| B — Align docs to 4-outcome contract | Remove `fail` from protocol + agents + skill | Large (8+ files) | High — semantic gap (notes lost with `release`) | 0.30 |
| C — Map `fail` at MCP server level | Intercept `fail` before AgentView delegation | Medium | Medium — adds complexity to MCP adapter | 0.50 |
| D — Use `edit_task` + `release` two-call pattern | Replace `fail` with two calls | Large | High — fragile non-atomic pattern | 0.20 |

## 4. Recommendation (confidence: 0.82)

**Option A — Restore `fail` to AgentView.end_work.**

The pipeline protocol is the authoritative source for agent behaviour. The #1077 architect acknowledged MCP drift as real and deferred to #1124. Restoring `fail` is not overriding a deliberate design — it is completing the reconciliation. The raw engine already handles `fail` correctly; AgentView just needs to stop rejecting it.

Challenge: `reconsider` — confidence in original: 0.34. Challenger argued this reopens the #1077 contract. **Rebuttal:** (a) the #1077 architect explicitly deferred MCP alignment to this task; (b) `release` is not a semantic substitute for `fail` because it drops notes — this is a data-loss gap, not a style preference; (c) the pipeline protocol is authoritative and mandates `fail` for 3 active use cases.

### Implementation scope

| File | Change |
|------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` (AgentView.end_work) | Add `fail` to valid_outcomes; require claimed state; delegate to raw engine end_work |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` (EndWorkParams) | Add `"fail"` to outcome Literal |
| `serve/kanban/tests/test_engine_end_work_1077.py` | Update `test_fail_outcome_raises_err_invalid_outcome` → expect `fail` to keep status |
| `serve/mcp-kanban/tests/test_mcp_models_1084.py` | Update `test_end_work_outcome_rejects_invalid_literal` to use non-`fail` value |
| `share/skills/h-mcp-kanban/SKILL.md` | Add `release` row to outcome table |

No changes needed to: pipeline protocol, agent instructions, MCP server.py (all already correct).

## 5. Follow-up Tasks

- **T-A:** Restore `fail` to AgentView valid_outcomes + update EndWorkParams Literal + update 2 test expectations + update h-mcp-kanban skill table (T1, implementation task)
- **T-B:** Remove MCP server.py `end_work` try/except TypeError fallback chain — dead code now that AgentView contract is stable (T1, cleanup)
