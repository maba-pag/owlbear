---
name: w-ideation-mediation
description: "Workflow: Ideation mediation — Phase 2 landscape synthesis, decisions, Brief drafting, and handoff"
user-invocable: false
---

# Ideation Mediation

Phase 2 of the ideation workflow. The mediation agent starts from the discovery handoff, owns M3-M6, orchestrates the late domain panel, applies Critic validation, supports user decisions, drafts the Brief, and hands the result to the pipeline.

## Working Rules

- Start from the Phase 1 artifacts in a fresh context.
- Use synthesis turns to summarize findings and tensions.
- Use decision turns only when the user is actually choosing.
- Apply anchor-recall only on synthesis and decision turns.
- Treat Critic output as adversarial stress input, not truth.
- Offer the Brief walkthrough before showing any Brief content in chat.

## Step 0 — Phase 2 Start

1. Read `context.md`, `decisions.md`, and `research-notes.md` from the Working Directory.
2. Read `synthesis-idea-panel.md` only if it exists.
3. Confirm that the handoff is sufficient to proceed. If the Phase 1 artifacts are too thin, say so explicitly and stop for correction rather than improvising.
4. Start from a fresh-context posture: do not inherit unstated assumptions from the discovery phase.

**Entry criteria:** A discovery handoff exists.
**Exit criteria:** Phase 2 has a stable artifact base.

## Step 1 — M3: Landscape Presentation and Research Follow-Up

1. Present the landscape from `research-notes.md` as a synthesis turn: what is verified, what is still uncertain, and what tensions matter.
2. If Phase 1 flagged meaningful research gaps, request targeted deep-dive research before moving on.
3. Keep attribution visible: separate verified findings from tentative implications.
4. Do not collapse the research bridge into an approach choice.

**Synthesis turn shape:** structured context header, findings, tensions, recommendation or next question.

**Structured context header:**

- current phase and moment
- current sub-topic
- prior anchor

**Anchor-recall rule:** if the current anchor differs from the prior anchor in a meaningful way, surface it explicitly before continuing.

## Step 2 — Late Domain Panel Orchestration

1. Tell the user which late-domain panelists you are invoking and why.
2. Invoke the relevant domain panelists in parallel by default:
   - `ideation-architect`
   - `ideation-data`
   - `ideation-enduser`
   - `ideation-security`
3. Use sequential deep-dive only when panel interdependence makes the parallel pass misleading.
4. After domain panelists finish, invoke `ideation-pragmatist` in `converge` mode to write `synthesis.md`.
5. Read `synthesis.md` only. Do not read raw debate logs unless the user asks for drill-in and the decision depends on exact wording.

## Step 3 — M4: Decision Support

1. Present the late-panel findings in plain language with attribution.
2. Separate convergences from disagreements.
3. When the user is making a real choice, switch to a decision turn with the full structure:
   - context
   - problem
   - proposal(s)
   - per-proposal pro
   - per-proposal con
   - per-proposal risk
   - per-proposal confidence
   - recommended option
4. Record chosen and rejected options with rationale in `decisions.md`.

## Step 4 — Critic Validation Pass (O15)

When Critic is invoked on the current position, the mediation agent must validate findings before they affect the user-facing recommendation.

Apply O15 to every Critic pass.

1. Classify each finding as `nonsense`, `minor`, or `material`.
2. Ground the classification in the actual claim and the available evidence, not in tone or force.
3. Present material findings individually.
4. Minor findings may be grouped thematically, with at most 3 findings per grouped question.
5. Do not bulk-accept Critic output.
6. Do not silently absorb Critic output.
7. Let the user reclassify or reject your assessment.
8. Record the validated outcome in `decisions.md`.

## Step 5 — M5: Brief Drafting and Disclosure Ladder

1. Before showing any Brief content in chat, offer the walkthrough choice.
2. Draft the Brief from `context.md`, `decisions.md`, `research-notes.md`, and `synthesis.md`.
3. Use the disclosure ladder in all subagent-to-user translation:
   - default summary first
   - concrete specifics when they are already decision-relevant or when the user asks
   - inline verbatim evidence only when the wording matters or the user requests it
4. Never hide decision-critical detail behind a file reference alone.
5. If the user chooses a walkthrough, present each chunk inline before asking for approval.
6. Write `brief.md` only after user approval.

## Step 6 — M6: Handoff

1. Create the parent kanban task from the approved Brief.
2. Invoke `planner` with the canonical prefix: `Plan and create: #{parent_id} — {brief summary}`.
3. Report the handoff result to the user.
4. Preserve the Working Directory as the audit trail.

## Interaction Modes

### Synthesis Turns

- Use for M3 findings and any later relay of subagent material.
- Require the structured context header and anchor-recall.
- Do not force decision scaffolding when no decision is being made.

### Decision Turns

- Use when the user is choosing.
- Require the structured context header and anchor-recall before the option framing.
- Require the full option and trade-off structure.
- Record chosen and rejected options in `decisions.md`.
- Decision entry template:
- Use this decision entry shape when mediation records the result:

```markdown
## D{N} — {YYYY-MM-DD HH:MM} — {Topic}

**Status quo:** ...
**Decision to make:** ...

**Options considered:**

- A: ...
- B: ...

**Chosen:** ...

**Rejected:**

- B because ...

**Source inputs (when relevant):**

- User: "..."
- Panel / research: ...
```

## Disclosure Ladder

### Default Summary

- situation
- problem
- options
- recommendation
- effect

### Concrete Specifics

- names
- settings
- mechanism
- failure modes
- trade-offs

### Inline Verbatim Evidence

- attributed panel wording
- raw Critic wording
- quoted brownfield evidence

Use the lightest disclosure level that still supports a good decision.

## Verification Checklist

- [ ] Phase 2 started from `context.md`, `decisions.md`, and `research-notes.md`.
- [ ] `synthesis-idea-panel.md` was read only when it existed.
- [ ] Synthesis turns and decision turns use different shapes.
- [ ] Anchor-recall appears only on synthesis and decision turns.
- [ ] Critic findings are triaged as `nonsense`, `minor`, or `material` before presentation.
- [ ] No bulk Critic acceptance appears in the mediation flow.
- [ ] The disclosure ladder is visible in user-facing translation.
- [ ] `brief.md` is approved before handoff.
