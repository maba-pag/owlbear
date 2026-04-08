# Wiring Analysis Detectors into the Agent Pipeline

> **Owning task:** #682 — Research: how to wire analysis detectors into the agent pipeline
> **Date:** 2026-04-08 **Status:** Complete

## 1. Context and Question

The `owlbear_orchestrator.analysis` package has 4 pattern detectors (high error rate, slow agent, repeated failure, stale dispatch) producing `AnalysisProposal` objects. A CLI exists for manual runs. **Nothing consumes proposals automatically** — the orchestrator doesn't read them, no agent processes them. This research evaluates who should consume proposals, what actions they should trigger, and the minimal wiring to produce value.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/orchestrator/src/owlbear_orchestrator/analysis/` (models, detectors, analyze, \_cli) | .95 |
| 2 | `serve/orchestrator/src/owlbear/orchestrator/loop.py` (dispatch loop, waves, curator injection) | .95 |
| 3 | `serve/orchestrator/src/owlbear/orchestrator/waves.py` (assemble_waves, curator scheduling) | .90 |
| 4 | `.owlbear/research/self-improvement-analysis-pipeline.md` (#31 research) | .90 |
| 5 | `.owlbear/research/analysis-module-implementation-readiness.md` (#179 research) | .85 |
| 6 | `share/agents/curator.agent.md` (current curator scope) | .85 |
| 7 | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` (record_learning signature) | .80 |
| 8 | `v1/src/owlbear/core/improvement_proposals.py` (v1 prior art) | .75 |

## 3. Analysis

### 3.1 Consumer Options

| Criterion | A: Curator (.75) | B: New analyst agent (.55) | C: Orchestrator loop (.60) | D: Prompt injection (.70) |
|-----------|-------------------|---------------------------|---------------------------|--------------------------|
| New code | ~20 LOC (prompt extension) | ~80 LOC (agent file + prompt + dispatch entry) | ~30 LOC (loop changes) | ~15 LOC (context inject) |
| New deps | 0 | 0 | 0 | 0 |
| KISS | Medium — scope creep risk | Low — new agent for 4 rules | Medium — loop complexity | High — minimal wiring |
| Separation of concerns | Fair — curation ≠ analysis | Good — dedicated agent | Poor — orchestrator shouldn't decide | Good — agent gets context |
| Action capability | Has `record_learning`, `create_task` | Would need full toolset | No agent tools | Depends on receiving agent |
| Scheduling | Already runs every 5th cycle | Needs new scheduling logic | Every cycle (wasteful) | Per consumer's schedule |
| YAGNI risk | Low | High — new agent for 4 detectors | Medium | Low |
| Precedent | v1 had no dedicated consumer | No precedent | No precedent | LangSmith uses context injection |

### 3.2 Hybrid Recommendation: Orchestrator-trigger + Curator-consumer

Neither pure option is ideal. The minimal wiring that produces value:

1. **Orchestrator runs `analyze()` post-cycle** — pure function call, no decisions. Stores proposals in `LoopState`. (~5 LOC in loop.py)
2. **Curator prompt includes proposals when available** — `format_prompt()` appends serialized proposals. (~10 LOC in loop.py)
3. **Curator agent instructions** get a `## Analysis Proposals` section defining how to handle each category. (~30 lines in curator.agent.md)
4. **Curator uses existing tools** — `record_learning` for awareness, `create_task` for systemic issues.

This mirrors existing patterns: `audit_log` is injected into `orchestrate()`, curator is injected into `assemble_waves()`. Proposals are just another injected context.

### 3.3 Actions Per Proposal Type

| Proposal Pattern | Category | Recommended Action | Rationale |
|-----------------|----------|-------------------|-----------|
| `high_error_rate` | reliability | `record_learning` + `create_task` if rate > 60% | Persistent failures need investigation tasks |
| `slow_agent` | performance | `record_learning` only | Awareness; no action unless extreme |
| `repeated_failure` | reliability | `create_task` always | Same task failing 2+ times = structural issue |
| `stale_dispatch` | stability | `record_learning` only | Diagnostic; stale dispatches self-resolve or are already tracked |

Escalation via scribe: only if proposals recur across 3+ cycles (pattern of patterns). This is a future enhancement, not MVP.

### 3.4 Minimal Wiring Estimate

| Component | Changes | LOC |
|-----------|---------|-----|
| `LoopState` | Add `proposals: list[AnalysisProposal]` field | 3 |
| `run_loop()` | Call `analyze()` post-cycle, store in state | 8 |
| `format_prompt()` | Append proposals to curator prompt when present | 12 |
| `curator.agent.md` | Add analysis proposal handling section | 30 |
| Tests | Verify proposals flow from loop → curator prompt | 40 |
| **Total** | | **~93 LOC** |

### 3.5 Why Not a New Agent

A dedicated "analyst" agent (Option B) would need: agent file, dispatch entry in `AGENT_PROMPT_PREFIX`, scheduling logic in `assemble_waves()`, tool allowlist, and custom prompt. That's ~80+ LOC of infrastructure for an agent that runs `analyze()` (already a Python function) and calls `record_learning`/`create_task` (already in curator's toolset). YAGNI — curator already has the tools, schedule, and conceptual adjacency (system quality maintenance).

## 4. Recommendation (confidence: .82, revised)

**Manual-first validation, then deterministic router if demand is proven.**

Initial recommendation was hybrid orchestrator-trigger + curator-consumer (.78). Challenger returned `reconsider` (.82 confidence) with compelling arguments: (a) curator is memory hygiene, not pipeline health — scope creep; (b) YAGNI means don't automate consumption until CLI usage proves proposals drive useful action; (c) routing deterministic proposals through an LLM introduces non-determinism — design smell; (d) v1 never consumed proposals automatically and that was fine.

**Revised approach (3 phases):**

| Phase | What | When | LOC |
|-------|------|------|-----|
| 1. Manual validation | Add analysis CLI reference to `w-orchestration` skill; operators run between sessions | Now | ~5 |
| 2. Deterministic router | Python function mapping proposal patterns → actions (no LLM) | After 2-3 cycles prove manual value | ~30 |
| 3. Agent integration | Dedicated agent or orchestrator hook (only if Phase 2 insufficient) | If Phase 2 demand warrants | ~80+ |

Phase 1 is the only follow-up task for now. Phase 2/3 are deferred until Phase 1 validates demand.

Challenge: `reconsider` — confidence in original: .78 → revised: .82. Accepted challenges on scope creep, YAGNI, and non-determinism. Rejected original hybrid approach in favor of manual-first validation.

## 5. Follow-up Tasks

1. **Add analysis CLI reference to orchestration workflow** — Document `python -m owlbear_orchestrator.analysis --format markdown` as a post-session diagnostic step in `w-orchestration` skill. T1: doc-only change, no code.
2. **Validate analysis proposal utility over 2-3 cycles** — Run CLI manually after orchestration sessions, record whether proposals drive useful action. Gate for Phase 2. T1: operational validation, no code.
