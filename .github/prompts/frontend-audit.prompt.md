---
description: "Run a read-only frontend audit for an optional scope using local design context and frontend-design guidance."
---

# Frontend Audit

You are running a read-only frontend audit and producing a severity-ranked report.

Optional scope input: ${input:scope:Files or feature area to audit (optional)}

## Step 1 - Load context

1. Read `docs/design-context.md` if it exists.
2. Read `../skills/frontend-design/SKILL.md`.
3. Read `../skills/frontend-design/references/anti-patterns.md` and use its
   two-tier finding classification: blocker and heuristic.
4. Determine the target surface:
   - Use `${input:scope}` when provided.
   - If no scope is provided, choose one page, route, or component and state it.

## Step 2 - Plan and scope

Before auditing, write a short plan that states:

1. What surface is in scope.
2. Which checks you will run in each required category.
3. Any constraints that could limit audit confidence.

## Step 3 - Execute audit

Inspect the scoped surface and report findings across exactly these categories:

1. accessibility
2. responsive behavior
3. design-system consistency
4. anti-patterns

Classify every finding with the anti-pattern taxonomy tiers:

- blocker: must-fix issues that block release quality.
- heuristic: warning-level issues for consistency or polish.

Rank findings by severity within each category and include concrete evidence for
each finding (affected files, selectors, components, or states).

## Step 4 - Verify and guardrails

Before final output:

1. Confirm this prompt does not edit code files and is report-only.
2. Confirm findings are severity-ranked and each finding is tagged blocker or
   heuristic.
3. Recommend next commands or follow-up tasks:
   - `/frontend-normalize` for structural consistency cleanup.
   - `/frontend-polish` for final-detail finishing.

## Guardrails

- Do not edit or modify source files during this audit.
- Do not silently broaden scope beyond the selected surface.
- If structural issues are out of scope, record them as follow-up tasks.