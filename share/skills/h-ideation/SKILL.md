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
| Phase 2 — Mediation | `ideation-mediator`   | M3-M6, late-domain panel, Critic validation, Brief, handoff | `synthesis.md`, `brief.md`, kanban parent task                                        |

## User-Facing Entry Points

### `@ideation-discoverer`

Use for:

- raw ideas
- fuzzy problems
- overscoped asks
- ambiguous project type
- missing ideation artifacts

### `@ideation-mediator`

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
    data.md
    enduser.md
    firstprinciples.md
    outsider.md
    security.md
    simplifier.md
    *-debate.md
  synthesis-idea-panel.md
  synthesis.md
  brief.md
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

## Shared Interaction Contract

### Investigative Turns

- Default for Phase 1 M1-M2.
- Freeform probing is the baseline. Do not force a structured decision scaffold when the user is still clarifying the problem.
- Do not use the structured context header or anchor-recall unless the user is making a real choice or the conversation has shifted into a synthesis relay.

### Synthesis Turns

- Use when relaying research, challenger output, or panel synthesis.
- Require the structured context header:
  - current phase and moment
  - current sub-topic
  - prior anchor
- Apply anchor-recall only when the anchor has changed in a meaningful way.

### Decision Turns

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

Phase 1 must end with an explicit message naming `@ideation-mediator` and those artifact paths. Phase 2 starts from those files in a fresh context.

## Cross-References

- `w-ideation-discovery` — Phase 1 operating procedure
- `w-ideation-mediation` — Phase 2 operating procedure
- `h-ideation-panel` — panelist-facing rules for early challengers, late domain panelists, Critic loops, and Pragmatist modes
