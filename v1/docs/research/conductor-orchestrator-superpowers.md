# Conductor Orchestrator Superpowers — Research

> **Owning task:** #587 — Research: Ibrahim-3d/conductor-orchestrator-superpowers
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

OwlBear needs to evaluate conductor-orchestrator-superpowers (v3.3.0) for multi-agent
delegation, orchestration patterns, and task execution logic that could improve OwlBear's
autonomous pipeline. Key question: which patterns transfer from a Claude Code prompt
framework to a PydanticAI daemon?

## 2. Sources Studied

| Source | URL | License | Relevance |
|--------|-----|---------|-----------|
| conductor-orchestrator-superpowers | <https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers> | MIT | .90 — Primary subject |
| obra/superpowers | <https://github.com/obra/superpowers> | MIT | .75 — Base framework conductor extends (72.6k stars) |
| OwlBear orchestrator agent | `.github/agents/orchestrator.agent.md` | (internal) | .85 — Existing patterns for fit analysis |

## 3. Architecture Comparison

Conductor is a **prompt engineering framework** for Claude Code. OwlBear is a **PydanticAI
daemon** with programmatic agents. This fundamental difference limits direct code reuse but
makes prompt design patterns highly transferable.

| Criterion | Conductor | OwlBear | Gap |
|-----------|-----------|---------|-----|
| **Agent creation** | Skill files loaded into LLM context | PydanticAI `Agent` instances with DI | None — different paradigm |
| **Inter-agent comms** | File-based JSONL message bus | Python objects + hooks | None — OwlBear's is native |
| **State tracking** | `metadata.json` with `loop_state` | kanban-md statuses + frontmatter | Low — kanban already sufficient |
| **Parallel dispatch** | DAG + topological levels + file locks | Wave-based parallel dispatch (max 4) | Low — both solve same problem |
| **Evaluation loop** | Plan→EvalPlan→Execute→EvalExec→Fix (max 3 cycles) | builder→reviewer→writer→auditor pipeline | Medium — OwlBear lacks formal retry cap |
| **Post-task learning** | Retrospective agent → patterns.md + errors.json | ErrorJournal (append-only JSONL) | **High** — no structured retrospective |
| **Anti-rationalization** | Tables in every agent prompt | Tables in orchestrator + reviewer | Low — extend to other agents |
| **Plan critique** | 5-pass red-team framework (plan-critiquer) | Architect does ad-hoc review | Medium — could formalize |
| **Worker templates** | Template files with placeholder substitution | PydanticAI FunctionToolset construction | None — different paradigm |
| **Board of Directors** | 5-persona deliberation with voting | Single architect gate | Low — too token-expensive for daemon |

## 4. Key Patterns Analyzed

### 4a. Retrospective Agent (HIGH value — .80 confidence)

**What:** After every completed track, extracts: what worked, what failed, patterns
discovered, error patterns, and skill improvement proposals. Writes to `patterns.md`
and `errors.json` knowledge stores.

**OwlBear fit:** OwlBear has `ErrorJournal` (append-only JSONL) but no structured
post-task retrospective. The knowledge graph + vector store could absorb retrospective
findings far more effectively than flat files. A retrospective hook on task completion
(`ON_TASK_DONE` event) could auto-trigger knowledge ingestion.

**Risk:** Token cost of analysis pass. Mitigation: run only for tasks that had fix
cycles or rejections, skip trivial tasks.

### 4b. Anti-Rationalization Tables (MEDIUM value — .70 confidence)

**What:** Every conductor agent prompt includes a "Common failure rationalizations"
table mapping excuses to correct responses. Example from verification-before-completion:
`"Should work now" → RUN the verification`, `"I'm confident" → Confidence ≠ evidence`.

**OwlBear fit:** OwlBear's orchestrator and reviewer already have these. The builder,
writer, and auditor agents could benefit from domain-specific rationalization tables.
Low effort, high defensive value.

### 4c. Structured Plan Critique (MEDIUM value — .65 confidence)

**What:** 5-pass red-team framework: gut check → assumption hunting → pre-mortem →
competitive/market blind spots → synthesis. Produces GO / GO WITH CAUTION / STOP verdict.

**OwlBear fit:** Could enhance the architect agent's backlog→todo gate with structured
critique passes. Currently the architect reviews AC and approach but doesn't do formal
assumption hunting or pre-mortem analysis. Most valuable for complex multi-task features.

### 4d. Fix-Loop with Max Retries (LOW value — .50 confidence)

