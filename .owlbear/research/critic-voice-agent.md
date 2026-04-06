# Critic Voice Agent — Research

> **Owning task:** #644 — P4-04: Create critic-voice.agent.md
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

The Ideator framework (thinking companion) requires a Critic subagent that provides genuine adversarial challenge to positions held by domain voices and the Mediator. The Critic runs on a **different model** (GPT-5.4) than all other voices (Opus) to produce cognitive diversity — not just different arguments, but fundamentally different reasoning patterns.

**Core question:** Can a single agent file serve both standalone checks (Mediator-invoked after M1/M2/M4/M5) and embedded critic loops (invoked by domain voices during deliberation)?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `.owlbear/research/thinking-companion-framework.md` §7, §12 | Internal spec | 1.0 |
| 2 | `share/agents/challenger.agent.md` | Internal pattern | 0.9 |
| 3 | VS Code custom agents docs — frontmatter fields (`model`, `user-invocable`, `disable-model-invocation`) | External docs | 0.8 |
| 4 | `share/skills/h-agent-structure/SKILL.md` — agent file structure | Internal standard | 0.8 |
| 5 | Existing agents: model field survey (16 agents) | Internal codebase | 0.7 |
| 6 | de Bono's Six Thinking Hats — adversarial perspective separation | Published methodology | 0.6 |

## 3. Analysis

### 3.1 Feasibility: Dual-scope from a single agent file

The two invocation scopes differ only in **input context**, not agent config:

| Aspect | Standalone (Mediator) | Embedded (Domain Voice) |
|--------|----------------------|------------------------|
| Invoker | ideator.agent.md | architect-voice, data-voice, etc. |
| Input | Problem/outcomes/approach/Brief + "What's wrong?" | Voice's current position + "Challenge me" |
| Reads | `context.md` from Working Dir | `context.md` + position passed in prompt |
| Returns | Challenges to Mediator (no file writes) | Challenges to invoking voice (no file writes) |
| Scope | Meta-level: wrong problem, wrong scope | Domain-level: weak position, missing trade-off |

**Finding:** Input context determines scope. Single agent file works. Confirmed by spec §7: "Scope determined by input context, not agent configuration."

### 3.2 Approach Comparison

| Option | Description | KISS | Maintainability | Spec Alignment |
|--------|-------------|------|-----------------|----------------|
| **A: Single file, dual-scope** | One `critic-voice.agent.md`, scope from input | ✓ | One file | Explicit spec requirement |
| B: Split files per scope | Separate standalone + embedded agents | ✗ | Two files, shared logic | Contradicts spec |
| C: Extend existing Challenger | Reuse `challenger.agent.md` | ✗ | Pollutes pipeline agent | Wrong model, wrong domain |

### 3.3 Key Technical Decisions

**Model:** `GPT-5.4 (copilot)` as sole model (not a fallback array). This is an architectural requirement — model diversity is the mechanism that makes adversarial critique effective. Confirmed 4 existing agents already use GPT-5.4: code-reader, curator, reviewer (as fallback), dispatcher (mini variant).

**Tools:** Read-only subset. The Critic reads `context.md` and codebase (for verification), never writes files. Mirrors Challenger's `tools: [read/readFile, read/viewImage, read/problems, search, vscode/memory]`.

**Frontmatter:** `user-invocable: false` + `disable-model-invocation: true` + `agents: []`. The Critic is invoked explicitly via `runSubagent` only.

**Exit behavior:** Prompt embeds: "If position is solid after honest examination, say so and exit. Do not manufacture objections." This prevents the adversarial persona from degenerating into reflexive opposition.

### 3.4 Challenger vs Critic — No Overlap

| Dimension | Challenger | Critic |
|-----------|-----------|--------|
| Pipeline stage | Execution (review, research) | Ideation (pre-pipeline) |
| Model | Claude Opus 4.6 | GPT-5.4 |
| Invoked by | Researcher, reviewer, architect | Domain voices, Mediator |
| Input | Task verdicts + AC + evidence | Positions, outcomes, approaches |
| Purpose | Stress-test pipeline decisions | Challenge thinking-in-progress |

These are distinct agents in different systems. No refactoring needed.

### 3.5 Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Critic manufactures objections (degrades quality) | Medium | Exit behavior in prompt + ≤5 cycle hard limit enforced by invoker |
| GPT-5.4 unavailable | Low | VS Code model fallback is handled by the IDE; could add Opus fallback but loses diversity benefit |
| Prompt too generic for dual-scope | Low | Persona + examples encode both scope patterns explicitly |

## 4. Recommendation

**Option A: Single file, dual-scope** (confidence: 0.88)

Straightforward implementation following the Challenger pattern with three key adaptations: (1) GPT-5.4 model, (2) Working Directory context instead of kanban tasks, (3) exit behavior clause. The spec is detailed enough that the agent file can be written directly from it.

Challenge: FALLBACK — challenger agent not applicable for ideation-scope research.

## 5. Follow-up Tasks

Task #644 itself moves to backlog — it is the build task. No additional follow-up tasks needed; the implementation is self-contained. The agent file has no code dependencies, no tests required (it's a `.agent.md` configuration file), and no infrastructure changes.
