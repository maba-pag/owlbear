# ToolError Unification Gate Assessment

> **Owning task:** #695 — Full ToolError unification across all MCP servers (gated on evidence)
> **Date:** 2026-04-08 **Status:** Complete

## 1. Context and Question

Task #695 is gated on evidence that agents struggle with the dual error pattern (`"error: ..."` strings with `isError: false` vs `ToolError` with `isError: true`). This research evaluates whether the gate condition is met.

## 2. Sources Studied

| # | Source | Path / URL | Relevance |
|---|--------|-----------|-----------|
| S1 | MCP Spec §6 (2025-11-25) | modelcontextprotocol.io/specification/2025-11-25/server/tools | 1.0 |
| S2 | Prior research #680 | `.owlbear/research/mcp-tool-error-signaling-680.md` | 1.0 |
| S3 | Prior research #540 | `.owlbear/research/dual-error-pattern-mcp-conventions.md` | 0.9 |
| S4 | Prior research #496 | `.owlbear/research/mcp-server-error-return-standardization.md` | 0.9 |
| S5 | r-architecture-standards | `share/skills/r-architecture-standards/SKILL.md` L32-39 | 1.0 |
| S6 | Error journal code | `serve/orchestrator/src/owlbear_orchestrator/error_journal.py` | 0.8 |
| S7 | approve.py (runtime consumer) | `serve/mcp-memory/src/owlbear_mcp_memory/approve.py` L183-220 | 0.9 |
| S8 | Agent instructions | `share/instructions/agent-common.instructions.md` | 0.8 |
| S9 | Kanban board (full search) | All task bodies searched for "dual pattern" / "error pattern" failures | 0.9 |

## 3. Analysis

### 3a. Evidence Search — Agent Failure Due to Dual Pattern

| Evidence source | Finding | Gate signal |
|-----------------|---------|-------------|
| Error journal (`.owlbear/error-journal.jsonl`) | **File does not exist** — orchestrator has never been deployed to production | No data |
| Memory store (`store/memory/`) | Zero entries referencing error pattern confusion | No evidence |
| Kanban tasks (all 695+ tasks) | Zero tasks document agent failure from dual pattern | No evidence |
| Agent instructions (`agent-common.instructions.md`) | No mention of dual pattern; no `startswith("error:")` guidance | No evidence of need |
| Agent source files (`share/agents/`) | Zero agents check for `"error:"` prefix in their logic | No evidence of struggle |
| Runtime consumers (`approve.py`) | Handles both patterns correctly via `result.isError or text_r.startswith("error:")` | Working as designed |
| Prior research (#496, #540, #680) | All three validated the dual pattern as intentional and spec-valid | Counter-evidence |

### 3b. Why No Evidence Exists

1. **No telemetry infrastructure deployed.** The error journal class exists in code but `.owlbear/error-journal.jsonl` has never been created. The orchestrator hasn't run in production.
2. **LLM agents handle text naturally.** Copilot CLI presents tool results as text. Agents can read `"error: ..."` strings and recognize them as errors regardless of the `isError` flag.
3. **The convention is well-documented.** `r-architecture-standards` (S5) explicates when each pattern applies.
4. **The design rationale is sound.** Typed returns (TypedDict, BaseModel) cannot embed error strings → must raise ToolError. String returns can embed errors → use `"error: "` prefix. This is a Return-Type-Driven (RTD) decision, not arbitrary.

### 3c. MCP Spec Update Assessment

The 2025-11-25 spec (S1) §6 now explicitly lists "Input validation errors" and "Business logic errors" as Tool Execution Errors (`isError: true`). This is directionally aligned with full unification but:

| Criterion | Assessment |
|-----------|-----------|
| Spec language | SHOULD (not MUST) — both patterns remain spec-valid |
| Breaking change | No — spec hasn't invalidated the string-error approach |
| Urgency | None — SHOULD recommendation, not compliance requirement |

### 3d. Cost-Benefit at Current State

| Factor | Assessment |
|--------|-----------|
| Evidence of agent failures | **Zero.** No empirical data exists. |
| Blast radius | ~10 tools, ~40 test assertions, 1 runtime consumer, core lib wrappers |
| Priority | `someday` — lowest priority tier |
| Risk | Medium — breaking change with no demonstrated benefit |
| Opportunity cost | Dev time better spent on tasks with demonstrated need |

## 4. Recommendation (.90 confidence)

**Gate condition NOT met. Do not proceed with full unification.**

The dual pattern has been validated by 3 prior research tasks (#496, #540, #680), is spec-valid, follows a sound design rationale (RTD), and has zero documented agent failures. The system lacks the telemetry to detect such failures even if they occurred.

**Action:** Close #695. If monitoring becomes available (error journal deployed), reassess.

Challenge: SKIP — gate assessment with clear negative evidence, no recommendation trade-offs.

## 5. Follow-up Tasks

None created. The gate condition requires evidence that doesn't exist and can't be generated without the error journal infrastructure being deployed (separate concern, tracked elsewhere).

When to revisit: after error journal (#522) reaches production and accumulates runtime data showing agents mishandling `isError: false` tool responses.
