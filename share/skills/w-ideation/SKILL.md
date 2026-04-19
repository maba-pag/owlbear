---
name: w-ideation
description: "Workflow: Ideation — 6-moment thinking companion process for problem definition, panelist deliberation, and Brief handoff to pipeline"
user-invocable: false
---

# Ideation Workflow

Six-moment process for transforming fuzzy ideas into approved Briefs. The Mediator (ideator agent) drives the conversation with the user while coordinating subagent panelists and managing the Working Directory (Blackboard). Equivalent to w-orchestration for the execution pipeline.

See `h-ideation-panel` for panelist characterizations, Critic-loop rules, and invocation prompts.

> **Turn-ending rule:** Every turn that elicits a user reply ends with `askQuestions`. Use `allowFreeformInput: true` for open investigative probes; use structured `options` for decisions. This rule applies to all six moments — M1–M3 investigative probes and M4–M6 facilitated decisions alike.
>
> Worked example — M1 probe: `askQuestions(title="Tell me more", questions=[{id: "q1", question: "What happened recently that made this feel urgent?", allowFreeformInput: true}])`. Use this same pattern for any investigative question at any moment.
>
> **Confidence/recommended rule:** When any `askQuestions` call presents >2 options with genuine trade-offs (not procedural navigation like "next / back"), include per-option `confidence` (0.0–1.0) and mark one option `recommended: true`. Skills are the canonical authority for this rule — it applies at every moment where the user chooses between meaningful alternatives.

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

**Turn-ending rule (applies to every M1 step that elicits a user reply):** End the turn with `askQuestions`. For open investigative probes (steps 2–5 below), use `allowFreeformInput: true` with no fixed options. The probe text goes in the question; the user's reply arrives as `freeText`. This prevents silent stalls and keeps the conversation event-driven.

1. Receive the user's idea, pain, or request.
2. Restate what you heard; check understanding. → end with `askQuestions` (freeform).
3. Dig into the trigger: what happened? what breaks? who's affected? what's the cost of inaction? → end with `askQuestions` (freeform).
4. Narrow from vague to specific ("what's really going wrong?"). → end with `askQuestions` (freeform).
5. Catch disguised solutions ("that's a solution — what's the need underneath?"). → end with `askQuestions` (freeform).
6. Write Problem Statement to `context.md` once stable.
7. Invoke `ideation-critic` standalone: "Here's the stated problem. Is this the real problem?"
8. If Critic surfaces a material issue, loop back with the user (again ending with `askQuestions`).

**Worked example — open M1 probe with freeform input:**

