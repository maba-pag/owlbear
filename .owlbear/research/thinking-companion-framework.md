# The Ideator — Thinking Companion Framework

> Design specification for OwlBear's user-facing goal-definition and planning system.
> Adjacent to the execution pipeline — produces a Brief that feeds the planner and orchestrator.
> Agent name: **ideator** (requires renaming kanban status "ideation" → "research")

**Status:** Design specification (approved concept, pre-implementation)
**Date:** 2026-04-05

---

## 1. Problem Statement

OwlBear's execution pipeline (research → architect → test → build → review → docs → audit) is mature. But the **intake funnel** is thin. The system assumes the user already knows what to build with reasonable clarity. Users who arrive with a fuzzy idea — "I want to automate my reports" — have no structured support for discovering what they actually need, why it matters, and how to approach it.

The existing `w-project-scoping` skill jumps from vague idea to structured definition (with acceptance criteria and tech stack) in one breath. It captures the *what* and superficially the *how*, but the **why** — who benefits, what outcome is desired, why this approach over alternatives — is compressed into a one-paragraph description that evaporates before reaching downstream agents.

## 2. Target User

An IT-minded person who is not a full-time developer but wants to build tools, analyze data, write reports, create automations.

**Key traits:**
- Thinks in **outcomes** (what effect does this create) and **outputs** (deliverables as vehicles to get there), with heavy focus on outcomes
- Needs help **structuring their thinking**, not just transcribing it
- Often doesn't know the best approach — needs the system to surface options they haven't considered
- Values **confidence** — knowing they're building the right thing before committing effort
- Sensitive to **wasted work** — building the wrong thing is worse than building slowly

## 3. Design Principles

1. **Conversation, not forms.** The user talks naturally. Structure is the system's job.
2. **Outcome-anchored.** Every deliverable traces back to a desired outcome. Disconnected work is waste.
3. **Problem before solution.** The system actively resists jumping to implementation until the problem and outcomes are settled.
4. **The system brings knowledge.** Not a scribe — it researches, surfaces alternatives, challenges assumptions.
5. **Decisions are first-class.** Every meaningful choice is captured with rationale. Context propagates downstream.
6. **Progressive depth.** A simple automation might take 5 minutes through all moments. A new project might take an hour.
7. **Clean handoff.** The transition from thinking to building is invisible to the user.
8. **Transparent-by-default.** At every decision point (tier selection, voice selection, loop-back, Brief approval), the system states what it will do, why, and gives the user a lightweight veto. The user is not dumb — they can and should see the system's reasoning and override it.

## 4. Theoretical Grounding

The framework synthesizes elements from established methodologies, adapted for human-AI interaction:

| Source | What We Use | What Doesn't Translate |
|--------|-------------|----------------------|
| **Shape Up** (Basecamp) | Appetite concept (fixed budget, variable scope); problem narrowing ("what's really going wrong?"); grab-bag detection | Six-week cycles; betting table process |
| **Opportunity Solution Trees** (Torres) | Outcome → Opportunity → Solution separation; "is there more than one way?" test for disguised solutions | Customer interview protocols (user IS the customer); formal tree visualization |
| **Working Backwards** (Amazon) | Success narrative as gut-check; outcome-first framing | Press release format; organizational process |
| **Double Diamond** (Design Council) | Two rounds of diverge-converge (problem space, then solution space) | Workshop facilitation; group dynamics |
| **Six Thinking Hats** (de Bono) | Deliberate perspective-shifting; attributed reasoning from different angles | Rigid hat sequences; formal group exercise format |
| **JTBD** (Christensen) | Focus on the "job" being hired for; outcome over feature thinking | Formal job statement syntax |

**Novel elements with no framework precedent:**
- AI as codebase-aware advisor (reads existing code during conversation)
- Real-time ecosystem scouting (searches libraries/tools during conversation)
- Continuous decision capture (decisions captured as they emerge, not at meeting endpoints)
- Seamless handoff to automated execution pipeline

## 5. Investment Tiers

The system calibrates depth and rigor based on the user's quality ambition, not calendar time. LLM-accelerated execution compresses time by 8-12x, making time estimates meaningless. What matters is how much care the work deserves.

| Tier | Mindset | Implications |
|------|---------|-------------|
| **Scratch** | "Just make it work for me right now" | Minimal error handling, no docs, hardcoded values, zero polish |
| **Tool** | "I'll use this regularly, it should be solid" | Reasonable error handling, basic docs, tested happy paths |
| **Shared** | "Others will use this, needs to be approachable" | UX matters, docs are real, edge cases handled, onboarding considered |
| **Production** | "This runs in a real environment with real stakes" | Security, monitoring, logging, deployment, testing at scale |