**What:** Conductor tracks `fix_cycle_count` in metadata.json, enforces max 3 fix
cycles before escalating to user. Each cycle: identify failures → create fix tasks →
execute → re-evaluate.

**OwlBear fit:** OwlBear's reviewer can reject back to `todo` or `backlog`, but there's
no formal retry counter. The kanban workflow already prevents infinite loops (human sees
stuck tasks on the board). A counter would add marginal safety.

### 4e. File-Based Message Bus (NOT transferable)

**What:** JSONL queue, file locks, event files, worker status heartbeats.

**Why not:** OwlBear agents communicate via Python objects, hooks, and PydanticAI's
native message passing. A file-based bus would be a regression. This pattern exists
because Claude Code subagents are isolated LLM invocations with no shared memory.

### 4f. Board of Directors (NOT recommended)

**What:** 5 expert personas (CA, CPO, CSO, COO, CXO) deliberate in 4 phases with
voting thresholds.

**Why not:** Token-expensive (5 parallel LLM calls per decision). OwlBear's single
architect gate is sufficient for the project's scale. The multi-persona pattern could
be revisited if OwlBear grows to manage larger projects.

## 5. Research Checklist

1. **Theoretical validity** — Sound. Conductor demonstrates that structured evaluate-loop
   and retrospective learning improve autonomous agent quality. Validated by obra/superpowers
   adoption (72.6k stars) and conductor's extension of those patterns.
2. **Prior art** — obra/superpowers (MIT, 72.6k stars) and conductor (MIT, extends
   superpowers with parallel execution and board deliberation).
3. **Technical feasibility** — Retrospective agent pattern works in PydanticAI (structured
   output for pattern extraction, knowledge graph ingestion). Anti-rationalization tables
   are pure prompt text. Plan critique passes are prompt design.
4. **Architecture fit** — Retrospective → hooks system (`ON_TASK_DONE`). Rationalization
   tables → agent prompt files. Critique passes → architect agent enhancement.
5. **Implementation approach** — Retrospective: PydanticAI agent with structured output
   (`RetroFindings` model) triggered by hook, ingests into knowledge graph.
   Rationalization tables: add to builder/writer/auditor `.agent.md` files.
   Critique: add structured passes to architect agent workflow.

## 6. Follow-up Tasks

Commands below — presented for review, NOT executed.

```
kanban\kanban-md.exe create "Retrospective learning hook: post-task pattern extraction" --priority needed --tags "phase-research,scope:agent,scope:knowledge" --body "Implement a retrospective agent/hook triggered on task completion that extracts: what worked, what failed, error patterns, reusable patterns. Ingest findings into knowledge graph.\n\nInspired by conductor-orchestrator-superpowers retrospective-agent pattern.\nSee docs/research/conductor-orchestrator-superpowers.md §4a\n\nAC:\n- Hook fires on ON_TASK_DONE for tasks that had reviewer rejections or fix cycles\n- Structured output: RetroFindings(patterns: list, errors: list, improvements: list)\n- Findings ingested into knowledge graph as entities\n- Trivial tasks (no rejections) skip retrospective to save tokens"

kanban\kanban-md.exe create "Add anti-rationalization tables to builder/writer/auditor agents" --priority important --tags "phase-research,scope:copilot,docs" --body "Extend the 'Common failure rationalizations' pattern (already in orchestrator and reviewer) to builder, writer, and auditor agent prompts.\n\nInspired by conductor-orchestrator-superpowers verification-before-completion and loop-executor patterns.\nSee docs/research/conductor-orchestrator-superpowers.md §4b\n\nAC:\n- builder.agent.md has rationalization table (TDD shortcuts, scope creep)\n- writer.agent.md has rationalization table (skipping docs, rubber-stamping)\n- auditor.agent.md has rationalization table (weak evidence, confidence-without-proof)"

kanban\kanban-md.exe create "Structured plan critique passes for architect agent" --priority nice-to-have --tags "phase-research,scope:copilot" --body "Enhance architect agent with formal critique passes before approving backlog→todo:\n1. Assumption hunting (identify + challenge key assumptions)\n2. Pre-mortem (imagine failure, brainstorm causes)\n3. Scope validation (overlap check with existing tasks)\n\nInspired by conductor plan-critiquer skill.\nSee docs/research/conductor-orchestrator-superpowers.md §4c\n\nAC:\n- Architect agent workflow includes 3 critique passes\n- Each pass produces structured findings\n- Only for tasks tagged 'complex' or with >3 AC lines (simple tasks skip)"
```
