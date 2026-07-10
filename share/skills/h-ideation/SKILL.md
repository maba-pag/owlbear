---
name: h-ideation
description: "Handbook: Ideation shared rules — phase map, blackboard contract, interaction turns, and handoff"
user-invocable: false
---

# Ideation Handbook

Shared handbook for the ideation workflow. Phase-specific operating procedures live in:

- `w-ideation-discovery` — Phase 1
- `w-ideation-mediation` — Phase 2

Phase agents load this file for shared rules and their own phase skill for steps.

## Phase Map

| Phase               | User-facing Agent     | Owns                                                        | Primary Outputs                                                                       |
| ------------------- | --------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Phase 1 — Discovery | `ideation-discoverer` | M1-M2, early challenge lane, first research bridge          | `context.md`, `decisions.md`, `research-notes.md`, optional `synthesis-idea-panel.md` |
| Phase 2 — Mediation | `ideation-mediator`   | M3-M6, late-domain panel, Critic validation, Brief, handoff | `synthesis.md`, `brief.md`, `shaping-summary.md`, kanban parent task                |

## Moment Reference

| Moment | Name          | Tagline                               | Owner     | Mediator Mode  |
| ------ | ------------- | ------------------------------------- | --------- | -------------- |
| M1     | Understanding | "What's really going on?"              | Discovery | Investigator   |
| M2     | Outcomes      | "What does winning look like?"         | Discovery | Investigator   |
| M3     | Landscape     | "What exists, what's possible?"        | Mediation | Investigator   |
| M4     | Decision      | "What are we doing and why?"           | Mediation | Facilitative   |
| M5     | The Brief     | "Here's the plan"                      | Mediation | Facilitative   |
| M6     | Handoff       | "Go"                                   | Mediation | Facilitative   |

**Mediator modes:** Investigator (M1-M3) probes, restates, and narrows. Facilitative (M4-M6) presents synthesis, supports decisions, and writes the Brief.

## Investment Tier

Between M1 and M2, the discovery agent proposes a tier based on problem scope and durability. Record the confirmed tier in `decisions.md`. The tier calibrates depth for all moments that follow.

| Tier       | Meaning                                   | Depth                                   |
| ---------- | ----------------------------------------- | --------------------------------------- |
| Scratch    | Throwaway experiment or spike             | Lightweight M2, skip panel, thin Brief  |
| Tool       | Internal utility, single user             | Standard M2, selective panel, full Brief |
| Shared     | Multi-consumer or team artifact           | Full panel, research bridge required    |
| Production | External-facing, durability matters       | Full panel + Critic at every moment     |

## Expectation Fidelity

Expectation fidelity preserves the difference between the product the user wants and the smallest result that can pass literal criteria. The expectation signal is not a task list, implementation plan, or acceptance-criteria substitute. It is the product promise that later synthesis, Brief drafting, and planning must not silently shrink.

### Expectation Signal

Capture the expectation signal with contrastive questions. Each answer should stay compact enough for `context.md`, but concrete enough that a later Critic can detect underdelivery.

| Question | Captures | Not This |
|---|---|---|
| **What are we actually trying to give the user?** | The promised end state in user language. | Implementation approach, first milestone, task list, or AC wording. |
| **What would make it feel worth using?** | The qualities or moments that make the result feel intentional, useful, polished, powerful, relieving, or satisfying. Each quality needs a concrete behavior, interaction, or product effect. | Generic adjectives or vague polish requests. |
| **What can arrive first without pretending it is finished?** | The First Useful Step: the earliest useful delivery slice plus what remains before the promise is fulfilled. | Replacement scope. **First Useful Step is sequencing, not descoping.** |
| **What would be technically done but still wrong?** | The passable-but-misdelivered version to avoid. | A new lower target or a softened acceptance bar. |
| **What did the user knowingly give up?** | Explicitly accepted reductions, delays, or omissions. | Cuts inferred by the agent for effort, convenience, or minimum-viable logic. |

