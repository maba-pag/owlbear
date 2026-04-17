---
name: w-ideation
description: "Workflow: Ideation — 6-moment thinking companion process for problem definition, panelist deliberation, and Brief handoff to pipeline"
user-invocable: false
---

# Ideation Workflow

Six-moment process for transforming fuzzy ideas into approved Briefs. The Mediator (ideator agent) drives the conversation with the user while coordinating subagent panelists and managing the Working Directory (Blackboard). Equivalent to w-orchestration for the execution pipeline.

See `h-ideation-panel` for panelist characterizations, Critic-loop rules, and invocation prompts.

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
7. Invoke `ideation-critic` standalone: "Here's the stated problem. Is this the real problem?"
8. If Critic surfaces a material issue, loop back with the user.

**Investment Tier Check (between M1 and M2):** Propose a tier (Scratch / Tool / Shared / Production) with rationale, then use askQuestions with the four tiers as options and your recommendation marked. Record confirmed tier in `decisions.md`. The tier calibrates depth for all moments that follow.

**Entry criteria:** User has stated an idea or problem.
**Exit criteria:** Problem Statement written to `context.md`; Investment Tier set; Critic check passed.

## Step 2 — M2: Outcomes — "What does winning look like?"

**Mediator mode:** Investigator. **Active subagents:** `ideation-critic` standalone (after conversation).

1. Shift from problem to desired future state.
2. Ask: "If this existed tomorrow, what's different about your day?"
3. Ask: "How would you know it's actually working?" (human-scale success indicators).
4. Identify best realistic outcome vs. minimum viable win.
5. Challenge scope against the tier: at Tool tier, 6 outcomes is 4 too many.
6. Write 2–5 concrete outcomes with success indicators to `context.md`.
7. Invoke `ideation-critic` standalone: "Here are the proposed outcomes. What's wrong with them?"

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

**Panelist Deliberation Phase (between M3 and M4):**

The Mediator pauses the user conversation and invokes the domain ideation panel. Before invoking, it tells the user which panelists it is consulting and why, and gives them a lightweight veto. Domain panelists are invoked in **parallel** (concurrent subagent calls).

