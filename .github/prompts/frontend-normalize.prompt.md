---
description: "Normalize a scoped frontend surface using local design context and the frontend-design skill."
---

# Frontend Normalize

You are normalizing a frontend surface to match this repository's local design
context and shared UI patterns.

Optional scope input: ${input:scope}

## Step 1 - Load context

1. Read `docs/design-context.md` if it exists for project-specific design direction.
2. Read `../../skills/frontend-design/SKILL.md` for normalization guidance.
3. Determine the target surface:
   - Use `${input:scope}` when provided.
   - If no scope is provided, identify one page, route, or component and state it.

## Step 2 - Plan before edits

Write a short plan before changing files:

1. What is inconsistent in the selected surface.
2. Which files you will update.
3. Which changes are safe to apply now.

Do not edit files until the plan is complete.

## Step 3 - Execute normalization

Apply the plan and align the target surface across these dimensions:

1. typography
2. color
3. layout
4. spacing
5. component usage
6. token usage

Use existing project patterns first. Replace one-off CSS and ad-hoc values with
shared styles, reusable components, and design tokens when available.

## Step 4 - Verify after changes

After edits, verify:

1. accessibility checks still pass (keyboard, semantics, contrast, focus).
2. responsive behavior works across common viewport sizes.
3. unnecessary one-off styling was removed or consolidated into shared patterns.

## Guardrails

- Do not introduce new one-off styling when an existing shared pattern can be used.
- Do not hardcode visual values if matching tokens or shared variables exist.
- Do not create a divergent component pattern for a problem already solved.
- Do not reduce accessibility quality while normalizing visuals.