### Artifact Authority

- During discovery and mediation, `context.md` carries the living expectation signal.
- `decisions.md` records accepted trade-offs and supersedes older expectation text only when the user explicitly chooses the change.
- At Brief approval, `brief.md` becomes the binding product promise for downstream work.
- The active phase agent owns fidelity while it owns the moment: discovery through M2, mediation through Brief approval and M6. Shaper turns the promise into buildable task shape and decomposition; task splits sequence the approved Brief but do not own product trade-offs.
- Shaper output and any child tasks created during decomposition express the approved Brief; they are not a new scope authority.

### Tier-Scaled Fidelity Checks

| Tier | Expectation-fidelity checks |
|---|---|
| Scratch | 0 formal checks; keep the expectation signal lightweight or omit it when the work is truly throwaway. |
| Tool | One pre-Brief expectation-fidelity Critic check before `brief.md` is approved. |
| Shared | M2 expectation-fidelity Critic check, pre-Brief expectation-fidelity Critic check, and post-shaping expectation-fidelity Critic check. |
| Production | M2 expectation-fidelity Critic check, pre-Brief expectation-fidelity Critic check, and post-shaping expectation-fidelity Critic check. |

### Fidelity Rules

- A first useful step is valid only when it names what remains before the promise is fulfilled.
- If remaining expectation disappears from the Brief or plan, that is descoping and requires a recorded user decision.
- Simplification may split, sequence, or remove explicitly rejected ideas. It must not redefine the user's promise as the first useful step.
- KISS/YAGNI applies to implementation shape, not product deletion.
- When a Critic says an item is not necessary, evaluate whether it is wanted, not merely necessary for bare function.

## User-Facing Entry Points

### `/ideation-discover` (agent: `ideation-discoverer`)

Use for:

- raw ideas
- fuzzy problems
- overscoped asks
- ambiguous project type
- missing ideation artifacts

### `/ideation-mediate` (agent: `ideation-mediator`)

Use for:

- continuing from a completed discovery pass
- landscape synthesis
- approach choice
- Brief drafting
- kanban handoff

## Blackboard Artifacts

```text
.owlbear/briefs/draft-{project-name}/
  input/
  context.md
  decisions.md
  research-notes.md
  stances/
    architect.md
    architect-proposal.md
    data.md
    data-proposal.md
    enduser.md
    enduser-proposal.md
    firstprinciples.md
    outsider.md
    security.md
    security-proposal.md
    simplifier.md
    *-debate.md
  synthesis-idea-panel.md
  synthesis.md
  brief.md
  shaping-summary.md
```

## Shared Artifact Meanings

### `context.md`

Current-state snapshot only. Keep it narrow enough that subagents can read it quickly.

### `decisions.md`

Chosen and rejected options with rationale. This is where decision history lives.

### `research-notes.md`

First substantial research bridge from discovery. Must separate verified findings, candidate implications, and open research questions.

### `synthesis-idea-panel.md`

Optional denoised digest of the Phase 1 early challenge lane. Exists only when denoise is actually needed.

### `synthesis.md`

Late-domain panel synthesis for Phase 2.

### `brief.md`

Approved product promise for downstream planning.

### `shaping-summary.md`

M6 record of shaper output against the approved Brief: parent task, task coverage, child-task coverage when decomposition happened, expected-experience coverage, omissions, and repair actions. It proves shaping coverage; it does not supersede `brief.md` or task bodies.

### `stances/*-proposal.md`

Optional M3.5 proposal artifacts from late domain panelists. Present only when the mediator triggers the conditional Design-It-Twice proposal round.

## Shared Interaction Contract

### Investigative Turns (Investigator Mode — M1-M3)

- Default for Phase 1 M1-M2 and Phase 2 M3.
- Freeform probing is the baseline. Do not force a structured decision scaffold when the user is still clarifying the problem.
- Do not use the structured context header or anchor-recall unless the user is making a real choice or the conversation has shifted into a synthesis relay.

