---
name: w-ideation
description: "Workflow: Ideation — 6-moment thinking companion process for problem definition, voice deliberation, and Brief handoff to pipeline"
user-invocable: false
---

# Ideation Workflow

Six-moment process for transforming fuzzy ideas into approved Briefs. The Mediator (ideator agent) drives the conversation with the user while coordinating subagent voices and managing the Working Directory (Blackboard). Equivalent to w-orchestration for the execution pipeline.

See `h-voice-panel` for voice characterizations, Critic-loop rules, and invocation prompts.

## Step 0 — Setup and Entry

On agent start:

1. Check for existing Working Directory at `.owlbear/briefs/draft-{project-name}/`:
   - **None found:** Create `.owlbear/briefs/draft-new/` with `input/`, empty `context.md`, empty `decisions.md`.
   - **`draft-new/` found:** Use askQuestions to let the user choose between continuing the existing draft or starting fresh.
   - **Named draft found:** Re-entry path — see Re-Entry Protocol section below.
2. Tell user: "Drop any reference files (spreadsheets, screenshots, docs) in the `input/` folder and I'll review them."
3. Read `input/*` for any pre-placed materials.
4. Check `owlbear-project.json` and `.owlbear/briefs/` for existing projects.
5. Determine: new project vs. feature change to existing? If uncertain, use askQuestions with options for each.
6. After M1 (once project is named): rename `draft-new/` → `draft-{project-name}/`.

**Entry criteria:** User has invoked the ideator agent.
**Exit criteria:** Working Directory initialised, user materials loaded, project type determined.

## Step 1 — M1: Understanding — "What's really going on?"

**Mediator mode:** Investigator. **Active subagents:** None (standalone Critic check at end).

The Mediator is in **Investigator mode** for Moments 1–3 — restates what it heard, probes root causes, and narrows from vague to specific.

1. Receive the user's idea, pain, or request.
2. Restate what you heard; check understanding.
3. Dig into the trigger: what happened? what breaks? who's affected? what's the cost of inaction?
4. Narrow from vague to specific ("what's really going wrong?").
5. Catch disguised solutions ("that's a solution — what's the need underneath?").
6. Write Problem Statement to `context.md` once stable.
7. Invoke `critic-voice` standalone: "Here's the stated problem. Is this the real problem?"
8. If Critic surfaces a material issue, loop back with the user.

**Investment Tier Check (between M1 and M2):** Propose a tier (Scratch / Tool / Shared / Production) with rationale, then use askQuestions with the four tiers as options and your recommendation marked. Record confirmed tier in `decisions.md`. The tier calibrates depth for all moments that follow.

**Entry criteria:** User has stated an idea or problem.
**Exit criteria:** Problem Statement written to `context.md`; Investment Tier set; Critic check passed.

## Step 2 — M2: Outcomes — "What does winning look like?"

**Mediator mode:** Investigator. **Active subagents:** `critic-voice` standalone (after conversation).

1. Shift from problem to desired future state.
2. Ask: "If this existed tomorrow, what's different about your day?"
3. Ask: "How would you know it's actually working?" (human-scale success indicators).
4. Identify best realistic outcome vs. minimum viable win.
5. Challenge scope against the tier: at Tool tier, 6 outcomes is 4 too many.
6. Write 2–5 concrete outcomes with success indicators to `context.md`.
7. Invoke `critic-voice` standalone: "Here are the proposed outcomes. What's wrong with them?"

**Entry criteria:** `context.md` has Problem Statement + Tier.
**Exit criteria:** `context.md` has 2–5 outcomes with success indicators; Critic check passed.

## Step 3 — M3: Landscape — "What exists, what's possible?"

**Mediator mode:** Investigator (delegates research). **Active subagents:** Research subagent (Explore).

1. Invoke a research subagent with a focused brief: problem statement, outcomes, tier.
   The subagent performs a **codebase scan** (existing, reusable, or constraining code) and an **ecosystem scan** (tools, libraries, prior art).
   → Writes detailed findings to `research-notes.md`
   → Returns a concise landscape summary to the Mediator (context economy — Mediator does NOT read raw research).
2. Present the landscape summary to the user.
3. Append landscape summary to `context.md` (which now contains: problem, tier, outcomes, landscape).

