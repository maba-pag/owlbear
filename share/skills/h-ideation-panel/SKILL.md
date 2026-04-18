---
name: h-ideation-panel
description: "Handbook: Ideation panel — panelist characterizations, invocation patterns, Critic-loop protocol, and synthesis rules"
user-invocable: false
---

# Ideation Panel Handbook

Reference for the ideator agent’s ideation panel architecture. Consolidates panelist characterizations, invocation patterns, Critic-loop protocol, disagreement resolution, and Mediator synthesis rules from the thinking-companion-framework spec (§7, §12) and all six panelist agent files.

## Panelist Roster

All six panelists are separate subagents invoked by the Mediator (ideator agent). The Investigator is an internal Mediator behavioral mode and is not listed here.

| Panelist | Agent Name | Domain | Persona | Behavioral Calibration |
|-------|-----------|--------|---------|----------------------|
| The Critic | `ideation-critic` | Adversarial challenge | Relentless adversary — exposes weaknesses, never proposes solutions | High assertiveness (aggressive) — pulls no punches |
| The Architect | `ideation-architect` | System design, structure, patterns | Opinionated technician — spots coupling and enforces clean separations | High assertiveness (opinionated) — strong structural positions |
| The Modeler | `ideation-data` | Data quality, schemas, ETL, validation | Schema-first thinker — treats schema as contract, hunts NaN propagation | High assertiveness (opinionated) — schema-as-contract stance |
| The End User | `ideation-enduser` | Human experience, usability, clarity | Comprehension-first practitioner — if the user can't see it, the system failed | High assertiveness (opinionated) — comprehension first |
| The Skeptic | `ideation-security` | Access control, trust, blast radius | Defense-in-depth enforcer — asks who sees the data when it fails | High assertiveness (opinionated) — defense posture |
| The Pragmatist | `ideation-pragmatist` | Synthesis, consolidation | Neutral synthesizer — consolidates panelist stances, never advocates | Low assertiveness (neutral) — pure synthesis, no advocacy |

### Behavioral Calibration Guidance

Behavioral calibration governs how forcefully each panelist positions its perspective. It is **not** a literal LLM temperature parameter — it is a behavioral instruction for assertiveness/tone:

| Panelist | Behavioral Temperature | Rationale |
|-------|----------------------|-----------|
| `ideation-critic` | High (aggressive) | Must find real flaws — genuine adversarial reasoning |
| `ideation-architect` | High (opinionated) | Strong structural positions, not hedged summaries |
| `ideation-data` | High (opinionated) | Schema-as-contract stance — no equivocation |
| `ideation-enduser` | High (opinionated) | UX comprehension-first — no compromise on clarity |
| `ideation-security` | High (opinionated) | Defense-in-depth — no shortcuts on security |
| `ideation-pragmatist` | Low (neutral) | Pure synthesis, zero advocacy |
| Mediator | Medium (facilitative) | Presents positions, does not advocate |

## Panelist Selection Logic

The Mediator activates panelists based on problem signals. Not all panelists are activated for every session.

| Problem Signal | Panelists Activated |
|----------------|------------------|
| Data processing / ETL / analytics | `ideation-data`, `ideation-architect` |
| User-facing tool / interface | `ideation-enduser`, `ideation-architect` |
| Automation / scripting | `ideation-architect`, `ideation-data` (if data involved) |
| Sensitive data / multi-user | `ideation-security` + relevant domain panelists |
| High investment tier (Shared/Production) | `ideation-security` added to any combination |
| Novel / uncharted territory | All available domain panelists |

**Default selection:** When in doubt, invoke all four domain panelists (ideation-architect, ideation-data, ideation-enduser, ideation-security). Always follow with ideation-pragmatist for synthesis after domain panelists complete their cycles.

## Invocation Patterns

### Parallel Batch (Standard)

The Mediator invokes all relevant domain panelists in **parallel** between Moments 3 and 4. Each panelist runs its own independent Critic loop and publishes its hardened stance before the Pragmatist synthesizes.

```
Mediator → [parallel batch]
  ideation-architect → stances/architect.md
  ideation-data      → stances/data.md
  ideation-enduser   → stances/enduser.md
  ideation-security  → stances/security.md
↓
Mediator → ideation-pragmatist → synthesis.md
```

