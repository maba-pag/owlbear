# Reconcile MCP end_work outcome contract with AgentView validation (v2)

> **Owning task:** #1124 — B-XX: Reconcile MCP end_work outcome contract with AgentView validation
> **Date:** 2026-04-25 **Status:** Complete (revision after architect rejection)

## 1. Context and Question

Task #1077 implemented Brief B D52's 4-outcome model at the AgentView layer, rejecting `fail` as `ERR_INVALID_OUTCOME`. However, the rest of the system was not aligned: the raw engine, MCP server.py, guidance, pipeline protocol, agent instructions, skill docs, session analytics, and cockpit UI all still expect `fail`. The #1077 architect created #1124 for reconciliation.

**Previous research** recommended restoring `fail` (Option A) but was rejected by the architect for: (a) missing Brief B D52 as the authoritative design source, (b) treating the `release` note-appending gap as evidence for `fail` rather than as a separate D52 implementation bug, (c) not presenting both options.

**Core question:** Should the entire system complete D52 (remove `fail` everywhere), or should AgentView/EndWorkParams align to the live 5-layer contract (restore `fail`)?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | Brief B D52 (`decisions.md`) | Authority | 1.0 |
| 2 | Brief B D55 (`decisions.md`) | Authority | 0.9 |
| 3 | Brief B paper-integration §1.8 (`paper-integration.md`) | Authority | 1.0 |
| 4 | `engine.py` AgentView.end_work (L2764–2950) | Code | 1.0 |
| 5 | `engine.py` KanbanEngine.end_work (L1355–1460) | Code | 1.0 |
| 6 | `engine.py` release_task (L1259–1295) | Code | 0.9 |
| 7 | `engine.py` _apply_outcome (L1308–1353) | Code | 0.9 |
| 8 | `models.py` EndWorkParams (L114) | Code | 0.9 |
| 9 | `server.py` end_work Literal (L399) | Code | 0.9 |
| 10 | `guidance.py` (L39) | Code | 0.8 |
| 11 | `r-pipeline-protocol/SKILL.md` L74, 201, 260 | Protocol | 1.0 |
| 12 | `h-mcp-kanban/SKILL.md` L57–70 | Skill doc | 0.9 |
| 13 | `builder.agent.md` L55, `test-writer.agent.md` L55 | Agent instr | 0.9 |
| 14 | `test_list_sessions_952.py` — completed-fail classification | Test | 0.9 |
| 15 | `ActivityTab.test.tsx` — fail vs released filter | Test | 0.9 |
| 16 | Task #1077 body — architect deferral to #1124 | Trail | 0.8 |

## 3. Analysis

### 3.1 Current contract per layer

| Layer | `fail` | `release` | Notes |
|-------|--------|-----------|-------|
| **r-pipeline-protocol** (authoritative) | ✅ 3 refs | — | Tool-unavailable, prereq, handoff |
| **Agent instructions** (builder, test-writer) | ✅ 1 ref each | — | Escalate rows |
| **h-mcp-kanban skill** | ✅ (outcome table) | — (missing) | |
| **MCP server.py Literal** | ✅ | ✅ | 5 values |
| **MCP guidance.py** | ✅ | — | Documents fail |
| **EndWorkParams model** | ❌ | ✅ | 4 values (D52 aligned) |
| **AgentView.end_work** | ❌ (ERR) | ✅ | 4 values (D52 aligned) |
| **KanbanEngine.end_work** | ✅ | ❌ | 4 values (no release) |
| **Activity log** | "outcome=fail" | "released by agent" | **Distinct events** |
| **Session analytics** | `completed-fail` state | `released` state | **Distinct classification** |
| **Cockpit UI (tests)** | failed-or-rejected filter | released filter | **Distinct filters** |

**Only 2 of 11 layers** reject `fail`. The rest actively use it.

### 3.2 Critical finding: `fail` ≠ `release` in observability

D52 consolidates `fail` into `release`, but the session/activity system assigns different meanings:

| Dimension | `fail` | `release` |
|-----------|--------|-----------|
| Activity event | `"outcome=fail"` | `"released by agent"` |
| Session state | `completed-fail` | `released` |
| Cockpit filter | failed-or-rejected | released |
| Semantic meaning | "tried, couldn't complete" | "voluntarily unclaiming" |

Merging these breaks the cockpit's ability to distinguish agent failures from voluntary releases — an **observability regression**.

### 3.3 D52 `release` note gap (separate defect)

D52 specifies: "`release`: clears claim, no status change, `note` appended if set."
Current implementation routes `release` through `release_task()` which does NOT append notes. This is a D52 implementation bug regardless of what happens with `fail`.

### 3.4 Two defects, not one

| Defect | Description | Tier |
|--------|-------------|------|
| D1 — AgentView rejects `fail` | Only 2 of 11 layers reject `fail`; #1077 partially applied D52 | T2 |
| D2 — `release` doesn't append notes | D52 implementation gap | T1 |

### 3.5 Option trade-off matrix

| Criterion | Option X: Complete D52 (remove `fail`) | Option Y: Restore `fail` + fix `release` notes |
|-----------|-------|--------|
| **Brief B authority** | Aligned (D52) | Deviates (D52 drop rationale) |
| **Live contract alignment** | 9 layers need update | 2 layers need update |
| **Observability** | Lost (fail/release merge) | Preserved (distinct events) |
| **Code files changed** | ~6 (engine, AgentView, guidance, server.py, models.py, session classifier) | ~3 (AgentView, models.py, release_task or AgentView routing) |
| **Doc files changed** | 0 (docs already have `release`) | 0 (docs already have `fail`) |
| **Test files changed** | ~5 (session tests, cockpit tests, guidance tests, engine tests, MCP tests) | ~2 (engine end_work test, MCP model test) |
| **Session/Cockpit impact** | Needs reclassification | None |
| **Risk** | High — cascading changes across analytics/UI | Low — aligns outlier layers |
| **KISS score** | 0.35 | 0.80 |
| **D52 `release` note bug** | Fixed (inherently) | Fixed (separately) |
| **Confidence** | 0.40 | 0.72 |

## 4. Recommendation

**Option Y — Restore `fail` to AgentView + fix `release` note-appending** (confidence: 0.72)

D52's consolidation of `fail` into `release` overlooked the observability distinction (different activity events, session states, and cockpit filters). The post-D52 system has 9 of 11 layers using `fail`; only AgentView and EndWorkParams reject it. Restoring `fail` aligns the outlier layers to the live contract and preserves the session/cockpit distinction.

The `release` note-appending gap is a separate D52 implementation bug fixed regardless of the `fail` decision.

**Tier: T2 (advisory DR).** This deviates from D52 but does not add new capabilities, change architecture, or alter security — it ratifies a de facto contract that D52 overlooked. The D52 rationale ("orphan-claim foot-gun") applies equally to `release` (same behavior: unclaim + keep status), so the stated rationale does not distinguish them.

### Challenge results

- Challenger: `reconsider` (confidence in original Option X: 0.36)
- Key findings: (1) `fail` and `release` carry distinct session/activity/cockpit semantics, (2) migration surface was understated — guidance, session tests, cockpit tests all depend on the distinction, (3) these are two separate defects not one
- Post-challenge: revised recommendation from Option X to Option Y. Acknowledged D52 authority but found its consolidation overlooks the observability layer.

## 5. Follow-up Tasks

- **T-A (#1125):** Restore `fail` to AgentView valid_outcomes + EndWorkParams Literal + update tests (T2, needs advisory DR)
- **T-B (#1126):** Remove dead try/except TypeError fallback chains in MCP server.py (T1, cleanup — already researched separately)
- **T-C (#1127):** Fix `release` outcome to append notes per Brief B D52 (T1, defect D2 — separate from the `fail` restoration)