The system proposes a tier based on conversational signals and the user confirms or adjusts. The tier is set between Moments 1 and 2, and affects all downstream decisions: how many approaches to explore, how thorough the research, how many edge cases the architecture addresses, how polished the documentation.

## 6. The Six Moments

The thinking process moves through six moments. These are not rigid steps — they're natural stages of how thinking progresses from fuzzy to sharp. The depth of each moment scales with the investment tier and the novelty of the problem.

### Moment 1: Understanding — "What's really going on?"

**Lead:** Mediator (Investigator mode). **Active:** The Critic.

The user presents their idea, pain, or request. The system:
- Restates what it heard, checks understanding
- Digs into the trigger: what happened? what breaks? who's affected? what's the cost of inaction?
- Narrows from vague to specific (Shape Up: flip from "what could we build?" to "what's really going wrong?")
- Catches disguised solutions (OST: "that's a solution, not a problem — what's the need underneath?")

The Critic challenges the premise: "Is this actually a problem, or just an inconvenience? What's the cost of doing nothing?"

Multiple exchanges. This continues until the real problem surfaces.

**Output:** Problem Statement — concise, specific, tested against "is this the real problem or a symptom?"

### Investment Tier Check (between Moments 1 and 2)

System proposes a tier. User confirms or adjusts. "This feels like a Tool-tier problem — solid for personal use, no multi-user concerns. That means I'll focus on reliability and basic automation without over-engineering. Sound right?"

### Moment 2: Outcomes — "What does winning look like?"

**Lead:** Mediator (Investigator mode). **Active:** The Critic (standalone, after conversation).

Shift from problem to desired future state:
- "If this existed tomorrow, what's different about your day?"
- "How would you know it's actually working?" (human-scale success indicators, not acceptance criteria)
- Best realistic outcome vs. minimum viable win
- Mediator draws on broad knowledge to challenge the user's framing: "In my experience with systems like this, the outcome people actually care about is X, not Y."

After conversation settles, the Critic challenges scope: "You listed 6 outcomes. At Tool tier, that's 4 too many."

**Output:** 2-5 concrete outcomes with success indicators.

### Moment 3: Landscape — "What exists, what's possible?"

**Lead:** Mediator (delegates heavy research to avoid context bloat).

The Mediator invokes a research subagent (Explore or custom scout) with a focused brief: problem statement, outcomes, tier. The subagent:
- **Codebase scan:** searches for existing code that's relevant, reusable, or constraining
- **Ecosystem scan:** fetches tools, libraries, approaches others have used
- **Prior art:** identifies similar problems and how they've been solved
- **Writes** detailed findings to `research-notes.md` in the Working Directory
- **Returns** a concise landscape summary (the Mediator sees only this, not the raw research)

The Mediator presents the landscape summary to the user. For existing projects: "Here's how this change interacts with what's already built."

**Output:** Landscape Summary presented to user + landscape appended to `context.md` (which now contains problem, outcomes, tier, and landscape). This triggers voice deliberation. Domain voices can read `research-notes.md` for deeper detail.

**[Voice Deliberation Phase]** — Between Moment 3 and Moment 4, the Mediator pauses the user conversation and invokes the domain voice panel. Before invoking, it tells the user which voices it's consulting and why: "I'll run this past the Architect and Data Person — your problem is structural and data-heavy. Security isn't relevant at Tool tier. Want to add or remove anyone?" Each domain voice reads `context.md`, forms a position through Critic-loop refinement, and publishes to the Working Directory. The Pragmatist then synthesizes all voice results into `synthesis.md`.

### Moment 4: Decision — "What are we doing and why?"

**Lead:** Mediator (presenting voice synthesis). **Active:** The Critic (after decision).

The Mediator reads `synthesis.md` and presents the panel's findings with attribution:
- 2-4 concrete approaches with trade-offs (surfaced by domain voices)
- Each option: what it is, effort/complexity cost, what it buys, what it gives up
- Investment tier filters options (at Scratch, only the simplest matters)
- Voice perspectives attributed: "[Architect] favors A because..." "[Data Person] warns B because..."
- Points of convergence and disagreement highlighted
- **The user decides.** Rationale captured: not just "Option A" but "Option A **because** [reasoning]"

