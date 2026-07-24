---
description: "Run a read-only legacy cleanup audit and produce a ranked report of stale references and compatibility residue."
---

# Legacy Audit

You are running a read-only cleanup audit and producing a severity-ranked report.

Optional scope input: ${input:scope:Files or surface to audit (optional)}

## Interaction Protocol

Use the user's language unless they ask otherwise. Keep working until the user explicitly stops or
pauses. Present exactly one finding, action, or continuation decision before each `askQuestions`;
never request a bulk decision. A report, empty queue, or completed tool call is not a stop condition.

When asking the user to choose an action, include status quo, problem, options with
pro/con/risk/confidence, recommendation, and expected outcome. Include `(bp:)` and `(rec:)` when
useful.

## Step 1 - Load context

Determine scope:

- Use `${input:scope}` when provided.
- If no scope is provided, audit the workspace root.

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

If many findings remain, summarize counts only and ask which single item to inspect next.

## Step 4 - Guardrails and closeout

Before final output, confirm that no files changed; all five categories appear in the required order
with severity, evidence, and confidence; and cleanup actions remain suggestions for user decision.

## Guardrails

- Do not broaden scope silently beyond the selected surface.
