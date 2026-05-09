---
name: h-ideation-panel
description: "Handbook: Ideation panel lanes — early challengers, late domain panelists, Critic loops, and Pragmatist modes"
user-invocable: false
---

# Ideation Panel Handbook

Reference for panel-facing ideation agents only. The user-facing phase agents should load their workflow skills, not this handbook.

## Universal Constraints

- **No kanban commands.** Ideation agents do not interact with the kanban board or pipeline status transitions.

## Panel Surface Map

Ideation now has two panel surfaces.

| Surface                     | Phase                                             | Default Participants                                                           | Purpose                                                                          |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| Early challenge lane        | Phase 1 — Discovery                               | `ideation-simplifier`, `ideation-firstprinciples`                              | Pressure-test framing, scope, and hidden assumptions before approach choice      |
| Conditional early challenge | Phase 1 — Discovery                               | `ideation-outsider`                                                            | Break tunnel vision when the current framing is trapped inside local assumptions |
| Late domain panel           | Phase 2 — Mediation                               | `ideation-architect`, `ideation-data`, `ideation-enduser`, `ideation-security` | Evaluate viable approaches through domain lenses                                 |
| Shared synthesis role       | Phase 1 or 2                                      | `ideation-pragmatist`                                                          | Denoise early challenges, converge late-domain stances, or compare proposals     |
| Shared adversarial role     | Phase 2 by default, embedded in late domain loops | `ideation-critic`                                                              | Stress-test positions without proposing alternatives                             |

## Early Challenge Lane

### Roster

| Agent                      | Role                                            | Default?    | Output                       |
| -------------------------- | ----------------------------------------------- | ----------- | ---------------------------- |
| `ideation-simplifier`      | Scope reduction and decomposition pressure      | Yes         | `stances/simplifier.md`      |
| `ideation-firstprinciples` | Strips the framing to irreducible claims        | Yes         | `stances/firstprinciples.md` |
| `ideation-outsider`        | Reframes through analogous domains or audiences | Conditional | `stances/outsider.md`        |

### Selection Logic

- Always invoke `ideation-simplifier` and `ideation-firstprinciples` at the end of M2.
- Invoke `ideation-outsider` only when the discovery agent sees tunnel vision, domain capture, or unclear user value.
- Do not use `ideation-critic` as the default early challenger.

### Invocation Pattern

```text
Discoverer
  ├─ ideation-simplifier      -> stances/simplifier.md
  ├─ ideation-firstprinciples -> stances/firstprinciples.md
  ├─ ideation-outsider        -> stances/outsider.md        (conditional)
  └─ ideation-pragmatist      -> synthesis-idea-panel.md    (optional, mode=denoise)
```

### Early-Challenge Rules

- Outputs must be short and bounded.
- The point is signal, not volume.
- Early challengers do **not** run the late-domain Critic loop by default.
- If a later revision deliberately adds an embedded Critic loop to an early challenger, its debate log belongs in `stances/{name}-debate.md`.
- Discovery may read challenger outputs directly when they are already compact. Denoise is conditional, not mandatory.

## Late Domain Panel

### Roster

| Agent                | Domain                                         | Output                 |
| -------------------- | ---------------------------------------------- | ---------------------- |
| `ideation-architect` | System design, structure, boundaries           | `stances/architect.md` |
| `ideation-data`      | Data quality, validation, schema               | `stances/data.md`      |
| `ideation-enduser`   | Human experience, usability, clarity           | `stances/enduser.md`   |
| `ideation-security`  | Trust boundaries, blast radius, access control | `stances/security.md`  |

### Selection Logic

| Problem Signal                    | Panelists Activated                                   |
| --------------------------------- | ----------------------------------------------------- |
| Data processing / ETL / analytics | `ideation-data`, `ideation-architect`                 |
| User-facing tool / interface      | `ideation-enduser`, `ideation-architect`              |
| Automation / scripting            | `ideation-architect`, `ideation-data` when data-heavy |
| Sensitive data / multi-user       | `ideation-security` plus relevant domain panelists    |
| Novel / uncharted territory       | all relevant domain panelists                         |

### Parallel Batch (Default)

```text
Mediator -> [parallel batch]
  ideation-architect -> stances/architect.md
  ideation-data      -> stances/data.md
  ideation-enduser   -> stances/enduser.md
  ideation-security  -> stances/security.md
Mediator -> ideation-pragmatist (mode=converge) -> synthesis.md
```

### Sequential Deep-Dive (Conditional)

Use sequential invocation only when later panelists need earlier stance outputs to evaluate the real trade-off.

### Propose Mode (M3.5 Path)

Use this mode only when the mediator's M3.5 gate detects real ambiguity (at least two viable approaches, no dominant option).