After the decision, the Critic stress-tests: "What fails? What's the maintenance burden?"
If the Critic surfaces significant concerns, the Mediator is transparent with the user (see Phase 5 loop-back pattern) and they decide together whether to re-invoke voices.

**Output:** Decision Record — chosen approach + rationale + scope (in/out) + accepted trade-offs.

### Moment 5: The Brief — "Here's the plan"

**Lead:** Mediator. **Active:** The Critic (final check).

The Mediator synthesizes everything into the Brief artifact (see Section 8):
- Problem, Outcomes, Approach (from previous moments)
- Scope boundaries, risks, key decisions with rationale
- Optionally starts with a success narrative (Working Backwards): "A month from now, you run one command and..."

The Critic does a final pass: "Is there anything we're sweeping under the rug?"

User reviews, adjusts, approves. This is the **contract** between thinking and building.

**Output:** The Brief — a persisted artifact.

### Moment 6: Handoff — "Go"

**Lead:** Mediator.

- User approves the Brief
- System decomposes into tasks (invokes planner), sets dependencies, creates kanban entries
- "Project X is live — N tasks created. First tasks are being researched now."
- The user's role as thinker is done (for now). Execution pipeline takes over.

**Output:** Tasks on the project's kanban board, decomposed from the Brief.

## 7. The Voice Panel

The Ideator uses a **Mediator + Subagent Panel** architecture. The user talks to the Mediator (the ideator agent) — a single orchestrating entity that coordinates subagent voices with distinct perspectives. All voices except the Investigator (which is an internal Mediator mode) are implemented as **separate subagents**, invoked via `runSubagent`.

### The Mediator (ideator agent)

The Mediator is the main agent the user interacts with:
- Drives the conversation through all six moments — the single user-facing voice throughout
- Internally adopts **Investigator** mode in Moments 1-3 (problem mining, outcome shaping, landscape research)
- Shifts to facilitative mode in Moments 4-6 (presenting synthesis, supporting decisions, writing Brief)
- Delegates heavy research to subagent in M3 (receives summary, not raw results)
- Invokes voice subagents between M3 and M4, and reads `synthesis.md` to present results
- Invokes the Critic at moment boundaries (after M1, M2, M4, M5) as standalone checks
- Attributes voice perspectives to the user in conversation
- Assesses investment tier, manages depth, handles transitions

### Structural Voice Subagents

| Voice | Lifecycle | Implementation | Purpose |
|-------|-----------|---------------|---------|
| **The Investigator** | Moments 1-3 | **Internal** (Mediator behavioral mode) | Problem mining. Asks "why?" relentlessly. Reframes problems. Needs full conversation context → must be internal. |
| **The Critic** | All moments — at boundaries and inside voice loops | **Always subagent** | Challenges everything: premise, approach, user's assumptions, other voices. Purely adversarial. Self-critique doesn't work — separate invocation is required for genuine adversarial reasoning. |
| **The Pragmatist** | Between M3 and M4 (synthesis phase) | **Always subagent** | Reads all voice results + context + decisions. Writes `synthesis.md`. Consolidates domain expert opinions into a coherent synthesis for the Mediator to present. |

**Why the Critic must be a subagent:** A model that just proposed "Option A is best" cannot genuinely dismantle Option A in the same context. Separate invocation with a focused adversarial prompt produces real challenges, not performative ones. This mirrors the existing Challenger agent pattern.

**Critic invocation points (standalone, Mediator-invoked — separate from voice-embedded Critic loops):**
1. After Moment 1: "Here's the stated problem. Is this the real problem?"
2. After Moment 2: "Here are the proposed outcomes. What's wrong with them?"
3. After Moment 4: "Here's the chosen approach. What will fail?"
4. After Moment 5: "Here's the Brief. What are we sweeping under the rug?"

These are **in addition to** the Critic loops inside each domain voice (see Section 12). The standalone checks catch meta-level issues (wrong problem, wrong scope). The voice-embedded loops catch domain-level issues (weak position, missing trade-off).

### Domain Voice Subagents

All domain voices are **always implemented as subagents** — never internally simulated. They are invoked between Moments 3 and 4 (the Voice Deliberation Phase), when `context.md` has been written and there is enough context for informed opinions.

