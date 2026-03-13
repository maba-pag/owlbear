---
name: arch-review
description: "Architecture review workflow: read task + research → analyze codebase → evaluate architecture → decide (approve/refine/split/merge/block) → produce report. Used by the architect agent."
---

# Architecture Review

Step-by-step process for reviewing researched tasks, refining acceptance criteria,
ensuring architectural soundness, and approving tasks for development.

## Step 1 — Read task and research

Read the single task dispatched to you:

1. `kanban\kanban-md.exe show {id}` — read full details, verify `backlog` status
2. `kanban\kanban-md.exe edit {id} --claim <agent>` — claim by ID (never use `pick`)
3. If task references a research doc (`docs/research/{slug}.md`), read it
4. Note each AC line for evaluation

Initialize `manage_todo_list` with steps to complete.

## Step 2 — Analyze codebase context

1. Use `search` to find related modules, interfaces, patterns
2. Use `read_file` to examine existing code the task will touch
3. Check `depends_on` — are dependencies actually `done`?
4. Identify: existing patterns to follow, interfaces to respect, invariants to maintain
5. Check the task body for prior context — architecture notes, research pointers,
   reviewer feedback from previous cycles.

<!-- DEACTIVATED: knowledge graph not yet available in VS Code agents.
Original: Query the knowledge graph for past failures via `query_knowledge`.
See kanban board for KG research task. -->

## Step 3 — Evaluate architecture

Assess the task against the codified standards in the `architecture-standards` skill
(read it with `read_file` if not already loaded)
and general architectural principles:

1. **Single responsibility** — one thing only? If "and" joins unrelated concerns, split.
2. **Interface clarity** — inputs, outputs, side effects clear from AC?
3. **Dependency correctness** — all listed? any missing?
4. **Module layering** — does the proposed change respect the dependency direction
   defined in the `architecture-standards` skill? No upward imports.
5. **TDD compliance** — preceding test task exists?
6. **KISS/YAGNI** — minimal scope? no hypothetical requirements?
7. **Pattern consistency** — follows existing codebase patterns (protocols, error taxonomy,
   toolset wrapping, config via pydantic-settings)?
8. **Security surface** — does the task introduce new system boundaries (user input,
   external APIs, file I/O)? If so, AC must include input validation requirements.
9. **Single domain** — does this task target exactly one domain (see canonical list in
   kanban-planner.agent.md)? Multi-domain → split. Edge case: an ancillary `config.py`
   field addition for a feature is NOT a domain violation — domain = primary concern.
10. **Failure Mode Map** — if the task introduces or modifies codepaths with potential
    failure modes, fill in the template below. Skip for docs/config-only tasks.

    | CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
    |----------|--------------|-----------|----------|-------------|
    | `store()` | DB write fails | `sqlite3.OperationalError` | Yes — retry 2× | Stale data until next sync |

## Step 4 — Decide and act

| Verdict     | When                              | Action                                                                  |
| ----------- | --------------------------------- | ----------------------------------------------------------------------- |
| **Approve** | AC precise, architecture sound    | `kanban\kanban-md.exe edit {id} --status todo --release`               |
| **Refine**  | Good concept, AC needs tightening | `kanban\kanban-md.exe edit {id} --body "..." --claim <agent>` (keep)   |
| **Split**   | Multiple responsibilities         | Create new tasks, update deps, edit/delete original, then `--release`   |
| **Merge**   | Two tasks = one logical change    | Edit one, delete redundant, then `--release`                            |
| **Block**   | Missing prerequisite or unclear   | `kanban\kanban-md.exe edit {id} --block "reason" --release`            |

## Step 5 — Produce report

Output a structured ArchitectReview for the task (see agent output format).

## Self-critique checklist

Before submitting:

- [ ] Read full task details and research doc
- [ ] Searched codebase for related patterns
- [ ] Checked task body for prior context on these modules
- [ ] Every AC line evaluated individually
- [ ] No vague AC remains
- [ ] TDD compliance checked
- [ ] Module layering validated against `architecture-standards` skill
- [ ] Security surface assessed (new boundaries have validation AC)
- [ ] Did NOT create/edit .py, .toml, or test files
- [ ] Dependency graph has no cycles
- [ ] Single-domain verified — task targets exactly one domain from the canonical list
- [ ] Failure mode map assessed (for tasks with new/modified codepaths)
