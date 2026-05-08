---
name: w-ideation-discovery
description: "Workflow: Ideation discovery — Phase 1 problem framing, early challenge, and research bridge"
user-invocable: false
---

# Ideation Discovery

Phase 1 of the ideation workflow. The discovery agent owns M1-M2, sharpens the problem and outcomes, runs the early challenge lane, curates the first research pass, and hands off to Phase 2.

Shared rules (interaction turns, decision template, handoff contract) are in `h-ideation`.

## Working Rules

- End every user-facing turn with `askQuestions`.
- Keep M1-M2 freeform unless the user is making a real choice.
- Challenge user framing by default. Agreement must be earned.
- Confirm project type early: `net-new`, `existing-feature/refactor`, or `uncertain`.
- Do not lock approach decisions in Phase 1. Phase 1 sharpens the problem and the outcomes; Phase 2 owns approach choice.
- Explore before asking: if a question is answerable from the codebase, run a targeted lookup first using `Explore` subagent, `read_file`, `semantic_search`, or `grep_search`.

## Conditional Denoise

- Use `ideation-pragmatist` in `mode=denoise` only when multiple early challenger outputs create genuine redundancy or volume.
- If challenger output is already compact, read the challenger stances directly and do not create `synthesis-idea-panel.md`.

## Step 0 — Setup and Entry

1. Check for an existing Working Directory at `.owlbear/briefs/draft-{project-name}/`.
2. If no draft exists, create `.owlbear/briefs/draft-new/` with `input/`, `context.md`, and `decisions.md`.
3. Read `input/*` for any reference material already provided.
4. Start by establishing what kind of work this is: `net-new`, `existing-feature/refactor`, or `uncertain`.
5. Tell the user this phase is for discovery only: problem, outcomes, early challenge, and research bridge.

**Entry criteria:** User has invoked the discovery phase.
**Exit criteria:** Working Directory exists and the project type is explicit.

## Step 1 — M1: Understanding — "What's really going on?"

1. Restate the user's request in plain language and check understanding.
2. Probe for trigger, breakage, affected user, cost of inaction, and hidden assumptions.
3. Catch disguised solutions and redirect to the underlying need.
4. Record the current problem statement in `context.md` once it is stable enough for subagent use.
5. Record the explicit project type in `decisions.md`.
6. Run only a lightweight brownfield suspicion check in M1. Do not trigger a full research pass yet.
7. Lightweight Critic check: once the problem statement is written to `context.md`, briefly validate it: is it actually a problem statement, not a disguised solution? Is the scope narrow enough? If not, probe further before proceeding.

**M1 turn shape:** concise status quo, what is still unclear, the next focused probe, and why that probe matters now.

**Exit criteria:** `context.md` contains a narrow problem snapshot; `decisions.md` records the project type.

## Step 1.5 — Investment Tier Check

Between M1 and M2, propose an Investment Tier from the table in `h-ideation` (Scratch / Tool / Shared / Production). Present it as a depth calibration from `h-ideation` section `Communication Patterns`: "This feels like a [Tier] problem - [plain description]. That means I'll [what tier means for depth]. Sound right?" Then present the 4 tiers as askQuestions options with your recommended tier marked. Record the confirmed tier in `decisions.md`.

The tier calibrates all subsequent moments:

- **Scratch:** Lightweight M2, skip panel, thin Brief.
- **Tool:** Standard M2, selective panel, full Brief.
- **Shared:** Full panel, research bridge required.
- **Production:** Full panel + Critic at every moment boundary.

## Step 2 — M2: Outcomes — "What does winning look like?"

1. Shift from the problem to the desired future state.
2. Define the best realistic outcome, the minimum viable win, and any obvious scope boundaries.
3. Record candidate choices and rejected directions in `decisions.md` using the decision entry template from `h-ideation`.
4. Invoke the early challenge lane at the end of M2:
   - always: `ideation-simplifier`
   - always: `ideation-firstprinciples`
   - conditional: `ideation-outsider` when the problem signal suggests tunnel vision, domain capture, or unclear user value