| Voice | Domain | Activated For | Example Opinion |
|-------|--------|--------------|-----------------|
| **The Architect** | System design, structure, patterns | Any project involving component design or integration | "Separate what changes from what doesn't. This coupling will hurt you." |
| **The Data Person** | Data quality, validation, flows | Data processing, ETL, analytics, reporting | "Schema is the contract. Validate between steps. NaN propagation is your enemy." |
| **The End User** | Human experience, usability, clarity | Any tool that humans interact with | "If the user can't tell what happened at a glance, the whole system failed." |
| **The Security Mind** | Access control, data safety, trust | Sensitive data, multi-user, networked | "Who sees this data when it fails? What's the blast radius?" |

### Voice Selection Logic

| Problem Signal | Voices Activated |
|----------------|-----------------|
| Data processing / ETL / analytics | Data Person, Architect |
| User-facing tool / interface | End User, Architect |
| Automation / scripting | Architect, Data Person (if data involved) |
| Sensitive data / multi-user | Security Mind + relevant domain |
| High investment tier (Shared/Production) | Security Mind added to any combination |
| Novel / uncharted territory | All available domain voices |

### Multi-Model Diversity

The Critic uses a **different LLM model** from all other voices. This creates genuine cognitive diversity — a different model doesn't just find holes the first model left, it sees the problem from a fundamentally different angle. This is what makes adversarial critique effective rather than performative.

All voices: **Claude Opus 4.6 (copilot)**. Critic: **GPT-5.4 (copilot)**. Configured via the `model:` key in each agent's YAML frontmatter.

### Voice Attribution in Conversation

The Mediator attributes perspectives clearly when surfacing voice opinions:

```
[Architect] Your codebase already handles auth — reuse that module.
[Critic] But will you actually maintain auth rules when requirements change?
[End User] The login flow needs to feel instant. Users don't care about your auth architecture.
[Pragmatist] At Tool tier: reuse existing auth, skip the UX polish, add a clear error message.
```

The attribution makes it transparent which lens is active and why the conversation's perspective shifted.

## 8. The Brief: Output Artifact

The Brief is the bridge between the thinking process and the execution pipeline. It persists in the workspace and is referenced by downstream agents (planner, researcher, architect, etc.).

### Structure

```markdown
# [Project/Feature Name]

## Investment Tier: [Scratch | Tool | Shared | Production]

## Problem
[Specific problem statement, narrowed through Moment 1]

## Outcomes
1. [Outcome with success indicator]
2. [Outcome with success indicator]
...

## Approach
[Chosen approach with decision rationale — not just what, but WHY]

### Alternatives Considered
- [Option B: what it was, why rejected]
- [Option C: what it was, why rejected]

## Scope
**In:** [explicit list of what's being built]
**Out:** [explicit list of what's deliberately excluded and why]

## Risks & Mitigations
- [Risk → mitigation strategy]

## Key Decisions
- [Decision: rationale, including what was traded off]

## Context
[Relevant codebase findings, ecosystem notes, constraints inherited from existing work]
```

### Brief Properties (inspired by Shape Up)

- **Rough:** Not a detailed specification. Leaves room for downstream agents (architect, builder) to apply their judgment. No wireframes, no line-level specs.
- **Solved:** The core approach is spelled out. All major questions are answered. The direction is clear even though details aren't.
- **Bounded:** Explicit scope boundaries. What's in, what's out. The investment tier constrains everything.

## 9. Adaptive Depth

The system scales depth based on complexity signals and investment tier:

| Signal | System Response |
|--------|----------------|
| Simple/clear problem + low investment tier | Compress moments. Combine 1-4 into a short focused exchange. Brief is a paragraph. |
| Trivial change to existing project | **Skip voice deliberation entirely.** Mediator handles problem → recommendation → task creation in one exchange. (See Appendix B.) |
| Novel/ambiguous problem + high investment tier | Full depth. Multiple exchanges per moment. Extended research. Multiple option rounds. |
| Feature change to existing project | Load project context. Moments 1-2 compressed. Focus on Moments 3-4. |
| User says "just do it" | Quick restate (Moment 1) + recommendation (Moment 4). Doesn't force depth but protects against misalignment. |

The system **always tells the user** how it's calibrating: "This feels straightforward at Tool tier — I'll keep the exploration light unless something unexpected comes up."

## 10. New Project vs. Feature Change

Both use the same six-moment process. The difference is depth and starting context.

| Aspect | New Project | Feature / Change |
|--------|-------------|-----------------|
| Moment 0 (setup) | "What do you want to create?" | System loads existing Brief + codebase state |
| Moments 1-2 | Full exploration | "What's not working / what's needed?" (compressed, leverages existing context) |
| Moment 3 | Broad landscape scan | Focused on existing codebase + direct dependencies |
| Moment 4 | Fundamental approach choices | Implementation strategy choices |
| The Brief | Full document | Delta/addendum to existing Brief, or lightweight change brief |
| Handoff | New project on kanban | Tasks added to existing project board |

