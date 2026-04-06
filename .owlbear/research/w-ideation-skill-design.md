# w-ideation SKILL.md — Research

> **Owning task:** #651 — P4-11: Create w-ideation/SKILL.md workflow
> **Date:** 2026-04-07  **Status:** Complete

## 1. Context and Question

Task #651 creates `share/skills/w-ideation/SKILL.md` — the primary workflow skill invoked by the ideator agent (Mediator). Equivalent to `w-orchestration` for the execution pipeline. The spec is `.owlbear/research/thinking-companion-framework.md` (Sections 6, 7, 8, 10, 12). All dependency tasks (#646–#650: voice agents) are archived.

**Key question:** What structure and content should the SKILL.md use, given that (a) the spec is 600+ lines but the skill must be concise, and (b) voice panel details belong in the sibling `h-voice-panel` (#652)?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|-----------|------|
| 1 | `.owlbear/research/thinking-companion-framework.md` §6,7,8,10,12 | 1.0 | Canonical spec — moments, voices, blackboard, Brief, re-entry |
| 2 | `share/skills/w-orchestration/SKILL.md` | 0.9 | Structural template — step-based skill with verification checklist |
| 3 | `share/agents/ideator.agent.md` | 0.9 | Live agent — M1–M6 numbering, entry point logic, context economy |
| 4 | `share/skills/w-research/SKILL.md` | 0.7 | Step pattern reference — setup → steps → deliverables → advance |
| 5 | `share/skills/h-agent-structure/SKILL.md` | 0.7 | YAML frontmatter rules, skill naming conventions (w- prefix) |

## 3. Analysis

### 3.1 Moment Numbering Discrepancy

| Source | Numbering | Setup Phase |
|--------|-----------|-------------|
| AC (#651) | M0–M5 (6 moments) | M0 is setup |
| Spec §6 | Moment 1–6 (6 moments) | "Moment 0 (setup)" in §10 table |
| ideator.agent.md | M1–M6 (6 moments) | "Entry Point Logic" (unnumbered) |

The AC says M0–M5 but both the spec and the live agent use M1–M6 + unnamed setup. Best resolution: **the SKILL.md uses the spec's M1–M6 plus a Step 0 for setup** (matching w-orchestration's Step 0 pattern). This preserves consistency with the approved spec and the live agent while the AC's M0–M5 is re-interpreted as "6 moments including setup."

**Risk:** AC literal compliance says M0–M5. Mitigation: the architect can override to M1–M6 if alignment with the spec and agent outweighs literal AC wording.

### 3.2 Content Split: w-ideation vs. h-voice-panel (#652)

| Content | w-ideation | h-voice-panel |
|---------|------------|---------------|
| 6-moment process flow | ✓ | — |
| Entry/exit criteria per moment | ✓ | — |
| Deliberation flow (high-level) | ✓ (which voices, when, sequencing) | — |
| Voice characterizations | — | ✓ |
| Critic-loop mechanics | — | ✓ |
| Invocation patterns + prompt templates | — | ✓ |
| Voice selection matrix | ✓ (decision rules) | ✓ (detailed signal table) |
| Blackboard contract | ✓ | — |
| Brief artifact structure | ✓ | — |
| Adaptive depth | ✓ | — |
| Re-entry protocol | ✓ | — |

### 3.3 Proposed SKILL.md Structure

```
YAML frontmatter
# Ideation (intro paragraph)
## Step 0 — Setup
## Step 1 — Understanding (M1)
## Step 2 — Outcomes (M2)
## Step 3 — Landscape & Deliberation (M3)
## Step 4 — Decision (M4)
## Step 5 — Brief (M5)
## Step 6 — Handoff (M6)
## Blackboard Contract (table: agent → reads → writes)
## Brief Artifact (structure template)
## Adaptive Depth (table: signal → response)
## Re-entry Protocol
## Voice Selection (table: problem signal → voices)
## Verification Checklist
```

**Line budget estimate:** ~180–220 lines. Tables keep it concise. Cross-references to `h-voice-panel` for voice details and `h-mcp-kanban` for kanban operations.

### 3.4 Key Builder Decisions

| Decision | Recommendation | Confidence |
|----------|---------------|------------|
| Numbering convention | Follow spec M1–M6 + Step 0 setup | .85 |
| Voice deliberation placement | Embed in Step 3 (after landscape, before M4) | .90 |
| Brief structure: inline vs. reference | Inline template (concise) — agent already references the skill | .90 |
| Adaptive depth: full table from §9 | Compressed to 5-row table (signal → response) | .85 |
| Re-entry: full protocol from §12 | 4-step numbered list, ≤15 lines | .90 |

## 4. Recommendation

**Structure the SKILL.md following the w-orchestration step-based pattern.** Use Step 0 (setup) + Steps 1–6 for M1–M6, with tables for Blackboard contract, adaptive depth, voice selection, and Brief structure. Cross-reference h-voice-panel (#652) for voice mechanics. Target ~200 lines.

**Overall confidence: .88**

Challenge: FALLBACK — near-trivial structural extraction from approved spec; recommendation is the only viable approach.

**Tier classification: T1 — Autonomous.** This is creating a workflow skill file from an already-approved design spec. No new capability, no architecture change, no security impact.

## 5. Follow-up Tasks

| Task | Rationale |
|------|-----------|
| Align ideator.agent.md moment numbering with SKILL.md | After #651 is built, the agent may need section header updates if SKILL.md numbering diverges |

Follow-up deferred: the numbering alignment is minor and will be evident during #651's review phase. No separate task warranted unless the architect flags it.