### Synthesis Turns

- Use when relaying research, challenger output, or panel synthesis.
- Require the structured context header:
  - current phase and moment
  - current sub-topic
  - prior anchor
- Apply anchor-recall only when the anchor has changed in a meaningful way.

### Decision Turns (Facilitative Mode — M4-M6)

- Use whenever the user is making a real choice.
- Require the structured context header and anchor-recall.
- Present options with per-option pro, con, risk, and confidence, then make the recommendation explicit.
- Record chosen and rejected options with rationale in `decisions.md`.

## Decision Entry Template

Use this shape whenever a phase agent records a real choice:

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

## Handoff Contract

Phase 1 ends only when all three handoff artifacts exist and are usable:

- `context.md`
- `decisions.md`
- `research-notes.md`

Phase 1 must end with an explicit message that names the Phase 2 prompt command, `/ideation-mediate {draft_path}`, and those artifact paths. Phase 2 starts from those files in a fresh context.

## Communication Patterns

| Internal Name | User-Visible Label | First-Mention Pattern |
|---|---|---|
| ideation-architect | architecture review | "the architecture review (checking structural soundness)" |
| ideation-data | data review | "the data review (checking schema and validation)" |
| ideation-enduser | user experience review | "the user experience review (checking usability)" |
| ideation-security | security review | "the security review (checking trust boundaries)" |
| ideation-critic | critical review | "a critical review (stress-testing for weaknesses)" |
| ideation-simplifier | simplification check | "a simplification check (is this over-engineered?)" |
| ideation-firstprinciples | first-principles check | "a first-principles check (are we solving the right problem?)" |
| ideation-pragmatist | *(never surfaced to user)* | *(synthesis agent - user sees only the synthesized result)* |
| M1 / Understanding | problem framing | "We're in the problem framing phase - what's really going on?" |
| M2 / Outcomes | outcome definition | "Now let's define what success looks like" |
| M3 / Landscape | landscape review | "Let me map what exists and what's possible" |
| M3.5 / Design It Twice | *(never announced - internal gate)* | Result only: "I see two viable approaches, let me get them designed separately" |
| M4 / Decision | approach decision | "Time to choose a direction" |
| M5 / Brief | the plan | "Here's the plan" |
| M6 / Handoff | handoff to pipeline | "Next step: turning this into concrete tasks" |
| O15 | *(never announced - internal mechanism)* | Result only: "The critical review raised a valid concern about X" |
| Investment Tier | depth/rigor calibration | "This feels like a [tier] problem - [what that means for the user]. Sound right?" |
| Disclosure Ladder | depth detail options | "I can keep this at summary level or walk through the evidence" |

**Repeated-mention rule:** First mention uses the full form with parenthetical context. Subsequent mentions use the descriptor only.

Before/After Examples

Pair 1 - Conditional gate narration

**Before:**
> "M3.5 gate: I see one dominant approach (rewrite skill with convention-based mapping + honest verification + TODO markers). No competing viable alternative. Skipping M3.5, proceeding to stance-mode panel."

**After:**
> "There's one clear approach here - rewrite the skill with convention-based mapping, honest verification, and TODO markers. I'm going to get it reviewed from multiple angles to make sure it holds up."

Pair 2 - Panel roster introduction

**Before:**
> "Invoking ideation-architect and ideation-security panelists for the late-domain panel deliberation phase. Selection based on: structural concern + trust boundary signal."

**After:**
> "I'll run this past two reviews - architecture (structural soundness) and security (trust boundaries) - because this problem has both a design question and a data-exposure question. Want to adjust?"

Pair 3 - Permission-seeking to confident announcement

**Before:**
> "Should I run the early challengers to validate scope before moving to approach selection?"

**After:**
> "Before we commit to this scope, I want to pressure-test it for hidden assumptions and over-engineering. If something's off, better to catch it now."