## 11. Relationship to OwlBear Execution Pipeline

The Ideator is **adjacent** to the execution pipeline, not part of it.

```
┌─────────────────────────────┐     ┌──────────────────────────────────┐
│         THE IDEATOR         │     │     OWLBEAR EXECUTION PIPELINE   │
│                             │     │                                  │
│  User ↔ Mediator ↔ Panel   │────→│  Brief → Planner → Kanban Tasks  │
│                             │     │  → Researcher → Architect → ...  │
│  Output: The Brief          │     │  → Test → Build → Review → Done  │
│                             │     │                                  │
│  Operates: before pipeline  │     │  Operates: after Brief approved  │
│  Coupling: Brief artifact   │     │  Coupling: kanban tasks          │
│            only             │     │   (Brief content in parent task) │
└─────────────────────────────┘     └──────────────────────────────────┘
```

**Loose coupling:** The Brief is the only contract between the two systems. The Ideator doesn't know about kanban statuses, TDD phases, or agent dispatch. The execution pipeline doesn't know about voices, moments, or investigation. They can evolve independently.

**The Brief propagates "why":** Downstream agents (researcher, architect, test-writer, builder) work from kanban tasks that carry the Brief's content. The intent behind the work — the "why" — no longer evaporates before reaching the agents who need it.

## 12. Technical Architecture

### Architecture: Blackboard Pattern with Embedded Critic

The Ideator uses a **Blackboard architecture** where a shared file system artifact (the Working Directory) serves as the communication channel between all agents. This solves the critical context window problem: the Mediator's context contains only user conversation + Pragmatist summaries, not the full debate.

**Core principle:** Agents communicate through shared files, not through the Mediator's context window.

```
User ←→ ideator.agent.md (Mediator)
         │
         ├── Internal: Investigator mode (Moments 1-3, user conversation)
         ├── Manages: Working Directory (writes context, reads synthesis)
         │
         ├── Tools: MCP kanban, project, knowledge
         ├── Tools: vscode_askQuestions (user decision points)
         │
         ├── Invokes research subagent (M3 — codebase + ecosystem scan):
         │   └── Writes research-notes.md, returns summary to Mediator
         │
         ├── Invokes domain voice subagents (each voice internally invokes critic):
         │   ├── architect-voice → reads/writes Working Dir
         │   ├── data-voice → reads/writes Working Dir
         │   ├── enduser-voice → reads/writes Working Dir
         │   └── security-voice → reads/writes Working Dir
         │
         ├── Invokes pragmatist-voice (synthesizer):
         │   └── Reads all voice results → writes synthesis.md
         │
         ├── Optional: final critic-voice on synthesis.md
         │
         ├── Invokes planner (Moment 6 — task decomposition)
         │
         └── Output: brief.md → Kanban tasks
```

### The Working Directory (Blackboard)

```
.owlbear/briefs/draft-{project-name}/
  input/                    ← User's reference materials (dropped before or at start of conversation)
                               (Excel, docs, screenshots, links — anything the user brings)
  context.md                ← Problem, Outcomes, Tier, Landscape summary
                               (populated incrementally: M1 adds problem + tier, M2 adds outcomes, M3 adds landscape)
  research-notes.md         ← Detailed codebase/ecosystem findings
                               (written by research subagent during M3)
  decisions.md              ← User decisions as they're made
                               (created empty at start, populated by Mediator after each user choice)
  voices/
    architect.md            ← Architect final position (after Critic cycles)
    architect-debate.md     ← Architect ↔ Critic debate log
    data-person.md          ← Data Person final position
    data-person-debate.md   ← Data Person ↔ Critic debate log
    enduser.md              ← End User final position
    enduser-debate.md       ← End User ↔ Critic debate log
    security.md             ← Security Mind final position (if activated)
    security-debate.md      ← Security Mind ↔ Critic debate log
  synthesis.md              ← Pragmatist synthesis of all voice results
  brief.md                  ← Final Brief (written at user approval)
```

### What Each Agent Reads and Writes