**When to use:** Standard panelist deliberation phase (M3 → M4). Use when context is well-defined and panelists can work independently.

**Context economy:** Each panelist reads `context.md` + optionally `research-notes.md`. Panelists do NOT share intermediate reasoning — they operate on the same blackboard (shared files) but in isolated context windows.

### Sequential Deep-Dive

For complex or highly interdependent problems, panelists may be invoked **sequentially** so later panelists can read earlier stances. The Mediator invokes one panelist at a time; each reads previously published positions.

```
Mediator → ideation-architect  (reads context.md)               → stances/architect.md
Mediator → ideation-data       (reads architect.md)             → stances/data.md
Mediator → ideation-security   (reads architect.md, data.md)    → stances/security.md
↓
Mediator → ideation-pragmatist → synthesis.md
```

**When to use:** When panelists have strong interdependencies (Security needs to evaluate the Architect's proposed approach). Slower but produces richer disagreement analysis — a **deep dive** into interdependent dimensions.

### Standalone Critic Invocations

The Critic is also invoked standalone by the Mediator (not via panelist loops) at four moment boundaries to catch meta-level issues:

| Invocation Point | Challenge Prompt |
|-----------------|-----------------|
| After M1 | "Here's the stated problem. Is this the real problem?" |
| After M2 | "Here are the proposed outcomes. What's wrong with them?" |
| After M4 | "Here's the chosen approach. What will fail?" |
| After M5 | "Here's the Brief. What are we sweeping under the rug?" |

## Critic Loop Protocol

### When to Challenge

The Critic (`ideation-critic`) is invoked **inside each domain panelist's reasoning cycle** as a subagent of the panelist — not as a separate panel member. The trigger is every panelist response cycle: the panelist forms a position, then immediately subjects it to Critic challenge before publishing.

The invocation prompt template: `"My position is [X]. Context in context.md. Challenge me."`

### The Stance Reasoning Cycle

```
Panelist invoked by Mediator:
  1. Read context.md + decisions.md
  2. Form initial stance

  CRITIC LOOP (≤5 cycles):
    3. Invoke ideation-critic: "My position is [X]. Challenge me."
    4. ideation-critic returns adversarial challenges
    5. Panelist evaluates: accept challenge → refine position, OR reject → stand firm
    6. If refined: loop back to step 3 with updated position
    7. If Critic says "position is solid" or 5 cycles reached: exit loop

  8. Write stances/{name}.md (final, hardened stance)
  9. Write stances/{name}-debate.md (full Critic dialogue log)
```

### Qualitative Exit Condition

The Critic loop exits when either:

1. **The Critic says "position is solid"** — after honest examination the Critic genuinely cannot find material flaws. This is the canonical exit phrase (spec §12). The Critic's prompt must always include: *"If after honest examination you genuinely cannot find material flaws, say the position is solid and exit. Do not manufacture objections."*
2. **5 cycles reached** — hard cap regardless of whether the position is fully hardened.

**Architecture Review notes:** "convergence threshold" in the AC refers to this qualitative exit condition — not a numeric threshold.

### Max Rounds

**Maximum: 5 cycles per domain panelist** (spec §12). Each cycle = one Critic challenge + one panelist response. The qualitative exit ("position is solid") can terminate the loop before 5 cycles.

### Critic Rules

| Rule | Requirement |
|------|-------------|
| Do not manufacture objections | Critic must exit cleanly if it cannot find genuine material flaws |
| Evidence-backed challenges only | Every challenge must cite specific claims from the panelist's position |
| No alternatives, no proposals | Critic challenges only — never proposes fixes or suggests a different stance |
| Different model always | `ideation-critic` uses GPT-5.4 (copilot); all domain panelists use Claude Opus 4.7 (copilot) |
| Adversarial, not performative | Separate model invocation ensures genuine cognitive diversity |

**Why a different model for the Critic:** A model that just proposed "Option A is best" cannot genuinely dismantle Option A in the same context. Separate invocation with a focused adversarial prompt produces real challenges. GPT-5.4 sees the problem from a fundamentally different angle than Claude Opus 4.6.

## Disagreement Resolution

### How Disagreements Are Surfaced

When domain panelists disagree, ideation-pragmatist does **not** resolve the disagreement algorithmically. Instead:

1. Pragmatist identifies diverging positions in `stances/*.md`
2. Flags each disagreement with attribution in `synthesis.md`
3. Mediator reads `synthesis.md` and **surfaces** the disagreement to the user with full attribution

Example (attributed disagreement surfacing):

```
Panel converged on X. [Architect] and [Modeler] disagree on Y.
[Architect] says A because...
[Modeler] warns B because...
Your call on Y.
```

### Resolution Protocol

**Resolution is the user’s decision.** The Mediator presents the disagreement with attribution, then waits for the user to choose. The Mediator does not cast a tiebreaker vote or algorithmically prefer one panelist over another.

**If the user’s decision contradicts a panelist’s premise:** The Mediator is transparent — "Your decision changes the foundation [Architect] built on. I recommend re-running the panel with this new context. Want me to? Or proceed as-is?" The user decides whether to loop back.

**On loop-back:** Panelists are stateless — they re-read updated `context.md` + `decisions.md` and form fresh positions (no anchoring to prior stance).

## Synthesis Rules

### Mediator Role in Synthesis

The Mediator does **not** directly synthesize panelist outputs. It delegates synthesis entirely to ideation-pragmatist and reads only `synthesis.md`. The Mediator’s context window never contains raw panelist debates or Critic challenges.

### Pragmatist Synthesis Process

ideation-pragmatist produces the synthesis summary:

1. Reads all `stances/*.md` (final hardened stances — post-Critic-loop)
2. Reads `context.md` + `decisions.md`
3. Identifies convergences across panelists
4. Identifies and flags disagreements (without resolving them)
5. Writes `synthesis.md` with attributed positions

**Key rule:** ideation-pragmatist never advocates for a position. It synthesizes and consolidates; it does not evaluate which panelist is correct.

### Convergence and Merge Mechanics

| Synthesis Mode | Description |
|---------------|-------------|
| **Full convergence** | All activated panelists agree → Pragmatist writes a unified recommendation |
| **Partial convergence** | Most panelists agree, one dissents → Pragmatist notes the dissent with attribution |
| **Disagreement** | Panelists diverge on a key decision → Pragmatist surfaces both positions with attribution, flags for user resolution |
| **Domain isolation** | Panelists address different dimensions → Pragmatist consolidates into separate sections without merge |

### Synthesis Output Format (`synthesis.md`)

```markdown
## Summary
[1–3 sentence Pragmatist frame — no advocacy]

## Convergences
- [Item]: [Architect], [Modeler], and [End User] all agree that...

## Disagreements (User Decision Required)
- [Item]: [Architect] says A because... [Skeptic] warns B because...

## Recommendations
[Only include if all panelists converge; omit if any disagreement remains]
```

## Panelist References

All six ideation panel agents are in `share/agents/`. They are subagents (`user-invocable: false`) and must be listed in the invoking agent's `agents:` frontmatter array.

| Canonical Name | File | Role |
|---------------|------|------|
| `ideation-critic` | `share/agents/ideation-critic.agent.md` | Adversarial challenger |
| `ideation-architect` | `share/agents/ideation-architect.agent.md` | System design panelist |
| `ideation-data` | `share/agents/ideation-data.agent.md` | Data quality panelist |
| `ideation-enduser` | `share/agents/ideation-enduser.agent.md` | End user experience panelist |
| `ideation-security` | `share/agents/ideation-security.agent.md` | Security panelist |
| `ideation-pragmatist` | `share/agents/ideation-pragmatist.agent.md` | Synthesis panelist |

**Invocation prerequisites:**

1. The invoking agent must list the desired panelists in its `agents:` frontmatter array.
2. Without an `agents:` listing, `disable-model-invocation: true` blocks the `runSubagent` call.
3. `ideation-pragmatist` must be invoked **after** all domain panelists have published their stances to `stances/*.md`.

**Cross-reference:** The `w-ideation` skill documents the full 6-moment process and the precise points within the deliberation flow at which each panelist is invoked.