5. Keep early challenger output bounded. The goal is better framing and scope control, not a second design panel.
6. If the combined early-challenger output is actually redundant or noisy, invoke `ideation-pragmatist` in `denoise` mode to write `synthesis-idea-panel.md`.
7. If challenger output is already compact, skip denoise and read the challenger stances directly.
8. Lightweight Critic check: once the outcomes are written, validate: are these outcomes measurable? Do they describe end-state, not implementation steps? Is the scope boundary real or aspirational?
9. Update `context.md` with the locked outcomes and the latest active tensions.

**Exit criteria:** `context.md` contains the current outcomes; the early challenge lane has either produced direct challenger stances or an optional `synthesis-idea-panel.md` digest.

## Step 3 — Research Bridge and Phase Handoff

1. Once the problem and outcomes are sharp enough, brief the research subagent for the first substantial research pass.
2. Require `research-notes.md` to separate:
   - `Verified findings`
   - `Candidate implications`
   - `Open research questions`
3. Treat candidate implications as hypotheses only. They do not lock the approach.
4. If the work is clearly net-new, keep the first research pass narrow unless stronger brownfield signal appears.
5. Prepare the handoff to Phase 2:
   - ensure `context.md` is a narrow current-state snapshot
   - ensure `decisions.md` contains rejected options and rationale where real choices occurred
   - ensure `research-notes.md` is present and bounded
6. Commit the Working Directory: `git add .owlbear/briefs/draft-{name}/ && git commit -m "ideation: complete Phase 1 discovery for {name}"`
7. End Phase 1 with an explicit handoff message that:
   - summarises what was discovered (1–3 sentences)
   - explains whether `synthesis-idea-panel.md` exists and why
   - provides a fenced code block with the exact command to start Phase 2 in a new chat:

     ```
     /ideation-mediate .owlbear/briefs/draft-{name}/
     ```

   **Narrate as:** "The problem and outcomes are sharp. Next step: a fresh synthesis session will take these findings and work through approach options with you. Start it with: `/ideation-mediate .owlbear/briefs/draft-{name}/`"

   Use vocabulary from `h-ideation` section `Communication Patterns` and transition style from `Transition Patterns`; describe what is complete, what opens next, and how to start.

**Phase boundary rule:** discovery ends after problem/outcomes lock and research curation. It does not continue into landscape presentation or approach choice.

**Exit criteria:** `context.md`, `decisions.md`, and `research-notes.md` are committed and ready for a fresh-context Phase 2 start.

## Artifact Contract

### `context.md`

- Narrow current-state snapshot only.
- No transcript.
- No rejected-option history.
- Update at moment boundaries and after material direction changes.

### `decisions.md`

- Append-only.
- Preserve chosen and rejected options with rationale whenever a real choice is made.
- Preserve exact user wording only when the wording itself matters.
- Use the decision entry template from `h-ideation`.

### `research-notes.md`

- Phase 1 owns the first-pass research curation.
- Verified findings, candidate implications, and open questions must stay separated.

### `synthesis-idea-panel.md`

- Optional.
- Exists only when multiple early challenger outputs actually require denoise.
- Denoised digest, not a converged recommendation.

## Verification Checklist

- [ ] Project type recorded before deep research.
- [ ] Investment Tier confirmed and recorded in `decisions.md` between M1 and M2.
- [ ] `context.md` stays narrow enough for subagent read use.
- [ ] `decisions.md` records rejected options where a real choice occurred.
- [ ] Early challengers ran with the default set and conditional outsider logic.
- [ ] `research-notes.md` separates verified findings, candidate implications, and open questions.
- [ ] Phase 1 ends with a purpose-framed handoff: what is complete, what starts next, and the Phase 2 command + artifact path.