| Agent | Reads | Writes |
|-------|-------|--------|
| **Mediator** | `input/*`, `context.md`, `decisions.md`, `synthesis.md` | `context.md` (incremental), `decisions.md`, `brief.md` |
| **Research subagent** | `context.md`, `input/*`, codebase (via tools), ecosystem (via web fetch) | `research-notes.md` (returns summary to Mediator) |
| **Domain Voice** | `context.md`, `decisions.md`, optionally `research-notes.md` | `voices/{name}.md`, `voices/{name}-debate.md` |
| **Critic** (standalone, after M1/M2/M4/M5) | `context.md` | Returns response to Mediator (not direct file write) |
| **Critic** (invoked by voice) | Voice's current draft (passed in prompt) + `context.md` reference | Returns response to invoking voice (not direct file write) |
| **Pragmatist** | `context.md`, `decisions.md`, ALL `voices/*.md` results | `synthesis.md` |
| **Final Critic** (optional) | `context.md`, `synthesis.md` | Appends challenges to `synthesis.md` |
| **Planner** | `brief.md` | Kanban tasks |

**The Mediator reads only `input/*` (at start) and Working Directory summary files** (`context.md`, `decisions.md`, `synthesis.md`) — never raw research, debate logs, or individual voice arguments. Its context window stays clean throughout the conversation.

### Voice Reasoning Cycle (with Embedded Critic)

Each domain voice is a self-contained reasoning unit. The Critic is invoked as a **subagent of the voice**, not as a separate panel member. This produces deep, thorough critique of each voice's position.

```
Domain Voice invoked by Mediator:
  1. Read context.md + decisions.md
  2. Form initial opinion

  CRITIC LOOP (≤5 cycles):
    3. Invoke critic-voice: "My position is [X]. Context in context.md. Challenge me."
    4. Critic returns adversarial challenges
    5. Voice evaluates: accept challenge → refine position, OR reject → stand firm
    6. If refined: loop back to step 3 with updated position
    7. If Critic says "position is solid" or 5 cycles reached: exit loop

  8. Write voices/{name}.md (final, hardened position)
  9. Write voices/{name}-debate.md (full Critic dialogue log)
```

**Critic exit behavior:** The Critic's prompt includes: "If after honest examination you genuinely cannot find material flaws, say the position is solid and exit. Do not manufacture objections."

**Important:** By the time a voice publishes its position, it has survived 3-5 rounds of adversarial scrutiny. The Pragmatist reads battle-tested positions, not unexamined first drafts.

**Rule: Voices can ONLY invoke the Critic as a subagent.** The Critic adds genuine value because it runs on a *different model*, producing reasoning patterns the voice cannot generate itself.

### Multi-Model Assignment

All voices use **Claude Opus 4.6 (copilot)**. The Critic uses **GPT-5.4 (copilot)** for genuine model diversity — a different model producing different reasoning patterns is what makes adversarial critique effective.

Model assignment is specified per voice agent file via the `model:` key in YAML frontmatter.

### The Full Deliberation Flow

```
PHASE 1 — User Conversation (Mediator ↔ User, internal)
  Mediator reads input/* for reference materials
  Mediator talks with user (Investigator mode)
  Clarifies problem, establishes outcomes, sets tier
  Writes context.md incrementally (problem after M1, outcomes after M2)
  Standalone Critic checks after M1 and M2 (reads context.md)
  Invokes research subagent (codebase + ecosystem scan → research-notes.md)
  Appends landscape to context.md (from research summary)

PHASE 2 — Voice Deliberation (parallel)
  Mediator invokes relevant domain voices in parallel:
    Each voice: read context.md → think → Critic loop → publish
  All voices write: voices/{name}.md + voices/{name}-debate.md

PHASE 3 — Synthesis (Pragmatist subagent)
  Mediator invokes pragmatist-voice:
    Reads: context.md + decisions.md + all voices/*.md
    Identifies: convergences, disagreements, recommendation
    Writes: synthesis.md
    Disagreements are flagged with attribution, NOT resolved algorithmically.
    Resolution is the user's job (Phase 5).

PHASE 4 — Optional Final Critic
  Mediator invokes critic-voice on the combined result:
    Reads: context.md + synthesis.md
    Catches contradictions BETWEEN voices (individual critique wouldn't find)
    Appends: challenges to synthesis.md

PHASE 5 — Present to User (Mediator)
  Mediator reads: synthesis.md (ONLY this, not the full debate)
  Presents attributed summary to user:
    "Panel converged on X. [Architect] and [Data Person] disagree on Y.
    [Architect] says A because..., [Data Person] warns B because...
    Your call on Y."
  User decides → Mediator writes: decisions.md
  If user's decision contradicts a voice's premise or changes scope:
    Mediator is transparent: "Your decision changes the foundation [Architect]
    built on. I recommend re-running the panel with this new context.
    Want me to? Or should we proceed as-is?"
    User decides whether to loop back.
  On loop-back: voices are intentionally stateless — they read updated
    context.md + decisions.md and form fresh positions (no anchoring
    to prior stance).

PHASE 6 — Brief & Handoff
  Mediator writes: brief.md (from context + decisions + synthesis)
  Strips debate artifacts, keeps conclusions
  Invokes planner with brief.md reference
  Planner creates kanban tasks
```