- The mediator dispatches all four late domain panelists in parallel, overriding the selection matrix for maximum design diversity.
- Each panelist receives M3 landscape synthesis plus an explicit PROPOSE-mode directive in the prompt payload.
- Panelists produce complete designs shaped by domain emphasis, not domain-only slices.
- Panelists write `stances/{name}-proposal.md` with these sections:
  - `Design Summary`
  - `Key Structural Choices`
  - `Trade-offs`
  - `Domain Rationale`
  - `Confidence`
- In propose mode, panelists skip the embedded Critic loop. Adversarial validation occurs later through post-hybridization Critic passes in mediation.

```text
Mediator -> [parallel batch, propose mode]
  ideation-architect -> stances/architect-proposal.md
  ideation-data      -> stances/data-proposal.md
  ideation-enduser   -> stances/enduser-proposal.md
  ideation-security  -> stances/security-proposal.md
Mediator -> ideation-pragmatist (mode=compare) -> synthesis.md
```

## Critic Loop Protocol

The late-domain panelists use the embedded Critic loop by default for stance mode.

### Stance Reasoning Cycle

```text
Panelist invoked by Mediator:
  1. Read context.md + decisions.md (+ research-notes.md if needed)
  2. Form initial stance

  CRITIC LOOP (<= 5 cycles):
    3. Invoke ideation-critic
    4. Receive adversarial challenges
    5. Refine or stand firm
    6. Exit early if the position is solid

  7. Write stances/{name}.md
  8. Write stances/{name}-debate.md
```

Propose mode is the exception: panelists write `stances/{name}-proposal.md` directly and skip the embedded Critic loop.

### Exit Conditions

- exit when the Critic says the position is solid
- or exit at 5 cycles, whichever comes first

### Critic Rules

- evidence-backed challenges only
- no manufactured objections
- no alternatives or fixes
- cognitive diversity is the goal; hardcoded vendor/model strings are not the contract

## Pragmatist Modes

### `mode=denoise`

Use only for the Phase 1 early challenge lane when multiple challenger outputs create real redundancy or volume.

- reads the active early-challenger stance set named by the invoker
- writes `synthesis-idea-panel.md`
- strips filler and repeated framing
- preserves distinct claims, divergences, and reasoning chains
- does **not** rank, converge, or recommend

### `mode=converge`

Use after the Phase 2 late domain panel completes.

- reads the active late-domain stance set named by the invoker
- writes `synthesis.md`
- identifies convergences and disagreements with attribution
- may recommend only where convergence justifies it

### `mode=compare`

Use after M3.5 proposal collection in Phase 2.

- reads `context.md` and `decisions.md`
- reads `stances/*-proposal.md`
- writes `synthesis.md`
- outputs a divergence-only comparison matrix with columns:
  - Decision Point
  - architect
  - data
  - enduser
  - security
  - Tension Level
- includes common ground summary
- includes open questions

## Disagreement Resolution

- Pragmatist flags disagreements; it does not resolve them.
- The mediation agent surfaces disagreements with attribution.
- The user decides.
- If the user's decision invalidates a core panel premise, the mediation agent should recommend a rerun with updated context.

## Panel Output Phrasing

- Use descriptive section headers that state the issue plainly (for example: Structural Concern: tight coupling between X and Y).
- Avoid protocol-coded or jargon-first headers (for example: O15-FAIL: coupling violation).
- Prefer natural language headers rather than internal shorthand so meaning is clear on first read.
- Stance files may be quoted by the mediator in downstream synthesis.
- Write headers so they are readable to the user without translation.
- This guidance affects phrasing only; panel mechanics and stance file structure stay unchanged.

## Panelist References

| Canonical Name             | File                                             | Role                            |
| -------------------------- | ------------------------------------------------ | ------------------------------- |
| `ideation-firstprinciples` | `share/agents/ideation-firstprinciples.agent.md` | Early assumption challenger     |
| `ideation-simplifier`      | `share/agents/ideation-simplifier.agent.md`      | Early scope challenger          |
| `ideation-outsider`        | `share/agents/ideation-outsider.agent.md`        | Early outsider lens             |
| `ideation-critic`          | `share/agents/ideation-critic.agent.md`          | Adversarial challenger          |
| `ideation-architect`       | `share/agents/ideation-architect.agent.md`       | Structural panelist             |
| `ideation-data`            | `share/agents/ideation-data.agent.md`            | Data panelist                   |
| `ideation-enduser`         | `share/agents/ideation-enduser.agent.md`         | UX panelist                     |
| `ideation-security`        | `share/agents/ideation-security.agent.md`        | Security panelist               |
| `ideation-pragmatist`      | `share/agents/ideation-pragmatist.agent.md`      | Denoise/convergence synthesizer |

The invoking agent must name the active panelists explicitly in its `agents:` frontmatter before attempting to call them.
