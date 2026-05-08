---
name: w-ideation-mediation
description: "Workflow: Ideation mediation — Phase 2 landscape synthesis, decisions, Brief drafting, and handoff"
user-invocable: false
---

# Ideation Mediation

Phase 2 of the ideation workflow. The mediation agent starts from the discovery handoff, owns M3-M6, orchestrates the late domain panel, applies Critic validation, supports user decisions, drafts the Brief, and hands the result to the pipeline.

Shared rules (interaction turns, decision template, handoff contract) are in `h-ideation`.

## Working Rules

- Start from the Phase 1 artifacts in a fresh context.
- Use synthesis turns to summarize findings and tensions.
- Use decision turns only when the user is actually choosing.
- Apply anchor-recall only on synthesis and decision turns.
- Treat Critic output as adversarial stress input, not truth.
- Offer the Brief walkthrough before showing any Brief content in chat.
- Explore before asking: for Phase 2 brownfield or pattern questions, check the codebase first with `Explore` subagent, `read_file`, `semantic_search`, or `grep_search`.

## Critic Validation (O15)

When Critic is invoked on the current position, validate findings before they affect the user-facing recommendation.

1. Classify each finding as `nonsense`, `minor`, or `material`.
2. Ground the classification in the actual claim and the available evidence, not in tone or force.
3. Present material findings individually.
4. Minor findings may be grouped thematically, with at most 3 findings per grouped question.
5. Do not bulk-accept Critic output.
6. Do not silently absorb Critic output.
7. Let the user reclassify or reject your assessment.
8. Record the validated outcome in `decisions.md`.

## Disclosure Ladder

Subagent material reaching the user should be disclosed in the lightest form that still supports a good decision.

Use vocabulary and phrasing patterns from `h-ideation` -> `## Communication Patterns`.

### Default Summary

- situation
- problem
- options
- recommendation
- effect

**Narrate as:** "Here's the summary first, then we can go deeper only where it helps your decision."

### Concrete Specifics

- names
- settings
- mechanism
- failure modes
- trade-offs
- verbal cue: "I can walk through the reasoning and trade-offs."

**Narrate as:** "If you want, I can walk through the reasoning and trade-offs behind this recommendation."

### Inline Verbatim Evidence

- attributed panel wording
- raw Critic wording
- quoted brownfield evidence
- verbal cue: "The specific evidence is [source] - I can show it inline."

**Narrate as:** "The specific evidence is in the architecture review notes; I can show the exact wording inline."

Use the lightest disclosure level that still supports a good decision. Never hide decision-critical detail behind a file reference alone.

## Step 0 — Phase 2 Start

1. Read `context.md`, `decisions.md`, and `research-notes.md` from the Working Directory.
2. Read `synthesis-idea-panel.md` only if it exists.
3. Confirm that the handoff is sufficient to proceed. If the Phase 1 artifacts are too thin, say so explicitly and stop for correction rather than improvising.
4. Start from a fresh-context posture: do not inherit unstated assumptions from the discovery phase.

**Entry criteria:** A discovery handoff exists.
**Exit criteria:** Phase 2 has a stable artifact base.

## Step 1 — M3: Landscape — "What exists, what's possible?"

1. Present the landscape from `research-notes.md` as a synthesis turn: what is verified, what is still uncertain, and what tensions matter.
2. If Phase 1 flagged meaningful research gaps, request targeted deep-dive research before moving on.
3. Keep attribution visible: separate verified findings from tentative implications.
4. Do not collapse the research bridge into an approach choice.

## Step 1.5 — M3.5: Conditional Proposal Round (Design It Twice)

1. Evaluate the M3 landscape for ambiguity before selecting the panel path.
2. Trigger M3.5 only when there are at least two viable approaches and no dominant option.
3. If one approach is clearly dominant, skip M3.5 and continue to Step 2 unchanged.
4. When M3.5 triggers, skip Step 2 entirely. M3.5 and Step 2 are mutually exclusive paths to `synthesis.md`.
5. Announce the shift as a user-benefit step: what is happening next and why it improves decision quality.

   **Narrate as:** "I see two viable directions, so next I'll have each one designed and compared side by side so you can choose with clearer trade-offs."
6. Dispatch all four late domain panelists in parallel regardless of the selection matrix:
   - `ideation-architect`
   - `ideation-data`
   - `ideation-enduser`
   - `ideation-security`