### Context Window Economics

| Agent | Context Contains | Does NOT Contain |
|-------|-----------------|-----------------|
| **Mediator** | User conversation + input files + research summary + Working Dir summary files (context, decisions, synthesis) | Voice debates, Critic challenges, raw research data, domain arguments |
| **Research subagent** | context.md + input files + codebase/web tool results | User conversation, voice results |
| **Domain Voice** | context.md + optionally research-notes.md + its own critic debate | Other voices' debates, user conversation, input files |
| **Critic** (standalone) | context.md (read from file, grows per moment) | Other voices, user conversation |
| **Critic** (voice-embedded) | Voice's current position + context reference | Other voices, user conversation |
| **Pragmatist** | All voice results + context + decisions | Voice debate logs, user conversation, raw research, input files |

Each agent sees only what it needs. No context is duplicated through the Mediator.

### Entry Point

The user selects **ideator** in the VS Code agent picker, or invokes by name.

**Argument hint:** `[idea, problem, or feature — drop reference files in .owlbear/briefs/draft-new/input/]`

**On start:**
1. Creates `.owlbear/briefs/draft-new/` with `input/`, empty `context.md`, empty `decisions.md`
   - If `draft-new/` already exists (unfinished prior session): asks user to continue or start fresh
2. Tells user: "Drop any reference files (spreadsheets, documents, screenshots) in the input folder and I'll review them."
3. Reads `input/*` for any materials the user has already placed
4. Checks for existing project (`owlbear-project.json`, `.owlbear/briefs/`)
5. Detects whether user references existing code
6. Determines new project vs. change to existing; if uncertain, asks
7. After M1 (when project is named): renames `draft-new/` → `draft-{project-name}/`

### Agent File Structure

```
share/agents/
  ideator.agent.md             ← main agent (user-invocable, Mediator)
  critic-voice.agent.md        ← adversarial subagent (not user-invocable)
  pragmatist-voice.agent.md    ← synthesis subagent (not user-invocable)
  architect-voice.agent.md     ← domain subagent (not user-invocable)
  data-voice.agent.md          ← domain subagent (not user-invocable)
  enduser-voice.agent.md       ← domain subagent (not user-invocable)
  security-voice.agent.md      ← domain subagent (not user-invocable)

share/skills/
  w-ideation/
    SKILL.md                   ← workflow skill: 6-moment process + deliberation flow
  h-voice-panel/
    SKILL.md                   ← handbook: voice characterizations, invocation patterns, Critic-loop rules
```

### Brief Lifecycle

1. **On invocation:** Working Directory created at `.owlbear/briefs/draft-new/` with `input/`, empty `context.md`, empty `decisions.md`
2. **After M1:** Renamed to `.owlbear/briefs/draft-{project-name}/`
3. **During ideation:** `context.md` populated incrementally, voices write to `voices/`, Pragmatist writes `synthesis.md`
4. **At approval:** Mediator writes `brief.md` from context + decisions + synthesis
5. **At handoff (new project):** Brief content transferred into a **parent kanban task** (problem, outcomes, approach, scope as the task body). Planner decomposes into subtasks. Downstream agents work from kanban tasks, not from the Brief file. The Brief file is preserved as audit trail.
6. **At handoff (feature change):** For trivial changes: new task added directly to existing board, no Brief needed. For complex changes: voice deliberation produces a change brief in a new Working Directory → new parent task + subtasks.
7. **After handoff:** Working Directory preserved for audit trail. Cleaned up when the parent task is completed or archived.

### Re-entry (Mid-Execution Modification)

When the user wants to modify direction mid-execution:
1. Mediator loads existing Working Directory + reads current board state (tasks on `.owlbear/kanban/`)
2. Shows the user what's built, what's in progress, what's planned
3. Enters at the relevant Moment (usually M1 or M4) based on the scope of change
4. After re-deliberation: updates the parent task, archives obsolete tasks, creates new tasks for the changed direction

## 13. Prerequisites for Implementation

