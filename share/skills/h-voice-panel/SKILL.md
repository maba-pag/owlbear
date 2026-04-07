---
name: h-voice-panel
description: "Handbook: Voice panel — voice characterizations, invocation patterns, Critic-loop protocol, and synthesis rules"
user-invocable: false
---

# Voice Panel Handbook

Reference for the ideator agent's voice panel architecture. Consolidates voice characterizations, invocation patterns, Critic-loop protocol, disagreement resolution, and Mediator synthesis rules from the thinking-companion-framework spec (§7, §12) and all six voice agent files.

## Voice Roster

All six panel voices are separate subagents invoked by the Mediator (ideator agent). The Investigator is an internal Mediator behavioral mode and is not listed here.

| Voice | Agent Name | Domain | Persona | Behavioral Calibration |
|-------|-----------|--------|---------|----------------------|
| The Critic | `critic-voice` | Adversarial challenge | Relentless adversary — exposes weaknesses, never proposes solutions | High assertiveness (aggressive) — pulls no punches |
| The Architect | `architect-voice` | System design, structure, patterns | Opinionated technician — spots coupling and enforces clean separations | High assertiveness (opinionated) — strong structural positions |
| The Data Person | `data-voice` | Data quality, schemas, ETL, validation | Schema-first thinker — treats schema as contract, hunts NaN propagation | High assertiveness (opinionated) — schema-as-contract stance |
| The End User | `enduser-voice` | Human experience, usability, clarity | Comprehension-first advocate — if the user can't see it, the system failed | High assertiveness (opinionated) — comprehension first |
| The Security Mind | `security-voice` | Access control, trust, blast radius | Defense-in-depth enforcer — asks who sees the data when it fails | High assertiveness (opinionated) — defense posture |
| The Pragmatist | `pragmatist-voice` | Synthesis, consolidation | Neutral synthesizer — consolidates domain expert opinions, never advocates | Low assertiveness (neutral) — pure synthesis, no advocacy |

### Behavioral Calibration Guidance

Behavioral calibration governs how forcefully each voice positions its perspective. It is **not** a literal LLM temperature parameter — it is a behavioral instruction for assertiveness/tone:

| Voice | Behavioral Temperature | Rationale |
|-------|----------------------|-----------|
| `critic-voice` | High (aggressive) | Must find real flaws — genuine adversarial reasoning |
| `architect-voice` | High (opinionated) | Strong structural positions, not hedged summaries |
| `data-voice` | High (opinionated) | Schema-as-contract stance — no equivocation |
| `enduser-voice` | High (opinionated) | UX comprehension-first — no compromise on clarity |
| `security-voice` | High (opinionated) | Defense-in-depth — no shortcuts on security |
| `pragmatist-voice` | Low (neutral) | Pure synthesis, zero advocacy |
| Mediator | Medium (facilitative) | Presents positions, does not advocate |

## Voice Selection Logic

The Mediator activates voices based on problem signals. Not all voices are activated for every session.

| Problem Signal | Voices Activated |
|----------------|-----------------|
| Data processing / ETL / analytics | `data-voice`, `architect-voice` |
| User-facing tool / interface | `enduser-voice`, `architect-voice` |
| Automation / scripting | `architect-voice`, `data-voice` (if data involved) |
| Sensitive data / multi-user | `security-voice` + relevant domain voices |
| High investment tier (Shared/Production) | `security-voice` added to any combination |
| Novel / uncharted territory | All available domain voices |

**Default selection:** When in doubt, invoke all four domain voices (architect-voice, data-voice, enduser-voice, security-voice). Always follow with pragmatist-voice for synthesis after domain voices complete their cycles.

## Invocation Patterns

### Parallel Batch (Standard)

The Mediator invokes all relevant domain voices in **parallel** between Moments 3 and 4. Each voice runs its own independent Critic loop and publishes its hardened position before the Pragmatist synthesizes.

```
Mediator → [parallel batch]
  architect-voice → voices/architect.md
  data-voice      → voices/data-person.md
  enduser-voice   → voices/enduser.md
  security-voice  → voices/security.md
↓
Mediator → pragmatist-voice → synthesis.md
```

