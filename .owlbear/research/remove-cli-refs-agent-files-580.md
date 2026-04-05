# Remove CLI Refs from Agent Files — Obsolescence Analysis

> **Owning task:** #580 — P2-B1: Remove CLI refs from agent files, MCP-only
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Task #580 says: "Replace all 44 kanban\kanban-md.exe references across 11 agent files."
Created from `phase-b-mcp-only-kanban-migration.md §3a` on 2026-04-03. Since then,
the workspace was reorganized (agents → .github/agents/) and v2 agents were rewritten
as thin persona/rules/boundaries containers.

**Key question:** Is #580's scope still valid, or is it obsolete against v2 agents?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `.github/agents/*.agent.md` (16 files) | Codebase | .95 — grep: 0 kanban-md matches |
| 2 | #484 body (Stale Subtasks, Architecture Review) | Board | .90 — architect marks #580 stale |
| 3 | docs/research/update-pipeline-agents-mcp-refs.md | Research | .90 — #575 independently confirms 0 CLI in agents |
| 4 | #594 body (Re-scope #575 AC) | Board | .85 — MCP lifecycle gap follow-up |
| 5 | docs/research/phase-b-mcp-only-kanban-migration.md | Research | .80 — original #484 research (stale counts) |

## 3. Analysis

### 3a. AC Evaluation

| AC Line | State | Assessment |
|---------|-------|-----------|
| AC1: 0 kanban\kanban-md.exe matches | Already 0 | Satisfied — no work needed |
| AC2: output_format uses MCP syntax only | Neither CLI nor MCP tool syntax | Vacuously true. Intent (MCP examples) not met — but that's #594's scope |
| AC3: Example sections use MCP tool calls | No tool-call examples exist in v2 | Vacuously true. v2 examples are domain-specific, not tool demos |
| AC4: kanban-planner uses create_task | kanban-planner doesn't exist | Invalid — agent not created yet |
| AC5: Existing MCP blockquotes remain | No MCP blockquotes exist | Phase A added `owlbear-kanban/*` to frontmatter, not body blockquotes |

AC1 is satisfied. AC2-AC3 are vacuously satisfied but the underlying intent (MCP lifecycle
visibility in agents) is a real gap tracked by #594. AC4-AC5 have false premises.

### 3b. Options Comparison

| Criterion | A: Close as obsolete | B: Re-scope (MCP lifecycle) | C: Re-scope (verify-only) |
|-----------|---------------------|----------------------------|--------------------------|
| AC premise validity | 0/5 AC items actionable | Would duplicate #594 | Trivial: single grep |
| DRY compliance | Good — #594 covers gap | Poor — #594 overlap | Neutral |
| Board hygiene | Resolves stale subtask | Adds cross-tree coupling | Overhead for no value |
| MCP lifecycle gap risk | Depends on #594 landing | Eliminates dependency | Not addressed |
| Parent #484 alignment | Matches architect intent | Conflicts with revised AC | Overhead |
| Confidence | **.82** | .35 | .25 |

### 3c. #594 Dependency Risk

The MCP lifecycle gap (3-hop indirection: agent → r-pipeline-protocol → h-mcp-kanban)
is a valid concern raised by #575's challenger and confirmed in this research. Closing
#580 transfers coverage to #594 (under #575's tree, at ideation). Risk: if #594 stalls,
no task in #484's subtree tracks agent MCP lifecycle. Mitigation: #594 has concrete AC
(10 agents, 3-line lifecycle block, test assertion) and is next in the #575 pipeline.

## 4. Recommendation

**Close #580 as obsolete** (confidence: .82, revised from .92 after challenge)

The task's literal AC is either already satisfied (AC1) or has false premises (AC2-AC5).
The underlying MCP lifecycle intent is real but tracked by #594 under a different parent.
Re-scoping #580 would duplicate #594 and conflict with #484's revised AC which explicitly
excludes agent files.

Challenge: reconsider — confidence in original: .60. Key challenges accepted: C1 (AC2-AC5
vacuously vs substantively satisfied — addressed by separating "literal AC" from "intent"),
C3 (#594 coverage — mitigated by documenting dependency explicitly), B3 (verification
gap — accepted as managed risk). Rebutted: C2 (circular dep is metadata bug — removed
from arguments), C4 (parent authority double-counting — noted as single source).

## 5. Follow-up Tasks

1. **Batch-cancel #580-#584** — All 5 subtasks are stale per #484 architect review.
   Remaining Phase B scope is fully captured in #484's revised AC.
