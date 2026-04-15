# Briefs

This directory is the **Blackboard** for the Ideator agent system. Opinionated agents communicate through shared filesystem artifacts here — each agent reads and writes only the files it owns.

## Directory Structure

Each ideation session lives in a named Working Directory:

```
.owlbear/briefs/draft-{project-name}/
  input/                    ← User's reference materials (Excel, docs, screenshots, links)
                               Drop files here before or at the start of the conversation.
  context.md                ← Problem, Outcomes, Tier, Landscape summary
                               Populated incrementally by the Mediator:
                                 M1 → problem + tier
                                 M2 → outcomes
                                 M3 → landscape summary
  research-notes.md         ← Detailed codebase / ecosystem findings
                               Written by the research subagent during M3.
  decisions.md              ← User decisions as they are made
                               Created empty at invocation; populated after each user choice.
  opinions/
    {name}.md               ← Domain opinion final position (after Critic cycles)
    {name}-debate.md        ← Domain opinion ↔ Critic debate log
  synthesis.md              ← Pragmatist synthesis of all opinion results
  brief.md                  ← Final Brief (written at user approval)
```

**Standard opinionated agent names:** `architect`, `data-person`, `enduser`, `security`

### `input/` subfolder convention

Place any reference materials the Ideator should consider here before starting:

- Spreadsheets, screenshots, design documents, existing specs
- Web links (as `.txt` or `.md` files)
- Anything the user brings to the conversation

The Mediator reads `input/*` at start and summarises what it found. Files are never modified.

### `opinions/` subdirectory convention

Each domain opinion writes two files:

| File | Contents |
|------|----------|
| `opinions/{name}.md` | Final, hardened position — the conclusion after Critic cycles |
| `opinions/{name}-debate.md` | Full Critic dialogue log — adversarial rounds, refinements |

The Pragmatist reads only `opinions/{name}.md` (final positions), never the debate logs.

## Agent Read / Write Matrix

| Agent | Reads | Writes |
|-------|-------|--------|
| **Mediator** | `input/*`, `context.md`, `decisions.md`, `synthesis.md` | `context.md` (incremental), `decisions.md`, `brief.md` |
| **Research subagent** | `context.md`, `input/*`, codebase (tools), ecosystem (web fetch) | `research-notes.md` (returns summary to Mediator) |
| **Domain Opinion** | `context.md`, `decisions.md`, optionally `research-notes.md` | `opinions/{name}.md`, `opinions/{name}-debate.md` |
| **Critic** (standalone, M1/M2/M4/M5) | `context.md` | Returns response to Mediator — no direct file write |
| **Critic** (op-agent-embedded) | Opinionated agent's current draft + `context.md` | Returns response to invoking opinionated agent — no direct file write |
| **Pragmatist** | `context.md`, `decisions.md`, ALL `opinions/*.md` | `synthesis.md` |
| **Final Critic** (optional) | `context.md`, `synthesis.md` | Appends challenges to `synthesis.md` |
| **Planner** | `brief.md` | Kanban tasks |

**Rule:** The Mediator never reads raw research, debate logs, or individual opinion arguments. Its context window stays clean throughout the conversation.

## Brief Lifecycle

1. **Invocation** — Mediator creates `.owlbear/briefs/draft-new/` with:
   - `input/` (empty, for user to populate)
   - `context.md` (empty scaffold — problem, outcomes, tier, landscape fields)
   - `decisions.md` (empty scaffold — a header and blank body)

2. **After M1 (project named)** — `draft-new/` renamed to `draft-{project-name}/`

3. **During ideation** — `context.md` populated incrementally; opinionated agents write to `opinions/`; Pragmatist writes `synthesis.md`

4. **At user approval** — Mediator writes `brief.md` from context + decisions + synthesis

5. **At handoff** — Brief content transferred into a parent kanban task; Planner decomposes into subtasks. Agents work from kanban tasks, not from the Brief file. The Brief file is preserved as **audit trail**.

6. **After handoff** — Working Directory preserved for audit. Cleaned up when the parent task is completed or archived.

### `context.md` scaffold (created empty at invocation)

```markdown
# Context

## Problem


## Outcomes


## Tier


## Landscape

```

### `decisions.md` scaffold (created empty at invocation)

```markdown
# Decisions

<!-- Populated by Mediator after each user choice -->
```

## For users

To start an ideation session, select **ideator** in the VS Code agent picker (or type `@ideator`).

**Argument hint:** `[idea, problem, or feature — drop reference files in .owlbear/briefs/draft-new/input/]`

If a `draft-new/` already exists from a previous unfinished session, the Mediator will ask whether to continue or start fresh.