**When to use:** Standard voice deliberation phase (M3 → M4). Use when context is well-defined and voices can work independently.

**Context economy:** Each voice reads `context.md` + optionally `research-notes.md`. Voices do NOT share intermediate reasoning — they operate on the same blackboard (shared files) but in isolated context windows.

### Sequential Deep-Dive

For complex or highly interdependent problems, voices may be invoked **sequentially** so later voices can read earlier voices' results. The Mediator invokes one voice at a time; each reads previously published positions.

```
Mediator → architect-voice  (reads context.md)               → voices/architect.md
Mediator → data-voice       (reads architect.md)             → voices/data-person.md
Mediator → security-voice   (reads architect.md, data.md)    → voices/security.md
↓
Mediator → pragmatist-voice → synthesis.md
```

**When to use:** When voices have strong interdependencies (Security needs to evaluate the Architect's proposed approach). Slower but produces richer disagreement analysis — a **deep dive** into interdependent dimensions.

### Standalone Critic Invocations

The Critic is also invoked standalone by the Mediator (not via voice loops) at four moment boundaries to catch meta-level issues:

| Invocation Point | Challenge Prompt |
|-----------------|-----------------|
| After M1 | "Here's the stated problem. Is this the real problem?" |
| After M2 | "Here are the proposed outcomes. What's wrong with them?" |
| After M4 | "Here's the chosen approach. What will fail?" |
| After M5 | "Here's the Brief. What are we sweeping under the rug?" |

## Critic Loop Protocol

### When to Challenge

The Critic (`critic-voice`) is invoked **inside each domain voice's reasoning cycle** as a subagent of the voice — not as a separate panel member. The trigger is every voice response cycle: the voice forms a position, then immediately subjects it to Critic challenge before publishing.

The invocation prompt template: `"My position is [X]. Context in context.md. Challenge me."`

### The Voice Reasoning Cycle

```
Domain Voice invoked by Mediator:
  1. Read context.md + decisions.md
  2. Form initial opinion

  CRITIC LOOP (≤5 cycles):
    3. Invoke critic-voice: "My position is [X]. Challenge me."
    4. critic-voice returns adversarial challenges
    5. Voice evaluates: accept challenge → refine position, OR reject → stand firm
    6. If refined: loop back to step 3 with updated position
    7. If Critic says "position is solid" or 5 cycles reached: exit loop

  8. Write voices/{name}.md (final, hardened position)
  9. Write voices/{name}-debate.md (full Critic dialogue log)
```

### Qualitative Exit Condition

The Critic loop exits when either:

1. **The Critic says "position is solid"** — after honest examination the Critic genuinely cannot find material flaws. This is the canonical exit phrase (spec §12). The Critic's prompt must always include: *"If after honest examination you genuinely cannot find material flaws, say the position is solid and exit. Do not manufacture objections."*
2. **5 cycles reached** — hard cap regardless of whether the position is fully hardened.

**Architecture Review notes:** "convergence threshold" in the AC refers to this qualitative exit condition — not a numeric threshold.

### Max Rounds

**Maximum: 5 cycles per domain voice** (spec §12). Each cycle = one Critic challenge + one voice response. The qualitative exit ("position is solid") can terminate the loop before 5 cycles.

### Critic Rules

| Rule | Requirement |
|------|-------------|
| Do not manufacture objections | Critic must exit cleanly if it cannot find genuine material flaws |
| Evidence-backed challenges only | Every challenge must cite specific claims from the voice's position |
| No alternatives, no proposals | Critic challenges only — never proposes fixes or suggests a different stance |
| Different model always | `critic-voice` uses GPT-5.4 (copilot); all domain voices use Claude Opus 4.6 (copilot) |
| Adversarial, not performative | Separate model invocation ensures genuine cognitive diversity |

**Why a different model for the Critic:** A model that just proposed "Option A is best" cannot genuinely dismantle Option A in the same context. Separate invocation with a focused adversarial prompt produces real challenges. GPT-5.4 sees the problem from a fundamentally different angle than Claude Opus 4.6.

## Disagreement Resolution

### How Disagreements Are Surfaced

When domain voices disagree, pragmatist-voice does **not** resolve the disagreement algorithmically. Instead:

1. Pragmatist identifies diverging positions in `voices/*.md`
2. Flags each disagreement with attribution in `synthesis.md`
3. Mediator reads `synthesis.md` and **surfaces** the disagreement to the user with full attribution

Example (attributed disagreement surfacing):

```
Panel converged on X. [Architect] and [Data Person] disagree on Y.
[Architect] says A because...
[Data Person] warns B because...
Your call on Y.
```

### Resolution Protocol

**Resolution is the user's decision.** The Mediator presents the disagreement with attribution, then waits for the user to choose. The Mediator does not cast a tiebreaker vote or algorithmically prefer one voice over another.

**If the user's decision contradicts a voice's premise:** The Mediator is transparent — "Your decision changes the foundation [Architect] built on. I recommend re-running the panel with this new context. Want me to? Or proceed as-is?" The user decides whether to loop back.

**On loop-back:** Voices are stateless — they re-read updated `context.md` + `decisions.md` and form fresh positions (no anchoring to prior stance).

## Synthesis Rules

### Mediator Role in Synthesis

The Mediator does **not** directly synthesize voice outputs. It delegates synthesis entirely to pragmatist-voice and reads only `synthesis.md`. The Mediator's context window never contains raw voice debates or Critic challenges.

### Pragmatist Synthesis Process

pragmatist-voice produces the synthesis summary:

1. Reads all `voices/*.md` (final hardened positions — post-Critic-loop)
2. Reads `context.md` + `decisions.md`
3. Identifies convergences across voices
4. Identifies and flags disagreements (without resolving them)
5. Writes `synthesis.md` with attributed positions

**Key rule:** pragmatist-voice never advocates for a position. It synthesizes and consolidates; it does not evaluate which voice is correct.

### Convergence and Merge Mechanics

| Synthesis Mode | Description |
|---------------|-------------|
| **Full convergence** | All activated voices agree → Pragmatist writes a unified recommendation |
| **Partial convergence** | Most voices agree, one dissents → Pragmatist notes the dissent with attribution |
| **Disagreement** | Voices diverge on a key decision → Pragmatist surfaces both positions with attribution, flags for user resolution |
| **Domain isolation** | Voices address different dimensions → Pragmatist consolidates into separate sections without merge |

### Synthesis Output Format (`synthesis.md`)

```markdown
## Summary
[1–3 sentence Pragmatist frame — no advocacy]

## Convergences
- [Item]: [Architect], [Data Person], and [End User] all agree that...

## Disagreements (User Decision Required)
- [Item]: [Architect] says A because... [Security Mind] warns B because...

## Recommendations
[Only include if all voices converge; omit if any disagreement remains]
```

## Voice Agent References

All six voice panel agents are in `share/agents/`. They are subagents (`user-invocable: false`) and must be listed in the invoking agent's `agents:` frontmatter array.

| Canonical Name | File | Role |
|---------------|------|------|
| `critic-voice` | `share/agents/critic-voice.agent.md` | Adversarial challenger |
| `architect-voice` | `share/agents/architect-voice.agent.md` | System design voice |
| `data-voice` | `share/agents/data-voice.agent.md` | Data quality voice |
| `enduser-voice` | `share/agents/enduser-voice.agent.md` | End user experience voice |
| `security-voice` | `share/agents/security-voice.agent.md` | Security mind voice |
| `pragmatist-voice` | `share/agents/pragmatist-voice.agent.md` | Synthesis voice |

**Invocation prerequisites:**

1. The invoking agent must list the desired voices in its `agents:` frontmatter array.
2. Without an `agents:` listing, `disable-model-invocation: true` blocks the `runSubagent` call.
3. `pragmatist-voice` must be invoked **after** all domain voices have published their results to `voices/*.md`.

**Cross-reference:** The `w-ideation` skill documents the full 6-moment process and the precise points within the deliberation flow at which each voice is invoked.
