---
name: research-workflow
description: "Structured research workflow: clarify scope → gather sources → analyze with trade-off matrices → write doc → create follow-up tasks. Used by the researcher agent."
---

# Research Workflow

Step-by-step process for investigating a topic and producing structured, actionable findings.

## Research checklist

Before a task can leave `ideation`, complete this checklist. Items 1–5 are **mandatory**;
items 6–7 are **recommended**.

1. **Theoretical validity** — Is this a sound concept? Does the abstraction make sense? Is it the right approach?
2. **Prior art** — Find 2+ GitHub repos, articles, or docs showing how others solved this problem.
3. **Technical feasibility** — Will it work in our stack (Python 3.12, PydanticAI, etc.)? Any blockers or dependencies?
4. **Architecture fit** — How does it integrate with existing OwlBear components? What interfaces does it touch?
5. **Implementation approach** — What patterns, idioms, and data structures should we adopt from prior art?
6. **Testing strategy** _(recommended)_ — How will we test this? Unit, integration, mocks? Coverage approach?
7. **Findings documented** _(recommended)_ — Brief notes in task body, or linked `docs/research/{slug}.md` for complex research.

For trivial tasks (rename, typo, config tweak): items 1–3 get a one-liner
`N/A — trivial change, rationale: X` and the task moves through quickly. **The gate
still exists** — it just doesn't create busywork.

## Step 0 — Claim

Immediately claim the task by ID (never use `pick` — see **kanban-md skill** → Agent Task Lifecycle Protocol):

```powershell
kanban\kanban-md.exe show {id}
kanban\kanban-md.exe edit {id} --claim <agent>
```

## Step 1 — Clarify scope

Understand exactly what's being asked:

- If ambiguous: use `askQuestions` (what aspects? what decision? what constraints?)
- Read `copilot-instructions.md` for tech stack and principles

## Step 2 — Gather sources

Find 2+ authoritative sources per claim:

- **Codebase:** search tools for related existing code
- **Web:** `fetch_webpage` for docs, articles, GitHub repos
- **Clone for deep analysis:** `docs/scratch/research/{repo-name}/` → analyze → delete when done

Track: name, URL, what was taken, relevance score (0.0–1.0).

## Step 3 — Analyze and compare

Structure analysis as trade-off matrices, not prose:

- Comparison tables (rows = options, columns = criteria)
- Confidence scores on recommendations (.0–1.0)
- Risks and mitigations for each option
- Apply KISS, YAGNI, DRY principles

## Step 4 — Write research document

Create `docs/research/{slug}.md`:

```markdown
# {Title}

> **Owning task:** #{id} — {title}
> **Date:** {date} **Status:** Complete

## 1. Context and Question

## 2. Sources Studied (table)

## 3. Analysis (trade-off matrices)

## 4. Recommendation (with confidence)

## 5. Follow-up Tasks (kanban commands)
```

Max 200 lines. Every claim needs a source reference.

## Step 5 — Create follow-up tasks

Generate `kanban-md create` commands for every actionable finding.
**Execute them** to create tasks at `ideation` status — the architect still gates them before `todo`.

If a finding requires a user decision with no clear winner, create a **decision request**
in `docs/decisions/pending/` instead. See `decision-requests.instructions.md` for the format.
Block the current task and move on to other work if available.

## Step 6 — Update attribution

Add rows to `docs/sources/overview.md` for any external sources used.

## Step 7 — Clean up

Delete any cloned repos from `docs/scratch/research/`.

## Step 8 — Advance + release

Advance the task to `backlog` and release the claim in one atomic command:

```powershell
kanban\kanban-md.exe edit {id} --status backlog --release
```

## Self-critique checklist

Before submitting:

- [ ] Every claim has ≥ 2 sources
- [ ] Analysis uses comparison tables
- [ ] Confidence scores on recommendations
- [ ] Research doc ≤ 200 lines
- [ ] Follow-up kanban tasks are concrete and actionable
- [ ] Did NOT create/edit source code
- [ ] External sources logged in sources/overview.md
- [ ] Cloned repos deleted
- [ ] Task advanced to `backlog` and claim released via `edit {id} --status backlog --release`
- [ ] Recommendations align with KISS/YAGNI
