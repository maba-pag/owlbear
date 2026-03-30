---
name: research-workflow
description: "Structured research workflow: clarify scope → gather sources → analyze with trade-off matrices → write doc → create follow-up tasks. Used by the researcher agent."
user-invocable: false
---

# Research Workflow

Step-by-step process for investigating a topic and producing structured, actionable findings.

## kanban-md Commands

See kanban-md skill for claiming protocol and pitfalls. Key researcher commands:

| Action | Command |
|--------|--------|
| Create follow-up | `kanban\kanban-md.exe create "TITLE" --priority P --status ideation --tags T` |

## Research checklist

Before a task can leave `ideation`, complete this checklist. Items 1–6 are **mandatory**;
items 7–8 are **recommended**.

1. **Theoretical validity** — Is this a sound concept? Does the abstraction make sense? Is it the right approach?
2. **Environment audit** — Is this capability already provided by the IDE, runtime, installed extensions, or existing tooling? Check VS Code built-in features, extension-provided servers, and installed packages before recommending additions.
3. **Prior art** — Find 2+ GitHub repos, articles, or docs showing how others solved this problem.
4. **Technical feasibility** — Will it work in our stack (Python 3.12, PydanticAI, etc.)? Any blockers or dependencies?
5. **Architecture fit** — How does it integrate with existing OwlBear components? What interfaces does it touch?
6. **Implementation approach** — What patterns, idioms, and data structures should we adopt from prior art?
7. **Testing strategy** _(recommended)_ — How will we test this? Unit, integration, mocks? Coverage approach?
8. **Findings documented** _(recommended)_ — Brief notes in task body, or linked `docs/research/{slug}.md` for complex research.

For trivial tasks (rename, typo, config tweak): items 1–4 get a one-liner
`N/A — trivial change, rationale: X` and the task moves through quickly. **The gate
still exists** — it just doesn't create busywork.

## Step 0 — Claim

Claim by ID per kanban-md skill → Claiming Protocol.

## Step 1 — Clarify scope

**Fail fast on invalid inputs before starting any research:**

- If the task is a placeholder (`TEMP-*` title or empty/unscoped body), refuse dispatch immediately. See agent-common → **Placeholder and unscoped task rejection**. Example: a task titled `TEMP-planner-test` with no scoped body must be blocked or handed off — it must not be clarified by question or have scope invented for it. See `docs/research/planner-temp-task-hygiene.md`.

If the task has scoped content but needs clarification:

- Present structured options to the user (what aspects? what decision? what constraints?)
- Read `.github/copilot-instructions.md` for tech stack and principles

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
in `docs/decisions/pending/` instead. See the `decision-requests` skill (`skills/decision-requests/SKILL.md`) for the format.
Block the current task and move on to other work if available.

## Step 6 — Finalize

1. Add rows to `docs/sources/overview.md` for any external sources used
2. Delete any cloned repos from `docs/scratch/research/`
3. Advance and release:

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
- [ ] Task advanced to `backlog` and claim released
- [ ] Verified no environment duplication
- [ ] Recommendations align with KISS/YAGNI
