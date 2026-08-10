# Briefs

This directory is the ideation **Blackboard**. Discovery, mediation, challengers, panelists, and synthesis agents communicate through shared filesystem artifacts here.

## Directory Structure

Each ideation session lives in a named Working Directory:

```text
.owlbear/briefs/draft-{project-name}/
  input/                    ← User reference materials
  context.md                ← Narrow current-state snapshot
  decisions.md              ← Chosen and rejected options with rationale
  research-notes.md         ← First substantial research bridge
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
    *-debate.md             ← Present only for agents that ran an embedded Critic loop
  synthesis-idea-panel.md   ← Optional denoised digest of the early challenge lane
  synthesis.md              ← Late-domain panel synthesis (converge or compare path)
  brief.md                  ← Final approved Brief
```

## Artifact Roles

### `context.md`

- narrow snapshot only
- problem, outcomes, constraints, current tensions
- kept concise for subagent read use

### `decisions.md`

- append-only decision history
- chosen and rejected options with rationale
- phase boundary and handoff notes when relevant

### `research-notes.md`

Must separate:

- `Verified findings`
- `Candidate implications`
- `Open research questions`

### `stances/`

Contains both early-challenger and late-domain stance files. The invoker must name the active stance set for each synthesis call so unrelated old stances are not swept into the current pass.

Late-domain proposal files (`*-proposal.md`) are optional and appear only when the mediator runs the conditional M3.5 proposal round.

### `synthesis-idea-panel.md`

Optional. Written only when the early challenge lane needs denoise.

### `synthesis.md`

Written by the Pragmatist after the late-domain panel.

## Agent Read / Write Matrix

| Agent | Reads | Writes |
|-------|-------|--------|
| **Discovery agent** | `input/*`, `context.md`, `decisions.md`, optional `synthesis-idea-panel.md` | `context.md`, `decisions.md`, `research-notes.md` |
| **Research subagent** | `context.md`, `input/*`, codebase and ecosystem sources | `research-notes.md` |
| **Early challenger** | `context.md`, `decisions.md`, optional `research-notes.md` | `stances/{name}.md` |
| **Late domain panelist** | `context.md`, `decisions.md`, optional `research-notes.md` | `stances/{name}.md`, `stances/{name}-debate.md`, or `stances/{name}-proposal.md` |
| **Pragmatist** | `context.md`, `decisions.md`, active `stances/*.md` set or `stances/*-proposal.md` set | `synthesis-idea-panel.md` or `synthesis.md` |
| **Critic** | `context.md`, current position supplied by invoker | no file writes |
| **Mediation agent** | `context.md`, `decisions.md`, `research-notes.md`, optional `synthesis-idea-panel.md`, `synthesis.md` | `decisions.md`, `brief.md` |
| **Planner** | `brief.md` | kanban tasks |

## Brief Lifecycle

1. **Discovery start** — `ideation-discoverer` creates or resumes the Working Directory.
2. **Discovery phase** — problem and outcomes are locked; early challenge lane runs; first-pass research is curated.
3. **Phase handoff** — discovery ends by naming `@ideation-mediator` and the artifact paths: `context.md`, `decisions.md`, `research-notes.md`.
4. **Mediation phase** — late-domain panel runs; decisions are supported; `brief.md` is drafted and approved.
5. **Handoff** — mediation creates a parent kanban task and invokes planner.
6. **Audit trail** — Working Directory is preserved after handoff.

## `context.md` scaffold

```markdown
# Context

## Problem


## Outcomes


## Tier


## Constraints


## Current Tensions
```

## `decisions.md` scaffold

Decision Entry Template:

`## D{N} — {YYYY-MM-DD HH:MM} — {Topic}`

```markdown
# Decisions

## D1 — YYYY-MM-DD HH:MM — Topic

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

Repeat the same entry shape for each real decision. Preserve chosen and rejected options with rationale rather than collapsing everything into a final summary.

## For users

Start a new ideation session with `@ideation-discoverer`.

Continue a completed discovery session with `@ideation-mediator`.
