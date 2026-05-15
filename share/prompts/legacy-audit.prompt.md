---
description: "Run a read-only legacy cleanup audit and produce a ranked report of stale references and compatibility residue."
---

# Legacy Audit

You are running a read-only cleanup audit and producing a severity-ranked report.

Optional scope input: ${input:scope:Files or surface to audit (optional)}

## Interaction Protocol

Use the user's language unless they ask otherwise. When presenting findings, proposed actions, or pause/continuation choices, present exactly one decision item at a time before calling `askQuestions`. Do not list multiple findings and ask for one bulk decision.

Keep working until the user explicitly tells you to stop, pause, or end the session. Do not treat a report, summary, empty subqueue, or completed tool call as permission to stop; move to the next queued item or ask exactly one continuation decision.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.

## Step 1 - Load context

1. Determine scope:
   - Use `${input:scope}` when provided.
   - If no scope is provided, audit the workspace root.
2. Confirm this is report-only work. Do not edit or delete files.

## Step 2 - Execute scan checks

Inspect the scoped surface and collect an internal finding queue for all categories below.

1. Stale task TODOs
   - Find TODO references in the form `TODO(#nnnn)`.
   - For each task ID, check whether the task is archived or done.
   - Report TODO references that still point to archived/done tasks.
2. Dead references
   - Find dead imports (for example, ruff F401-style unused imports).
   - Find likely zero-caller functions via repository-wide call-site checks.
3. Mock staleness
   - Find mocks, fakes, or fixtures that reference obsolete interfaces or patterns.
4. Stale task-scoped tests
   - Find test files matching `test_*_{task_id}.py`.
   - Check whether referenced tasks are archived while the task-scoped test file remains.
5. Legacy naming residue
   - Find functions or modules with names containing:
     - `legacy`
     - `compat`
     - `bridge`
     - `shim`

## Step 3 - Produce ranked cleanup report

Build findings grouped by type using this exact section order:

1. stale-task-todos
2. dead-references
3. mock-staleness
4. stale-task-tests
5. legacy-naming

Within each group:

1. Rank entries by severity: high, medium, low.
2. Include evidence for each entry:
   - file path
   - symbol or pattern
   - short reason the item appears stale
   - task ID (when applicable)
3. Mark confidence for each entry (`high`, `medium`, `low`) when detection is heuristic.

Present findings to the user one at a time using the Interaction Protocol. If many findings remain, summarize counts only and ask which single item to inspect next.

## Step 4 - Guardrails and closeout

Before final output, confirm all conditions:

1. Report-only: no files were modified.
2. All five scan categories are represented.
3. Findings are grouped by type and severity-ranked.
4. No auto-fix actions were applied.
5. Final section includes recommended cleanup actions as suggestions only; user decides whether to act.

## Guardrails

- Do not apply automatic fixes.
- Do not delete tests, imports, or compatibility code.
- Do not broaden scope silently beyond the selected surface.
- If certainty is low, keep the finding and label confidence as low.