1. **Rename kanban status** "ideation" → "research" (frees the term "ideator"; more accurate for what the researcher does)
2. **Create `ideator.agent.md`** with Mediator behavior, Investigator mode, Working Directory management
3. **Create `critic-voice.agent.md`** with purely adversarial system prompt, designed to be invoked BY other voices
4. **Create `pragmatist-voice.agent.md`** with synthesis behavior, reads all voice results
5. **Create domain voice agents** (architect, data, enduser, security) with embedded Critic invocation
6. **Create `w-ideation/SKILL.md`** workflow skill defining the 6-moment process and deliberation flow
7. **Create `h-voice-panel/SKILL.md`** handbook for voice characterizations, invocation patterns, Critic-loop rules
8. **Create `.owlbear/briefs/` directory structure** for Working Directories and Brief artifacts
9. **Update `w-project-scoping`** — deprecate or refactor to delegate to ideator
10. **Configure multi-model** — set `model:` key in each voice agent's YAML frontmatter (Opus for domain voices + Pragmatist, GPT for Critic)
11. **Update pipeline agents** to optionally read Brief artifacts from `.owlbear/briefs/` for deeper context/intent (primary context comes from kanban tasks)

## 14. Resolved Design Decisions

Questions raised during design, now resolved:

1. **Re-entry:** Context-aware. Mediator loads Working Directory + board state, enters at relevant Moment. See Brief Lifecycle section.
2. **Panel extensibility:** Fixed panel (4 domain voices + Critic + Pragmatist). If new voices are needed, they are added through development, not user configuration.
3. **Voice agent model configuration:** Specified via `model:` key in agent YAML frontmatter. Example: `model: [Claude Opus 4.6 (copilot), GPT-5.4 (copilot)]`
4. **Duplicate-voice pattern:** Removed. Voices run on Opus, Critic on GPT. This provides sufficient model diversity without the cost of dual-model runs.
5. **Brief versioning:** Brief content is transferred into a parent kanban task at handoff. Downstream agents work from kanban tasks, not Brief files. The Brief file is preserved in the Working Directory as audit trail. On re-entry, the Mediator reads the current board state + Working Directory to understand what's changed.
6. **Working Directory cleanup:** Draft artifacts preserved after handoff for audit trail. Cleaned up when parent task is completed/archived.
7. **Parallelism:** Confirmed — VS Code Copilot supports concurrent `runSubagent` calls (tested up to 6). Domain voices can run in parallel during the deliberation phase.

---

## Appendix A: Example Conversation (New Project)

**User:** "I have a bunch of Python scripts that I run manually to process data for monthly reports. It works but it's fragile — if I forget a step or run things in the wrong order, the numbers are off and I don't notice until someone flags it."

**[Moment 1 — Understanding]**

**Mediator (Investigator mode):** "So the core pain is reliability — the process depends on you running things perfectly every time, and silent failures mean bad data gets through.
- When something goes wrong, how do you discover it?
- Is it the ordering that's fragile, or also the data itself?
- How many scripts, and what's the dependency chain like?"

**User:** "Usually my boss catches it. 8 scripts, some depend on each other. Sometimes input CSV format changes break things silently."

**Mediator:** "Three problems:
1. **Silent failure** — errors don't surface until a human spots bad numbers
2. **Execution fragility** — manual sequencing with no guardrails
3. **Input instability** — format changes break processing without warning

Number 1 is the real pain — the other two are causes. Does that feel right?"

**[Tier Check]**

"This feels like **Tool tier** — solid for personal use, no multi-user. I'll focus on reliability without over-engineering. Sound right?"

**[Moment 2 — Outcomes]**

"What would winning look like? If this worked perfectly tomorrow, what's different about your report delivery?"

*(Conversation continues through outcomes, landscape exploration, options, decision, Brief, and handoff as described in this framework.)*

## Appendix B: Example Conversation (Feature Change)

**User (existing project):** "Can we add Slack notifications when the pipeline fails?"

**Mediator:** "Makes sense. Who gets notified — just you, or a channel? Success notifications too, or only failures?"

**User:** "Just me, only failures."

**Mediator:** "Still Tool tier. Your pipeline already raises exceptions with clear messages. Slack webhook is a 3-line addition in the except block. One other option: a notification abstraction that supports other channels later — but at Tool tier, the webhook is right. Want me to just add this as a task?"

**User:** "Go."

**Mediator:** "Task created: 'Add Slack webhook on pipeline failure.' Added to the project board."

*(Total: under 2 minutes. Same process, compressed.)*
