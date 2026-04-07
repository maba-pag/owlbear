# Pipeline Brief Context Integration

> **Owning task:** #653 — P4-13: Update pipeline agents with Brief context
> **Date:** 2026-04-07 **Status:** Complete

## 1. Context and Question

The ideator creates a Brief artifact at M6 and embeds it in a **parent kanban task** body. The planner decomposes the Brief into child tasks. Downstream pipeline agents (researcher, architect, test-writer, builder) work on child tasks but currently have no convention for referencing the originating Brief. The "why" behind the work evaporates between handoff and execution.

**Question:** How should pipeline skills be updated so agents can optionally reference Brief context from parent tasks — without breaking the existing pipeline flow?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| S1 | Framework spec §8, §11 | `.owlbear/research/thinking-companion-framework.md` L280–345 | 1.0 |
| S2 | w-ideation SKILL — Pipeline Handoff | `share/skills/w-ideation/SKILL.md` L256–265 | 1.0 |
| S3 | Ideator agent — handoff mechanics | `share/agents/ideator.agent.md` L108–116 | .95 |
| S4 | w-orchestration SKILL | `share/skills/w-orchestration/SKILL.md` (full) | .90 |
| S5 | w-task-decomposition SKILL | `share/skills/w-task-decomposition/SKILL.md` (full) | .95 |
| S6 | r-pipeline-protocol — Reading Rules | `share/skills/r-pipeline-protocol/SKILL.md` L130–140 | .90 |
| S7 | Kanban MCP — parent field | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L291, L645 | .85 |
| S8 | w-arch-review SKILL — body reading | `share/skills/w-arch-review/SKILL.md` L15–33 | .80 |

## 3. Analysis

### 3A. Current State

| Component | Brief Awareness | Parent Task Handling |
|-----------|----------------|---------------------|
| **ideator agent** | Creates Brief, embeds in parent task body | Creates parent task at M6 |
| **planner agent** | Reads `brief.md` for decomposition | Receives parent task ID |
| **w-task-decomposition** | "Read input (free-text, plan doc)" — no explicit Brief mention | Claims parent task via `start_work` |
| **w-orchestration** | None — dispatches from board state only | N/A (never reads task bodies) |
| **r-pipeline-protocol** | None — mentions "AC, architecture notes, research pointers" | No parent-reading convention |
| **w-arch-review** | None — reads task body for AC, decomposition markers | Checks `depends_on` tasks |
| **w-research** | None — reads task body for AC | No parent awareness |

### 3B. How Brief Content Reaches Child Tasks

```
ideator → parent task (Brief in body) → planner → child tasks (own AC, no Brief)
```

**Gap:** Child tasks carry task-specific AC but lose the originating Brief context (problem, outcomes, investment tier, approach rationale, scope boundaries). The spec (S1) explicitly states: "Downstream agents work from kanban tasks — the intent behind the work propagates downstream via the task body."

The `parent` field exists in the kanban model (S7) and `create_task` supports it. When the planner creates child tasks with `parent={id}`, agents can call `show_task(parent_id)` to read the Brief.

### 3C. Option Comparison: Brief Propagation Mechanism

| Criterion | A: Parent Lookup | B: Inline Summary | C: Doc-Only |
|-----------|-----------------|-------------------|-------------|
| **Desc** | Agent reads parent task body via `show_task` when `parent` is set | Planner embeds Brief summary in each child task body | Only update skill docs to mention Brief; no mechanism change |
| **Single source of truth** | Yes — Brief lives in parent only | No — duplicated per child | N/A |
| **Extra MCP calls** | 1 per child task execution | 0 | 0 |
| **Agent changes** | Skills mention parent-read; agents already have `show_task` | Planner only | None |
| **Drift risk** | None — reads live parent | Medium — snapshot at decomposition | N/A |
| **Graceful absence** | `parent=null` → skip | No Brief section → skip | N/A |
| **KISS alignment** | Good — one call, conditional | Good — no extra calls | Best |
| **Brief content available** | Full (problem, outcomes, tier, scope) | Summary only (~3 lines) | Nothing |
| **Breaking changes** | None — parent is already optional | None | None |
| **Confidence** | **.82** | .70 | .55 |

### 3D. Recommended Approach: Hybrid (A + B elements)

**Primary:** Option A (parent lookup) for agents that benefit from full Brief context.
**Secondary:** Planner includes a one-line Brief reference in child task bodies (`Brief: see parent #{id}`).

**Implementation — skill file updates (markdown only):**

1. **w-task-decomposition** — Step 1 updated: "If the parent task body contains a `## Brief` or `## Problem` section (Brief artifact), use it to derive scope, investment tier, and approach constraints for decomposition. Include `Brief: see parent #{id}` reference in each child task body."

2. **w-orchestration** — No direct change needed. The orchestrator never reads task bodies (by design, S4). But add a note to the Context Budget section: "Brief context from the ideator's parent task is available to pipeline agents via parent task lookup. The orchestrator does not use Brief context itself."

3. **r-pipeline-protocol** — Reading Rules updated: Add Brief to the list of context sources: "Architect / builder: read task body for AC, architecture notes, research pointers, **and Brief context (via parent task, when present)**."

4. **w-arch-review** — Step 1 updated: "If the task has a `parent` field, call `show_task(parent_id)` and check for Brief sections (Problem, Outcomes, Approach, Scope, Investment Tier). Use Brief context to inform AC evaluation and builder guidance."

5. **w-research** — Step 1 (Clarify Scope): "If the task has a `parent` field, check parent task body for Brief context. Use problem statement and outcomes to focus research scope."

### 3E. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Extra `show_task` call adds latency | Low | Low | Conditional — only when `parent` is set |
| Brief sections not standardised | Low | Medium | w-ideation defines the structure; heading detection is reliable |
| Agents ignore Brief (skill text not read) | Medium | Low | Brief is additive — tasks work fine without it |
| Older tasks have no parent/Brief | N/A | None | Graceful skip when `parent=null` |

## 4. Recommendation

**Update 4 skill files** (w-task-decomposition, w-orchestration, r-pipeline-protocol, w-arch-review) plus optionally w-research to reference Brief as an optional context source via parent task lookup. The Brief is **additive** — present when ideation produced it, absent for tasks created without ideation. All references use graceful-skip patterns ("when present", "if available").

**Tier: T1 — Autonomous.** No new capability. No architecture change. Skill file documentation updates only. The mechanism (parent field + `show_task`) already exists.

**Challenge: FALLBACK — T1 documentation update from approved spec. No alternative approaches to challenge.**

Confidence: **.82**

## 5. Follow-up Tasks

| Task | Action | Description |
|------|--------|-------------|
| Update w-task-decomposition for Brief-derived scope | Build (at `research`) | Add Brief awareness to Step 1: detect Brief in parent body, include `Brief: see parent #{id}` in child tasks |
| Update w-orchestration with Brief context note | Build (at `research`) | Add Brief mention to Context Budget section as optional context available to pipeline agents |
| Update r-pipeline-protocol Reading Rules for Brief | Build (at `research`) | Add Brief context to architect/builder reading rules |
| Update w-arch-review for parent Brief lookup | Build (at `research`) | Add parent task Brief check to Step 1 codebase analysis |