```
vscode_askQuestions({
  questions: [{
    header: "m1-trigger",
    question: "What was happening just before this became a problem worth solving?",
    allowFreeformInput: true
  }]
})
```

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

   **Worked example — M4 approach decision:**
   ```
   vscode_askQuestions(title="Which approach should we take?", questions=[{
     id: "approach",
     question: "[ideation-architect] favors A for simplicity; [ideation-pragmatist] warns C adds 2–3 weeks. Which path?",
     options: [
       { label: "Option A — extend existing module (low effort)", value: "a", confidence: 0.75, recommended: true },
       { label: "Option B — standalone service (medium effort)", value: "b", confidence: 0.55 },
       { label: "Option C — full rewrite (high effort)", value: "c", confidence: 0.30 }
     ],
     allowFreeformInput: true
   }])
   ```

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
5. Use askQuestions to offer the user a choice: read the Brief on their own, or be walked through it chunk by chunk. See [Brief Walkthrough Protocol](#brief-walkthrough-protocol) below.
6. After walkthrough or self-review: use askQuestions for Brief approval (approve / adjust / rework options). The Brief is the **contract** between thinking and building.
7. Write approved Brief to `brief.md`.

**Entry criteria:** `decisions.md` has chosen approach + rationale.
**Exit criteria:** `brief.md` written; user has approved.

## Step 6 — M6: Handoff — "Go"

**Mediator mode:** Facilitative (pipeline handoff). **Active subagents:** planner.

1. Invoke `owlbear-kanban/create_task` to create a **parent kanban task** with the Brief content in the task body. Capture the returned task ID.
2. Invoke the **planner** subagent with the structured prefix: `Plan and create: #{parent_id} — {brief summary}`. This puts planner in dispatch mode (auto-create subtasks, no askQuestions).
3. Report to user: "Project X is live — N tasks created. First tasks are queued for research now."
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

When the user opts for a guided walkthrough (M5 step 5), the Mediator presents each Brief chunk one at a time with inline metrics. This replaces the "read and approve" flow with an interactive review.

### Walkthrough Choice

Use askQuestions with two options:

- **"I'll read it myself"** — user reviews `brief.md` directly. Proceed to approval question.
- **"Walk me through it"** — Mediator presents each chunk with metrics. Proceed to walkthrough loop.

### Walkthrough Loop

Five topic chunks cover the entire Brief:

| Chunk | Name | Sections Covered |
|-------|------|------------------|
| 1 | **The Why** | Problem + Outcomes |
| 2 | **The How** | Approach + Alternatives Considered + Context |
| 3 | **The Boundary** | Scope (In/Out) + Key Decisions |
| 4 | **The Honesty** | Risks & Mitigations |
| 5 | **The Next Step** | Decomposition preview (summary of planned tasks and sequencing) |

For each chunk:

1. **Present the chunk content** in the conversation — blockquote or inline. Never rely on the user reading a file edit or tool output. The content being discussed must always be visible in the chat message itself.
2. **Mediator commentary** — structured across six slots (1–2 sentences each):
   - **Summary:** Restate what the chunk says in your own words.
   - **Opinion:** What's strong here? What's weak or uncertain?
   - **Decision trail:** Which user choices or panelist findings shaped this?
   - **Trade-offs:** What was accepted? What was given up or dropped?
   - **Why this shape:** Why is this the optimal form — what alternatives were rejected?
   - **Honest negatives:** What risks, gaps, or concerns remain?
3. **Metrics** — score three dimensions (see [Walkthrough Metrics](#walkthrough-metrics) below).
4. **askQuestions** — present metrics in the question text, with options: "Good, next chunk" / "Needs adjustment". Always allow freeform input.
5. If the user says "needs adjustment" or provides freeform feedback: address the concern, update the Brief, re-present the updated chunk content, re-score, and ask again.

**Critical rule:** Always present the chunk content inline in the conversation message before using askQuestions. The user must see what they're being asked about without opening a separate file. This applies to all askQuestions uses, not just Brief walkthroughs.

**Confidence/recommended rule:** When presenting options with genuine trade-offs — including the final approval options (approve / adjust / rework) — include per-option `confidence` (0.0–1.0) and mark one option `recommended: true`. Procedural navigation options ("next chunk" / "back") do not require confidence scores.

### Walkthrough Metrics

Three metrics scored per chunk:

| Metric | Scale | Definition |
|--------|-------|------------|
| **Fidelity** | 0.0–1.0 | Does this chunk accurately reflect what was discussed? High = directly from user's words or confirmed research. Low = paraphrased, inferred, or invented. |
| **Readiness** | 0.0–1.0 | Can a builder implement from this chunk without coming back to ask questions? Combines completeness (is anything missing?) and actionability (is it specific enough?). |
| **Risk** | low / medium / high | How much could go wrong if this chunk is slightly off? High = security, architecture, scope boundaries. Low = documentation, follow-ups. |

Present metrics in a compact single line: `Fidelity: 0.92 | Readiness: 0.85 | Risk: medium`

### Walkthrough Worked Example

**Chunk 1 — "The Why"** (Problem + Outcomes):

> **Problem:** The ideation loop currently presents users with 7–8 separate Brief sections one at a time. Each requires a separate review cycle, creating interaction fatigue and losing thematic coherence.
>
> **Outcomes:** After this change, walkthroughs use 5 thematic chunks. Users see related sections together, reducing context-switching. Review sessions feel like a conversation rather than a form.

**Mediator commentary:**

- **Summary:** The problem is interaction overhead from over-granular chunking; the outcome is a more coherent, less fatiguing review flow.
- **Opinion:** Strong — problem is clearly user-observable and the outcome is directly traceable. Slightly abstract on "thematic coherence" but the intent is clear.
- **Decision trail:** User reported the 8-section walkthrough felt mechanical. Pragmatist panelist confirmed fewer, richer chunks reduces decision fatigue.
- **Trade-offs:** Accepted: sections merged into theme-pairs lose fine-grained scoring granularity. Dropped: per-section restart option (now per-chunk restart).
- **Why this shape:** Five chunks matches natural Brief narrative arc (Why / How / Boundary / Honesty / Next). Fewer chunks under-group; more chunks replicates the problem.
- **Honest negatives:** "The Next Step" chunk has no source content in the current Brief structure — the Mediator must synthesise a decomposition preview rather than present existing text.

`Fidelity: 0.90 | Readiness: 0.85 | Risk: low`

### Post-Walkthrough Summary

After all chunks are reviewed, present a summary table of metrics across all chunks. Highlight the weakest Readiness score and highest Risk chunk — these are the areas most likely to cause implementation questions.

| Chunk | Name | Fidelity | Readiness | Risk |
|-------|------|----------|-----------|------|
| 1 | The Why | 0.90 | 0.85 | low |
| ... | ... | ... | ... | ... |

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

## Ad-hoc Critic Invocations

Ad-hoc Critic invocations are **additive** to the four fixed-boundary checks (after M1, M2, M4, M5). They fire at any moment, triggered by the user or the Mediator.

### User-Request Path

When the user asks "what does the Critic think?" or equivalent, the Mediator invokes `ideation-critic` standalone with the current proposal as context. Present findings with attribution and confidence.

### Mediator Self-Trigger

When a proposal changes the problem boundary, outcome set, or approach **after the corresponding fixed-boundary Critic has already run**, the Mediator MAY invoke the Critic on the changed element.

- **MAY, not MUST.** The Mediator exercises judgment — consistent with Adaptive Depth compression.
- **Rate limit:** At most one ad-hoc invocation per user turn. Batch multiple changed elements into one focused prompt.
- **Silent resolution:** If the Critic finds nothing material, the Mediator continues without surfacing the check.

### Tier Gating

| Tier | Self-trigger disposition |
|------|------------------------|
| Scratch | Skip — compressed flow, minimal Critic |
| Tool | Mediator judgment — invoke if the change is material |
| Shared / Production | Lean toward invoking |

### Recording

Ad-hoc findings follow the same treatment as fixed-boundary findings. The Mediator presents findings to the user with attribution: "[Critic] challenged this proposal — confidence {X}." If the finding influences a decision, record the *decision* in `decisions.md` with rationale citing the Critic finding.

### Worked Example

During M5 walkthrough, user proposes adding a new artifact type (`.owlbear/audit-log.md`) not discussed in M3–M4 panel deliberation. The M5 fixed-boundary Critic has already run on the Brief. The Mediator recognises this changes the outcome set after the relevant boundary. Mediator invokes `ideation-critic`: "User proposes adding an audit-log artifact to the Brief. This wasn't part of panel deliberation. What risks does this introduce?" Critic returns findings (confidence 0.45 against — artifact duplicates existing kanban activity log). Mediator presents: "[Critic] flagged overlap with the existing activity log — confidence 0.45 against adding this. Your call." User decides to drop it.

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
- [ ] M5 walkthrough: if user chose walkthrough, all chunks presented inline with Fidelity/Readiness/Risk metrics; summary table shown before approval
- [ ] All askQuestions uses: content being discussed is visible in the chat message (blockquote or inline), never only in a file edit or tool output
- [ ] M6 complete: parent kanban task created via `create_task`; planner invoked with `Plan and create: #{id}` prefix; kanban subtasks created; user confirmed
- [ ] User informed of depth calibration at each tier decision
- [ ] Mediator never reads raw `research-notes.md` or debate logs directly
- [ ] All panelist perspectives attributed to the user with panelist name
- [ ] Ad-hoc Critic invocations (if any) presented to user when material; silent resolution applied when non-material
