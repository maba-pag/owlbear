# Decisions — doc-writer quality

## Project type

**Decision: existing-feature/refactor.**

The doc-writer agent and w-doc-update skill already exist (shipped as part of docs-currency-2026-04-19 brief). The problem is behavioral quality — what the agent actually does when it runs, not whether the infrastructure exists.

## Investment tier

**Decision: Shared.**

Multi-consumer impact: broken docs affect all pipeline agents and future consumer projects.

## Verification scope per task

**Decision: Option C — full-file scan + task-scoped fix + follow-up flagging.**

When a task touches code in a package, the doc-writer reads the *entire* relevant README/doc (not just the section about the changed method). It fixes issues caused by the task's changes inline. Pre-existing issues unrelated to the task get flagged as follow-up kanban tasks.

Rejected options:
- A (task-scoped verification only): the current design, which never catches pre-existing rot. This is the root cause of the problem.
- B (full-file fix everything inline): muddies commit attribution — unrelated fixes get attributed to the current task.

## Diagram ownership

**Decision: remove diagram work from doc-writer entirely.**

All diagram responsibility (footer timestamps, content verification, creation, fixes) moves to doc-audit. The doc-writer pipeline gate no longer touches .excalidraw files.

Pro: pipeline stays fast, diagrams get proper editorial attention in audit sweeps.
Con: diagram footer dates go stale between audits (no longer auto-maintained per task).
User accepted the staleness trade-off — verification theater (stamping dates without reading content) is worse than honest staleness.

## Docstring depth

**Decision: cut — handled by ruff D100, not doc-writer.**

Challenger pressure: module docstrings are a code-quality concern, not a documentation concern. Adding LLM-powered docstring verification smuggles a new responsibility into a fix for a different problem.

## Pipeline speed

**Decision: tiered approach emerges from outcomes #1 and #3 — not a standalone deliverable.**

## Pre-existing issue handling

**Decision: TODO markers inline in the doc.**

When the doc-writer finds a pre-existing issue unrelated to the current task, it inserts a `<!-- TODO: [description] -->` marker directly in the doc file. This is:
- Visible to humans reading the doc ("this section may be stale")
- Machine-parseable by doc-audit ("find all TODO markers and fix them")
- No kanban task dedup needed
- No board flooding

Rejected options:
- Follow-up kanban tasks per issue: creates duplicates when multiple tasks touch the same package; floods the board when docs are broadly stale.
- Log-only in Docs Gate section: invisible to future readers; not actionable by doc-audit.

## doc-audit scope

**Decision: keep in same brief as doc-writer fix.**

User rejected split: "one problem, holistic solution." The doc-audit prompt is part of the same quality problem and depends on the TODO marker mechanism from outcome #1.

## Structural verification

**Decision: add for removal-focused checks only.**

Structural checks (symbol grep, signature comparison) catch stale references to removed or changed symbols. They don't catch missing documentation of new features — that remains LLM editorial judgment.

## D8 — 2026-05-08 16:00 — TODO marker visibility

**Status quo:** Locked outcome says markers are "visible to humans reading the doc" but the panel proposed HTML comments (invisible in rendered markdown).
**Decision to make:** How should markers appear?

**Options considered:**
- A: HTML-only (architect, data) — invisible in rendered docs, clean rendering, machine-parseable
- B: Visible for grep-confirmed removals + HTML for everything else (enduser) — two format variants
- C: Always visible blockquote markers (user preference)

**Chosen:** C — always visible. One format, no variants:
```
> **TODO:** {category} — {description} [#{task_id}]
```

**Rejected:**
- A because HTML comments are not "visible to humans" in rendered markdown — the locked claim would be false
- B because two format variants add complexity for a simple mechanism (user: "harder to clean up and more logic for such a simple thing")

**Source inputs:**
- User: "what's the problem with always visible? let's just do that"
- Enduser panel: identified the factual error in the "visible to humans" claim
- Architect/data concern about wall-of-warnings: acknowledged, user accepts

## D9 — 2026-05-08 16:00 — AST signature comparison

**Status quo:** Data panelist proposed ast.parse for task-changed functions. Architect opposed.
**Decision to make:** Include AST-based signature comparison?

**Chosen:** No. Grep for removals + LLM editorial is the design. Not staged as "v1" — this is the approach.

**Rejected:**
- AST comparison because: marginal value when LLM already reads full file + source; adds engineering cost; locked decision already scopes structural verification to "removal-focused checks only"

## D10 — 2026-05-08 16:00 — Marker schema

**Status quo:** Architect proposed 3-field pipe-delimited. Data proposed 4-category with agent namespace.
**Decision to make:** Marker format complexity.

**Chosen:** Categorized with 4 categories (`stale | inaccurate | missing | unverified`), no agent name:
```
> **TODO:** {category} — {description} [#{task_id}]
```

**Rejected:**
- Simple 3-field format: loses categorization value for doc-audit triage
- Agent-namespaced `TODO(doc-writer)`: user explicitly cut the agent name — simpler

## D11 — 2026-05-08 16:00 — Open questions batch

- **Doc-audit cadence:** Manual-only + sync-to-main pre-check as safety net
- **Sync-to-main enforcement:** Warning (list unresolved markers), not hard gate
- **Non-Python surface verification:** LLM-only; acceptable
- **Ruff D100 follow-up:** Separate backlog item, not in this brief
- **Section boundary:** Heading level (## and ###)