7. Pass a PROPOSE-mode directive in each `runSubagent` prompt payload (behavioral directive, not agent config) instructing each panelist to write a complete design proposal shaped by its domain emphasis.
8. Collect `stances/{name}-proposal.md` outputs from all four panelists.
9. Dispatch `ideation-pragmatist` with `mode=compare` so it reads proposal files plus `context.md` and `decisions.md`, then writes `synthesis.md` with:
   - divergence-only comparison matrix columns: Decision Point, architect, data, enduser, security, Tension Level
   - common ground summary
   - open questions

## Step 2 — Late Domain Panel Orchestration (Stance Path)

1. Run this step only when Step 1.5 did not trigger.
2. Introduce the reviews by purpose and angle (what checks are being run and why those checks matter) rather than by internal roster naming.

   **Narrate as:** "I'll run architecture, data, user-experience, and security reviews here so we can test structural soundness, validation risks, usability impact, and trust boundaries before choosing a direction."
3. Select panelists using the selection matrix in `h-ideation-panel` (problem signal → panelist combination). State the signal and selected roster explicitly.
4. Invoke the relevant domain panelists in parallel by default:
   - `ideation-architect`
   - `ideation-data`
   - `ideation-enduser`
   - `ideation-security`
5. Use sequential deep-dive only when panel interdependence makes the parallel pass misleading.
6. After domain panelists finish, invoke `ideation-pragmatist` in `converge` mode to write `synthesis.md`.
7. Read `synthesis.md` only. Do not read raw debate logs unless the user asks for drill-in and the decision depends on exact wording.

## Step 3 — M4: Decision — "What are we doing and why?"

1. Present `synthesis.md` in plain language with attribution.
2. For comparison-path outputs, present proposal divergences and common ground before asking for a decision.
3. Support direction choice or hybridization: the user may select one proposal or combine elements from multiple proposals.
4. When the user is making a real choice, switch to a decision turn with the full structure from `h-ideation`.
5. Record chosen and rejected options with rationale in `decisions.md`.

## Step 4 — Critic Validation Pass

Apply O15 to every Critic pass. See the Critic Validation section above for the full procedure.

1. After hybridization (or equivalent final direction selection), run two sequential `ideation-critic` passes:
   - Pass 1 (synthesis critic): read the hybridized `synthesis.md` and challenge internal consistency of the combined elements.
   - Pass 2 (result critic): read the updated `synthesis.md` plus `decisions.md` and challenge the final design on its own merits.
2. Apply O15 to both passes. See the Critic Validation section above for the full procedure.

## Step 5 — M5: The Brief — "Here's the plan"

1. Before showing any Brief content in chat, offer the walkthrough choice.
2. Draft the Brief from `context.md`, `decisions.md`, `research-notes.md`, and `synthesis.md`.
3. Apply the Disclosure Ladder in all subagent-to-user translation.
4. If the user chooses a walkthrough, present each chunk inline before asking for approval.
5. Write `brief.md` only after user approval.

## Step 6 — M6: Handoff — "Go"

1. Create the parent kanban task from the approved Brief.
2. Invoke `planner` with the canonical prefix: `Plan and create: #{parent_id} — {brief summary}`.
3. Commit the final Working Directory state: `git add .owlbear/briefs/draft-{name}/ && git commit -m "ideation: complete Phase 2 mediation for {name}"`
4. Report the handoff result to the user:
   - parent task ID and title
   - number of child tasks created by planner
   - what happens next (architect reviews, then pipeline proceeds automatically)

## Verification Checklist

- [ ] Phase 2 started from `context.md`, `decisions.md`, and `research-notes.md`.
- [ ] `synthesis-idea-panel.md` was read only when it existed.
- [ ] Synthesis turns and decision turns use different shapes (per `h-ideation`).
- [ ] Anchor-recall appears only on synthesis and decision turns.
- [ ] Critic findings are triaged as `nonsense`, `minor`, or `material` before presentation.
- [ ] No bulk Critic acceptance appears in the mediation flow.
- [ ] The Disclosure Ladder is visible in user-facing translation.
- [ ] Panelist reviews are introduced by purpose and angle (what is being checked and why), not raw agent name.
- [ ] `brief.md` is approved before handoff.
- [ ] Step 1.5 gate evaluated ambiguity (`>=2` viable approaches, no dominant option).
- [ ] M3.5 and Step 2 were treated as mutually exclusive paths to `synthesis.md`.
- [ ] When M3.5 triggered, all four late domain panelists were dispatched in parallel with PROPOSE-mode prompt directives.
- [ ] Proposal artifacts were produced at `stances/{name}-proposal.md` with the required sections.
- [ ] Pragmatist `mode=compare` produced `synthesis.md` with divergence matrix, common ground summary, and open questions.
- [ ] Post-hybridization dual Critic passes were executed and both were triaged with O15.
