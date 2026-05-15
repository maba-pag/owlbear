---
description: "Run a read-only Cockpit frontend audit for an optional scope using frontend design and convention guidance."
---

# Cockpit Frontend Audit

You are running a read-only Cockpit frontend audit and producing a severity-ranked report. This prompt is for critique and task discovery only; it does not edit source files.

Optional scope input: ${input:scope:Files or feature area to audit (optional)}

## Interaction Protocol

Use the user's language unless they ask otherwise. When presenting findings, proposed actions, or pause/continuation choices, present exactly one decision item at a time before calling `askQuestions`. Do not list multiple findings and ask for one bulk decision.

Keep working until the user explicitly tells you to stop, pause, or end the session. Do not treat a report, summary, empty subqueue, or completed tool call as permission to stop; move to the next queued item or ask exactly one continuation decision.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.

## Step 1 - Load context

1. Read `../skills/h-frontend-design/SKILL.md`.
2. Read `../skills/h-frontend-conventions/SKILL.md`.
3. If the scope includes test, lint, build, or E2E evidence, read `../skills/h-vitest-and-linting/SKILL.md`.
4. Use the frontend-design two-tier anti-pattern classification: blocker and heuristic.
5. Treat Cockpit as an internal developer-operations tool: dense but calm layout, predictable controls, clear status, and low decorative overhead.
6. Determine the target surface:
   - Use `${input:scope}` when provided.
   - If no scope is provided, choose one Cockpit page, route, component, or workflow and state it.

## Step 2 - Plan and scope

Before auditing, write a short plan that states:

1. What surface is in scope.
2. Which checks you will run in each required category.
3. Any constraints that could limit audit confidence.
4. Whether evidence can be gathered by file inspection, Vitest/jsdom, or Playwright/browser proof.

## Step 3 - Execute audit

Inspect the scoped surface and build an internal ranked queue across these categories:

1. accessibility
2. responsive behavior
3. design-system consistency
4. anti-patterns
5. test/proof adequacy

Classify every finding with these tiers:

- blocker: must-fix issues that block release quality.
- heuristic: warning-level issues for consistency or polish.

Rank findings by severity within each category. Present findings to the user one at a time with concrete evidence (affected files, selectors, components, or states) and the Interaction Protocol decision card.

Cockpit-specific checks:

- Prefer Porsche Design System components and tokens where they match the interaction.
- Flag PDS jsdom assumptions when tests rely on native roles or events that PDS custom elements do not expose.
- For responsive/layout claims, distinguish static CSS evidence from real browser geometry proof.
- Flag edit-style recommendations that should become kanban tasks instead of direct prompt-driven code changes.

## Step 4 - Verify and guardrails

Before final output:

1. Confirm this prompt does not edit code files and is report-only.
2. Confirm findings are severity-ranked and each finding is tagged blocker or
   heuristic.
3. Recommend one of these outcomes:
   - no action, with rationale.
   - a small direct follow-up for the user to approve.
   - a kanban task when the change needs implementation, tests, or review.
4. If multiple findings remain, summarize counts only and ask which single item to inspect next.

## Guardrails

- Do not edit or modify source files during this audit.
- Do not silently broaden scope beyond the selected surface.
- If structural issues are out of scope, record them as follow-up tasks.
- Do not recommend deleted frontend prompt commands as next steps.
