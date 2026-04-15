# Ideation Panel Handbook — Research

> **Owning task:** #652 — P4-12: Create h-ideation-panel/SKILL.md handbook
> **Date:** 2026-04-07 **Status:** Complete

## 1. Context and Question

Task #652 requires creating `share/skills/h-ideation-panel/SKILL.md` — a consolidated handbook documenting voice characterizations, invocation patterns, Critic-loop rules, disagreement resolution, and Mediator synthesis rules. The spec lives in `.owlbear/research/thinking-companion-framework.md` §7 and §12. All six voice agents are already built (tasks #644–#650).

**Research question:** What structure, content, and conventions should the handbook follow to serve as the single reference for both Mediator and voice agents?

## 2. Sources Studied

| # | Source | Relevance | What Taken |
|---|--------|-----------|------------|
| 1 | `thinking-companion-framework.md` §7 | 1.0 | Ideation panel architecture, voice selection logic, multi-model assignment, attribution rules |
| 2 | `thinking-companion-framework.md` §12 | 1.0 | Blackboard pattern, voice reasoning cycle, Critic-loop rules (≤5 cycles), deliberation flow phases |
| 3 | Voice agent files (6 agents in `share/agents/`) | 0.95 | YAML frontmatter conventions, tool sets, persona text, I/O contracts, Critic invocation prompts |
| 4 | Voice agent research docs (6 in `.owlbear/research/`) | 0.85 | Design rationale, template replication pattern, model diversity justification |
| 5 | `ideator.agent.md` | 0.90 | Mediator invocation patterns (parallel domain opinions → sequential Pragmatist), context window economy |
| 6 | Six Thinking Hats (de Bono 1985, Wikipedia) | 0.70 | Theoretical basis for deliberate perspective-shifting with distinct roles |
| 7 | Blackboard design pattern (Lalanda 1997, Wikipedia) | 0.75 | Architectural precedent: shared workspace + specialized knowledge sources + control component |
| 8 | Existing `h-*` skills (h-quality-runner, h-agent-structure, h-mcp-kanban) | 0.80 | YAML frontmatter conventions, section structure, reference style for handbook skills |

## 3. Analysis

### Research Gate Checklist

| Gate | Verdict | Evidence |
|------|---------|----------|
| Theoretical validity | Pass | Consolidation of scattered specs into single-point-of-truth. Six Thinking Hats validates perspective-shifting; Blackboard validates shared-workspace comms. |
| Environment audit | Pass — no existing skill | Info lives across 1 spec doc + 6 agent files + 6 research docs. No consolidated reference exists. |
| Prior art | Pass (2+ sources) | Six Thinking Hats (de Bono), Blackboard pattern (Lalanda), existing Challenger agent pattern |
| Technical feasibility | Pass — pure markdown | Follows `share/skills/h-*/SKILL.md` pattern. No code. Compatible with VS Code skill auto-loading. |
| Architecture fit | Pass | Mediator reads it for invocation rules; domain opinions read it for Critic-loop rules. Referenced by `w-ideation` skill. |
| Implementation approach | Defined below | Section-by-section mapping from AC to spec sources. |

### Proposed Handbook Structure (mapped to AC)

| AC Item | Proposed Section | Primary Source |
|---------|-----------------|----------------|
| Valid YAML frontmatter | Frontmatter block | h-agent-structure conventions |
| Voice characterizations | § Voice Roster | Spec §7 + agent personas |
| Invocation patterns | § Invocation Patterns | Spec §12 deliberation flow |
| Critic-loop rules | § Critic Loop Protocol | Spec §12 voice reasoning cycle |
| Disagreement resolution | § Disagreement Resolution | Spec §12 Phase 5 |
| Mediator synthesis rules | § Synthesis Rules | Spec §12 Phase 3 + Pragmatist agent |
| References all voice agents | § Voice Roster (names) | Agent file `name:` fields |
| Voice selection logic | § Voice Selection | Spec §7 selection table + w-ideation content-split |

**Note (post-challenge):** Voice Selection Logic added as 8th section after challenger identified gap. The w-ideation research doc (task #651) content-split table explicitly assigns the "detailed signal table" to h-ideation-panel. AC item "convergence threshold" maps to the qualitative Critic exit condition ("position is solid"), not a numeric threshold — this is an AC interpretation, not invention.

### Voice Characterization Summary (from agent files)

| Voice | Agent Name | Model | Domain | Stance | Tool Count |
|-------|-----------|-------|--------|--------|------------|
| Critic | ideation-critic | GPT-5.4 | Adversarial challenge | Purely destructive — never proposes | 5 (read-only) |
| Architect | ideation-architect | Claude Opus 4.6 | System design, structure, patterns | Opinionated — spots coupling | 8 (read + write + agent) |
| Data Person | ideation-data | Claude Opus 4.6 | Data quality, schemas, ETL | Opinionated — schema-as-contract | 8 |
| End User | ideation-enduser | Claude Opus 4.6 | UX, cognitive load, clarity | Opinionated — comprehension first | 8 |
| Security Mind | ideation-security | Claude Opus 4.6 | Access control, trust, blast radius | Opinionated — defense-in-depth | 8 |
| Pragmatist | ideation-pragmatist | Claude Opus 4.6 | Synthesis, consolidation | Neutral — never advocates | 4 (read + createFile) |

### Critic-Loop Rules (from spec §12)

- Max 5 cycles per domain opinion
- Exit on: Critic says "position is solid" OR 5 cycles reached
- Critic prompt must include: "do not manufacture objections"
- Critic runs on different model (GPT-5.4) for genuine cognitive diversity
- Voice evaluates each challenge: accept (refine) or reject (stand firm + reason)

### Key Design Decision: Temperature Guidance

The spec does not use literal LLM temperature parameters. "Temperature" in the AC maps to **assertiveness/behavioral calibration**:

| Voice | Behavioral Temperature | Rationale |
|-------|----------------------|-----------|
| Critic | High (aggressive) | Must find real flaws; pull no punches |
| Domain opinions | High (opinionated) | Strong positions, not hedged summaries |
| Pragmatist | Low (neutral) | Pure synthesis, no advocacy |
| Mediator | Medium (facilitative) | Presents, doesn't advocate |

## 4. Recommendation

**Recommendation:** Proceed with handbook creation following the 7-section structure mapped above. Content is fully specified across existing sources — the task is consolidation, not invention.

**Confidence: 0.88** — all AC items map directly to existing spec sections and agent implementations. Voice selection logic (added post-challenge) fills the structural gap. "Convergence threshold" is a qualitative Critic exit condition (not numeric) — an AC interpretation, not invention.

**Tier: T1 — Autonomous.** Handbook creation. No new capability, no architecture change, no security implications.

Challenge: proceed — confidence in original adjusted from 0.90 to 0.88 after challenger identified voice selection logic gap (accepted) and convergence threshold ambiguity (accepted).

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #652 itself covers the build. Research validates feasibility and defines the structure. The task advances to backlog for architect → build execution.