See [Panelist Deliberation Flow](#panelist-deliberation-flow) below.

**Entry criteria:** `context.md` has problem + tier + outcomes.
**Exit criteria:** `context.md` has landscape appended; `synthesis.md` written by `ideation-pragmatist`.

## Step 4 — M4: Decision — "What are we doing and why?"

**Mediator mode:** Facilitative (presenting synthesis). **Active subagents:** `ideation-critic` standalone (after decision).

The Mediator shifts to **facilitative mode** for Moments 4–6 — presenting synthesis, supporting decisions, writing the Brief.

1. Read `synthesis.md` (only this, not panelist debate logs or raw research).
2. Present the panel’s findings with attribution:
   - 2–4 concrete approaches with trade-offs (surfaced by domain panelists)
   - Each option: what it is, effort/complexity, what it buys, what it gives up
   - Panelist perspectives attributed: `[ideation-architect] favors A because…`
   - Points of convergence and disagreement highlighted
3. **User decides.** Present approaches as askQuestions options with your confidence and recommendation per option. Capture the chosen approach with rationale in `decisions.md`.
4. Invoke `ideation-critic` standalone: "Here's the chosen approach. What will fail?"
5. If Critic surfaces significant concerns, be transparent with the user. They decide whether to re-invoke panelists with updated context.
   On loop-back: panelists are stateless — they read updated `context.md` + `decisions.md` and form fresh positions.

**Entry criteria:** `synthesis.md` written.
**Exit criteria:** Decision Record written to `decisions.md`; Critic check passed.

## Step 5 — M5: The Brief — "Here's the plan"

**Mediator mode:** Facilitative (synthesis → Brief). **Active subagents:** `ideation-critic` standalone (final check).

1. Synthesise `context.md` + `decisions.md` + `synthesis.md` into the Brief structure (see [Brief Artifact](#brief-artifact) below).
2. Optionally open with a success narrative: "A month from now, you run one command and…"
3. Invoke `ideation-critic` standalone: "Here's the Brief. What are we sweeping under the rug?"
4. Address any Critic findings with the user.
5. Use askQuestions to offer the user a choice: read the Brief on their own, or be walked through it section by section. See [Brief Walkthrough Protocol](#brief-walkthrough-protocol) below.
6. After walkthrough or self-review: use askQuestions for Brief approval (approve / adjust / rework options). The Brief is the **contract** between thinking and building.
7. Write approved Brief to `brief.md`.

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

## Panelist Deliberation Flow

Invoked by the Mediator between M3 and M4 after `context.md` has been written.

### Panelist Selection

| Problem Signal | Panelists Activated |
|----------------|-----------------|
| Data processing / ETL / analytics | `ideation-data`, `ideation-architect` |
| User-facing tool / interface | `ideation-enduser`, `ideation-architect` |
| Automation / scripting | `ideation-architect`, `ideation-data` (if data-heavy) |
| Sensitive data / multi-user | `ideation-security` + relevant domain |
| High tier (Shared/Production) | `ideation-security` added to any combination |
| Novel / uncharted territory | All available domain panelists |

Panelists: `ideation-architect`, `ideation-data`, `ideation-enduser`, `ideation-security`, `ideation-pragmatist`, `ideation-critic`.

### Deliberation Steps

1. Tell the user which panelists are being consulted and why. Use askQuestions for a lightweight veto before proceeding.
2. Invoke all relevant domain panelists in **parallel** (concurrent subagent calls). Each panelist:
   a. Reads `context.md` + `decisions.md` (+ optionally `research-notes.md` for deep context).
   b. Forms an initial position.
   c. Invokes `ideation-critic` internally (Critic loop ≤ 5 cycles — see `h-ideation-panel` for protocol).
   d. Writes hardened final stance to `stances/{name}.md`.
   e. Writes full debate log to `stances/{name}-debate.md`.
3. Invoke `ideation-pragmatist` (synthesizer):
   - Reads: `context.md` + `decisions.md` + all `stances/*.md` results.
   - Identifies: convergences, disagreements, recommendation.
   - Writes `synthesis.md` — the convergence artifact.
   - Disagreements are **flagged with attribution**, not resolved. Resolution is the user's job in M4.
4. (Optional) Invoke `ideation-critic` on the combined result: reads `context.md` + `synthesis.md`, catches contradictions between panelists. Appends challenges to `synthesis.md`.

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
  stances/
    architect.md          ← ideation-architect final stance (after Critic cycles)
    architect-debate.md   ← ideation-architect ↔ ideation-critic debate log
    data.md               ← ideation-data final stance
    data-debate.md        ← ideation-data ↔ ideation-critic debate log
    enduser.md            ← ideation-enduser final stance
    enduser-debate.md     ← ideation-enduser ↔ ideation-critic debate log
    security.md           ← ideation-security final stance (if activated)
    security-debate.md    ← ideation-security ↔ ideation-critic debate log
  synthesis.md            ← ideation-pragmatist synthesis of all panelist stances
  brief.md                ← Final Brief (written at user approval in M5)
```

### File Ownership (Read/Write Rules)

| Agent | Reads | Writes |
|-------|-------|--------|
| **Mediator** | `input/*`, `context.md`, `decisions.md`, `synthesis.md` | `context.md` (incremental), `decisions.md`, `brief.md` |
| **Research subagent** | `context.md`, `input/*`, codebase + web tools | `research-notes.md` (returns summary to Mediator) |
| **Domain panelist** | `context.md`, `decisions.md`, optionally `research-notes.md` | `stances/{name}.md`, `stances/{name}-debate.md` |
| **ideation-critic** (standalone) | `context.md` | Returns response to invoking agent (no direct file write) |
| **ideation-critic** (panelist-embedded) | Panelist's current draft + `context.md` reference | Returns response to invoking panelist (no direct file write) |
| **ideation-pragmatist** | `context.md`, `decisions.md`, all `stances/*.md` | `synthesis.md` |
| **ideation-critic** (optional final) | `context.md`, `synthesis.md` | Appends challenges to `synthesis.md` |
| **planner** | `brief.md` | Kanban tasks |

**Context economy rule:** The Mediator reads **only** `input/*` (at start) and the Working Directory summary files (`context.md`, `decisions.md`, `synthesis.md`) — never raw `research-notes.md`, debate logs, or individual panelist arguments. The Mediator's context window stays clean throughout the conversation.

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

## Brief Walkthrough Protocol

When the user opts for a guided walkthrough (M5 step 5), the Mediator presents each Brief section one at a time with inline metrics. This replaces the "read and approve" flow with an interactive review.

### Walkthrough Choice

Use askQuestions with two options:

- **"I'll read it myself"** — user reviews `brief.md` directly. Proceed to approval question.
- **"Walk me through it"** — Mediator presents each section with metrics. Proceed to walkthrough loop.

### Walkthrough Loop

For each Brief section (Problem, Approach, Outcomes, Scope, Decisions, Implementation Sequence, Follow-ups):

1. **Present the section text** in the conversation — blockquote or inline. Never rely on the user reading a file edit or tool output. The content being discussed must always be visible in the chat message itself.
2. **Management summary** — 1–2 sentences: what this section says and why it matters.
3. **Mediator opinion** — brief assessment: is this section strong, weak, or notable in any way? What came from the user vs. what came from research/panel?
4. **Metrics** — score three dimensions (see [Walkthrough Metrics](#walkthrough-metrics) below).
5. **askQuestions** — present metrics in the question text, with options: "Good, next section" / "Needs adjustment". Always allow freeform input.
6. If the user says "needs adjustment" or provides freeform feedback: address the concern, update the Brief section, re-present the updated text, re-score, and ask again.

**Critical rule:** Always present the section content inline in the conversation message before using askQuestions. The user must see what they're being asked about without opening a separate file. This applies to all askQuestions uses, not just Brief walkthroughs.

### Walkthrough Metrics

Three metrics scored per section:

| Metric | Scale | Definition |
|--------|-------|------------|
| **Fidelity** | 0.0–1.0 | Does this section accurately reflect what was discussed? High = directly from user's words or confirmed research. Low = paraphrased, inferred, or invented. |
| **Readiness** | 0.0–1.0 | Can a builder implement from this section without coming back to ask questions? Combines completeness (is anything missing?) and actionability (is it specific enough?). |
| **Risk** | low / medium / high | How much could go wrong if this section is slightly off? High = security, architecture, scope boundaries. Low = documentation, follow-ups. |

Present metrics in a compact single line: `Fidelity: 0.92 | Readiness: 0.85 | Risk: medium`

### Post-Walkthrough Summary

After all sections are reviewed, present a summary table of metrics across all sections. Highlight the weakest Readiness score and highest Risk section — these are the areas most likely to cause implementation questions.

| Section | Fidelity | Readiness | Risk |
|---------|----------|-----------|------|
| Problem | 0.90 | 0.85 | low |
| ... | ... | ... | ... |

Then proceed to the approval askQuestions (approve / adjust / rework).

---

## Adaptive Depth

The Mediator **always tells the user** how it is calibrating depth: "This feels straightforward at Tool tier — I'll keep the exploration light unless something unexpected comes up." Transparency is required.

| Signal | System Response |
|--------|----------------|
| Simple/clear problem + low tier | Compress moments. Combine M1–M4 into a short focused exchange. Brief is a paragraph. |
| **Trivial** change to existing project | **Skip panelist deliberation entirely.** Mediator handles problem → recommendation → task creation in one exchange. |
| Feature change to existing project | Load project context. M1–M2 compressed. Focus on M3–M4. |
| Novel/ambiguous problem + high tier | Full depth. Multiple exchanges per moment. Extended research. All available domain panelists. |
| "Just do it" | Quick restate (M1) + recommendation (M4). Protects against misalignment without forcing full depth. |

### Investment Tier Calibration

| Tier | Mindset | Depth Effect |
|------|---------|-------------|
| **Scratch** | "Just make it work for me right now" | Compressed. Minimal panelist deliberation. Brief is a paragraph. |
| **Tool** | "I'll use this regularly, it should be solid" | Standard depth. 2–3 relevant panelists. |
| **Shared** | "Others will use this" | Full depth. Skeptic added. More approach options explored. |
| **Production** | "Real environment, real stakes" | Full depth. All applicable panelists. Extended research. |

The system proposes a tier based on conversational signals between M1 and M2. Use askQuestions with tier options for confirmation.

---

## Re-Entry Protocol

When the user returns to an existing Working Directory (mid-execution modification or continuation):

1. **Load existing Working Directory:** read `context.md`, `decisions.md`, and `synthesis.md` (if present) from `.owlbear/briefs/draft-{project-name}/`.
2. **Load current board state:** check `.owlbear/kanban/` for existing tasks — show the user what is built, what is in progress, and what is planned.
3. **Determine scope of change:** use askQuestions with options — narrow (re-enter at M4 for implementation pivots) or broad (re-enter at M1 for problem reframing).
4. **Enter at the relevant moment:** re-enter at M1 for significant problem/outcome changes; re-enter at M4 for approach/scope pivots.
5. On re-deliberation: **update** `decisions.md` with the new direction. Archive obsolete tasks from the kanban board. Create new tasks for the changed direction.
6. Panelists are **stateless** on re-entry — they read updated `context.md` + `decisions.md` and form fresh positions without anchoring to prior stance.

**Re-entry entry criteria:** An existing Working Directory is found in `.owlbear/briefs/`; user references an existing project or the system detects `draft-{name}/` on start.

---

## Verification Checklist

- [ ] Step 0 completed: Working Directory initialised, `input/*` read, project type determined
- [ ] M1 complete: Problem Statement in `context.md`; Investment Tier set; standalone Critic check done
- [ ] M2 complete: 2–5 outcomes in `context.md`; standalone Critic check done
- [ ] M3 complete: landscape in `context.md`; `research-notes.md` written; panelist deliberation complete; `synthesis.md` present
- [ ] M4 complete: Decision written to `decisions.md`; standalone Critic check done; user has decided
- [ ] M5 complete: `brief.md` written; user has approved
- [ ] M5 walkthrough: if user chose walkthrough, all sections presented inline with Fidelity/Readiness/Risk metrics; summary table shown before approval
- [ ] All askQuestions uses: content being discussed is visible in the chat message (blockquote or inline), never only in a file edit or tool output
- [ ] M6 complete: planner invoked; kanban tasks created; user confirmed
- [ ] User informed of depth calibration at each tier decision
- [ ] Mediator never reads raw `research-notes.md` or debate logs directly
- [ ] All panelist perspectives attributed to the user with panelist name