**Voice Deliberation Phase (between M3 and M4):**

The Mediator pauses the user conversation and invokes the domain voice panel. Before invoking, it tells the user which voices it is consulting and why, and gives them a lightweight veto. Domain voices are invoked in **parallel** (concurrent subagent calls).

See [Voice Deliberation Flow](#voice-deliberation-flow) below.

**Entry criteria:** `context.md` has problem + tier + outcomes.
**Exit criteria:** `context.md` has landscape appended; `synthesis.md` written by `pragmatist-voice`.

## Step 4 — M4: Decision — "What are we doing and why?"

**Mediator mode:** Facilitative (presenting synthesis). **Active subagents:** `critic-voice` standalone (after decision).

The Mediator shifts to **facilitative mode** for Moments 4–6 — presenting synthesis, supporting decisions, writing the Brief.

1. Read `synthesis.md` (only this, not voice debate logs or raw research).
2. Present the panel's findings with attribution:
   - 2–4 concrete approaches with trade-offs (surfaced by domain voices)
   - Each option: what it is, effort/complexity, what it buys, what it gives up
   - Voice perspectives attributed: `[architect-voice] favors A because…`
   - Points of convergence and disagreement highlighted
3. **User decides.** Present approaches as askQuestions options with your confidence and recommendation per option. Capture the chosen approach with rationale in `decisions.md`.
4. Invoke `critic-voice` standalone: "Here's the chosen approach. What will fail?"
5. If Critic surfaces significant concerns, be transparent with the user. They decide whether to re-invoke voices with updated context.
   On loop-back: voices are stateless — they read updated `context.md` + `decisions.md` and form fresh positions.

**Entry criteria:** `synthesis.md` written.
**Exit criteria:** Decision Record written to `decisions.md`; Critic check passed.

## Step 5 — M5: The Brief — "Here's the plan"

**Mediator mode:** Facilitative (synthesis → Brief). **Active subagents:** `critic-voice` standalone (final check).

1. Synthesise `context.md` + `decisions.md` + `synthesis.md` into the Brief structure (see [Brief Artifact](#brief-artifact) below).
2. Optionally open with a success narrative: "A month from now, you run one command and…"
3. Invoke `critic-voice` standalone: "Here's the Brief. What are we sweeping under the rug?"
4. Address any Critic findings with the user.
5. Use askQuestions for Brief approval (approve / adjust / rework options). The Brief is the **contract** between thinking and building.
6. Write approved Brief to `brief.md`.

**Entry criteria:** `decisions.md` has chosen approach + rationale.
**Exit criteria:** `brief.md` written; user has approved.

## Step 6 — M6: Handoff — "Go"

**Mediator mode:** Facilitative (pipeline handoff). **Active subagents:** planner.

1. Invoke the **planner** subagent with `brief.md` reference: decompose into kanban tasks with dependencies.
2. Report to user: "Project X is live — N tasks created. First tasks are queued for research now."
3. Confirm on the kanban board (tasks visible).
4. Working Directory preserved as audit trail.

For **feature changes** (non-trivial): Brief content from Working Directory becomes a delta brief; tasks are added to the existing project board.

**Entry criteria:** `brief.md` approved by user.
**Exit criteria:** Kanban tasks created from Brief; user confirmed; pipeline can proceed.

---

## Voice Deliberation Flow

Invoked by the Mediator between M3 and M4 after `context.md` has been written.

### Voice Selection

| Problem Signal | Voices Activated |
|----------------|-----------------|
| Data processing / ETL / analytics | `data-voice`, `architect-voice` |
| User-facing tool / interface | `enduser-voice`, `architect-voice` |
| Automation / scripting | `architect-voice`, `data-voice` (if data-heavy) |
| Sensitive data / multi-user | `security-voice` + relevant domain |
| High tier (Shared/Production) | `security-voice` added to any combination |
| Novel / uncharted territory | All available domain voices |

Voice agents: `architect-voice`, `data-voice`, `enduser-voice`, `security-voice`, `pragmatist-voice`, `critic-voice`.

### Deliberation Steps

1. Tell the user which voices are being consulted and why. Use askQuestions for a lightweight veto before proceeding.
2. Invoke all relevant domain voices in **parallel** (concurrent subagent calls). Each voice:
   a. Reads `context.md` + `decisions.md` (+ optionally `research-notes.md` for deep context).
   b. Forms an initial position.
   c. Invokes `critic-voice` internally (Critic loop ≤ 5 cycles — see `h-voice-panel` for protocol).
   d. Writes hardened final position to `voices/{name}.md`.
   e. Writes full debate log to `voices/{name}-debate.md`.
3. Invoke `pragmatist-voice` (synthesizer):
   - Reads: `context.md` + `decisions.md` + all `voices/*.md` results.
   - Identifies: convergences, disagreements, recommendation.
   - Writes `synthesis.md` — the convergence artifact.
   - Disagreements are **flagged with attribution**, not resolved. Resolution is the user's job in M4.
4. (Optional) Invoke `critic-voice` on the combined result: reads `context.md` + `synthesis.md`, catches contradictions between voices. Appends challenges to `synthesis.md`.

---

## Blackboard Contract

The Working Directory is the shared communication channel between all agents. No agent passes raw debate through the Mediator — all communication goes through files.

### Working Directory Layout

```
.owlbear/briefs/draft-{project-name}/
  input/                  ← User reference materials (Excel, docs, screenshots, links)
  context.md              ← Problem, Outcomes, Tier, Landscape summary (incremental)
  research-notes.md       ← Detailed codebase/ecosystem findings (written by research subagent)
  decisions.md            ← User decisions as they are made (created empty at start)
  voices/
    architect.md          ← architect-voice final position (after Critic cycles)
    architect-debate.md   ← architect-voice ↔ critic-voice debate log
    data-person.md        ← data-voice final position
    data-person-debate.md ← data-voice ↔ critic-voice debate log
    enduser.md            ← enduser-voice final position
    enduser-debate.md     ← enduser-voice ↔ critic-voice debate log
    security.md           ← security-voice final position (if activated)
    security-debate.md    ← security-voice ↔ critic-voice debate log
  synthesis.md            ← pragmatist-voice synthesis of all voice results
  brief.md                ← Final Brief (written at user approval in M5)
```

### File Ownership (Read/Write Rules)

| Agent | Reads | Writes |
|-------|-------|--------|
| **Mediator** | `input/*`, `context.md`, `decisions.md`, `synthesis.md` | `context.md` (incremental), `decisions.md`, `brief.md` |
| **Research subagent** | `context.md`, `input/*`, codebase + web tools | `research-notes.md` (returns summary to Mediator) |
| **Domain Voice** | `context.md`, `decisions.md`, optionally `research-notes.md` | `voices/{name}.md`, `voices/{name}-debate.md` |
| **critic-voice** (standalone) | `context.md` | Returns response to invoking agent (no direct file write) |
| **critic-voice** (voice-embedded) | Voice's current draft + `context.md` reference | Returns response to invoking voice (no direct file write) |
| **pragmatist-voice** | `context.md`, `decisions.md`, all `voices/*.md` | `synthesis.md` |
| **critic-voice** (optional final) | `context.md`, `synthesis.md` | Appends challenges to `synthesis.md` |
| **planner** | `brief.md` | Kanban tasks |

**Context economy rule:** The Mediator reads **only** `input/*` (at start) and the Working Directory summary files (`context.md`, `decisions.md`, `synthesis.md`) — never raw `research-notes.md`, debate logs, or individual voice arguments. The Mediator's context window stays clean throughout the conversation.

---

## Brief Artifact

The Brief is the contract between thinking and building. It persists in `brief.md` in the Working Directory and is referenced by downstream pipeline agents.

### Structure

```markdown
# [Project/Feature Name]

## Investment Tier: [Scratch | Tool | Shared | Production]

## Problem
[Specific problem statement narrowed through M1]

## Outcomes
1. [Outcome with success indicator]
2. [Outcome with success indicator]
...

## Approach
[Chosen approach with rationale — not just what, but WHY]

### Alternatives Considered
- [Option B: what it was, why rejected]

## Scope
**In:** [what is being built]
**Out:** [what is deliberately excluded and why]

## Risks & Mitigations
- [Risk → mitigation strategy]

## Key Decisions
- [Decision: rationale, trade-offs accepted]

## Context
[Codebase findings, ecosystem notes, constraints from existing work]
```

### Brief Properties

- **Rough:** Not a detailed specification. Leaves room for architect and builder judgment.
- **Solved:** Core approach is clear. All major questions answered.
- **Bounded:** Explicit scope boundaries. Investment tier constrains everything.

### Pipeline Handoff

At M6, the planner decomposes `brief.md` into kanban tasks. Brief content (problem, outcomes, approach, scope) is embedded in a **parent kanban task** body. Downstream agents (researcher, architect, test-writer, builder) work from kanban tasks — the intent behind the work propagates downstream via the task body. The `brief.md` file is preserved as audit trail.

---

## Adaptive Depth

The Mediator **always tells the user** how it is calibrating depth: "This feels straightforward at Tool tier — I'll keep the exploration light unless something unexpected comes up." Transparency is required.

| Signal | System Response |
|--------|----------------|
| Simple/clear problem + low tier | Compress moments. Combine M1–M4 into a short focused exchange. Brief is a paragraph. |
| **Trivial** change to existing project | **Skip voice deliberation entirely.** Mediator handles problem → recommendation → task creation in one exchange. |
| Feature change to existing project | Load project context. M1–M2 compressed. Focus on M3–M4. |
| Novel/ambiguous problem + high tier | Full depth. Multiple exchanges per moment. Extended research. All available domain voices. |
| "Just do it" | Quick restate (M1) + recommendation (M4). Protects against misalignment without forcing full depth. |

### Investment Tier Calibration

| Tier | Mindset | Depth Effect |
|------|---------|-------------|
| **Scratch** | "Just make it work for me right now" | Compressed. Minimal voice deliberation. Brief is a paragraph. |
| **Tool** | "I'll use this regularly, it should be solid" | Standard depth. 2–3 relevant voices. |
| **Shared** | "Others will use this" | Full depth. Security voice added. More approach options explored. |
| **Production** | "Real environment, real stakes" | Full depth. All applicable voices. Extended research. |

The system proposes a tier based on conversational signals between M1 and M2. Use askQuestions with tier options for confirmation.

---

## Re-Entry Protocol

When the user returns to an existing Working Directory (mid-execution modification or continuation):

1. **Load existing Working Directory:** read `context.md`, `decisions.md`, and `synthesis.md` (if present) from `.owlbear/briefs/draft-{project-name}/`.
2. **Load current board state:** check `.owlbear/kanban/` for existing tasks — show the user what is built, what is in progress, and what is planned.
3. **Determine scope of change:** use askQuestions with options — narrow (re-enter at M4 for implementation pivots) or broad (re-enter at M1 for problem reframing).
4. **Enter at the relevant moment:** re-enter at M1 for significant problem/outcome changes; re-enter at M4 for approach/scope pivots.
5. On re-deliberation: **update** `decisions.md` with the new direction. Archive obsolete tasks from the kanban board. Create new tasks for the changed direction.
6. Voices are **stateless** on re-entry — they read updated `context.md` + `decisions.md` and form fresh positions without anchoring to prior stance.

**Re-entry entry criteria:** An existing Working Directory is found in `.owlbear/briefs/`; user references an existing project or the system detects `draft-{name}/` on start.

---

## Verification Checklist

- [ ] Step 0 completed: Working Directory initialised, `input/*` read, project type determined
- [ ] M1 complete: Problem Statement in `context.md`; Investment Tier set; standalone Critic check done
- [ ] M2 complete: 2–5 outcomes in `context.md`; standalone Critic check done
- [ ] M3 complete: landscape in `context.md`; `research-notes.md` written; voice deliberation complete; `synthesis.md` present
- [ ] M4 complete: Decision written to `decisions.md`; standalone Critic check done; user has decided
- [ ] M5 complete: `brief.md` written; user has approved
- [ ] M6 complete: planner invoked; kanban tasks created; user confirmed
- [ ] User informed of depth calibration at each tier decision
- [ ] Mediator never reads raw `research-notes.md` or debate logs directly
- [ ] All voice perspectives attributed to the user with voice name