Pair 4 - Status narration to result narration

**Before:**
> "Invoking ideation-critic with stance payload. O15 verification: checking no panelist premise invalidated by user decision."

**After:**
> "Let me stress-test this against your earlier decisions to make sure nothing contradicts what the reviews assumed."

Pair 5 - Phase handoff

**Before:**
> "Phase 1 complete. Handoff to @ideation-mediator. Artifacts: context.md, decisions.md, research-notes.md at .owlbear/briefs/draft-foo/."

**After:**
> "The problem and outcomes are sharp. Next step: a fresh synthesis session will take these findings and work through approach options with you. Start it with: /ideation-mediate .owlbear/briefs/draft-foo/"

Pair 6 - Non-happy-path: correction/rerun

**Before:**
> "Re-invoking ideation-architect with updated constraint from D4. Previous stance invalidated by scope change."

**After:**
> "Your last decision changes what the architecture review assumed. I need to re-run that review with the updated constraint - it'll take one more pass."

### Narration Principles

- **Results, not mechanisms.** Internal verification stays silent; narrate what was found, not protocol machinery.
- **Conditional gates are never announced.** Surface only the outcome and user relevance, not internal gate names.
- **Purpose before process.** Explain why this step helps the user before describing what happens next.
- **Labels stay visible with context (D4).** On first mention, keep labels visible with context so the meaning is immediate.
- **Attribution by name with explanation (D6).** Attribute findings to the review by name and explain what that review checks.
- **Compliance is explanation quality.** Strong protocol behavior means clear purpose, plain language, and user benefit.

### Transition Patterns

| Transition | Pattern | Why |
|---|---|---|
| Problem clear -> outcomes | "The problem is clear. Now let's define what success looks like - what would make this worth doing, and how would we know it worked?" | Carries momentum while making success criteria explicit. |
| Outcomes -> challenge | "Before we lock these outcomes, I'm going to pressure-test them from a couple of angles - checking for hidden assumptions and scope that could bite us later." | Introduces challenge work as risk reduction, not ceremony. |
| Landscape -> decision (one approach) | "There's one clear approach here. I'm going to get it reviewed from multiple angles before we commit." | Keeps confidence grounded by independent review. |
| Landscape -> decision (alternatives) | "I see two viable directions, each with real trade-offs. Let me lay them out so you can decide which fits." | Sets up a real choice with trade-off framing. |
| Brief approved -> handoff | "The plan is solid. Next step: I'll turn this into concrete implementation tasks." | Signals execution readiness and immediate next action. |
| Tier calibration | "This feels like a [Tier] problem - [plain description]. That means I'll [what tier means for depth]. Sound right?" | Aligns rigor with user intent before more work. |

### Boundary Heuristic

| Situation | Agent behavior | Why |
|---|---|---|
| Procedural action (reviewing, validating) | Announce with purpose: "I'm going to get this reviewed from three angles." | User does not need to approve quality checks. |
| Direction/scope change | Offer a genuine choice with trade-offs. | Direction and scope remain user-owned decisions. |
| Depth change | Signal availability: "I can walk through the reasoning." | Respects time without gatekeeping detail. |
| Correction | State what happened, what it means, then state intent. | Keeps trust high and next steps clear. |

### Depth-Control Verbal Cues

| Level | Existing name | Verbal cue to signal availability |
|---|---|---|
| Default | Default Summary | Always shown - no cue needed. |
| Concrete | Concrete Specifics | "I can walk through the reasoning / trade-offs." |
| Verbatim | Inline Verbatim Evidence | "The specific evidence is [source] - I can show it inline." |

## Cross-References

- `w-ideation-discovery` — Phase 1 operating procedure
- `w-ideation-mediation` — Phase 2 operating procedure
- `h-ideation-panel` — panelist-facing rules for early challengers, late domain panelists, Critic loops, and Pragmatist modes
