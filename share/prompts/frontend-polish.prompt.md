---
description: "Apply a final frontend polish pass for a selected surface using local design context and frontend-design guidance."
---

# Frontend Polish

You are applying the last frontend detail pass before completion. Polish
improves finish quality without changing structure or intent.

Optional scope input: ${input:scope:Files or feature area to polish (optional)}

## Step 1 - Load context

1. Read `docs/design-context.md` if it exists. Use it as the source of truth
   for tone, users, accessibility, and design principles.
2. Read `../../skills/frontend-design/SKILL.md` and these references for targeted
   checks:
   - `../../skills/frontend-design/references/spatial-design.md`
   - `../../skills/frontend-design/references/interaction-design.md`
   - `../../skills/frontend-design/references/responsive-design.md`
   - `../../skills/frontend-design/references/ux-writing.md`
3. Determine the target surface:
   - Use `${input:scope}` when provided.
   - If no scope is provided, choose one page, route, or component and state it.

## Step 2 - Plan the polish pass

Before editing, write a short plan listing:

1. Files you will touch.
2. Which of the six polish categories apply.
3. What you will not change (layout structure, information architecture, or
   component strategy).

## Step 3 - Apply final-detail checks

Polish only these areas:

1. Spacing
   - Normalize rhythm, alignment, and visual balance.
   - Remove distracting density spikes or uneven gaps.
2. Interaction states
   - Ensure hover, active, disabled, and selected states are clear and
     consistent.
   - Keep state styling coherent with existing component patterns.
3. Copy consistency
   - Align button labels, helper text, and empty-state language to one voice.
   - Remove inconsistent capitalization, punctuation, or phrasing.
4. Focus treatment
   - Verify visible, accessible focus states for interactive elements.
   - Keep focus behavior predictable across inputs and controls.
5. Loading and empty states
   - Ensure each state is intentional, informative, and visually integrated.
   - Avoid abrupt blank screens or ambiguous status messaging.
6. Mobile readiness
   - Validate legibility, spacing, and touch target quality on small screens.
   - Check wrapping, overflow, and stacked layout behavior.

## Step 4 - Verify before completion

After edits, confirm:

1. Polish remained a finishing pass, not a redesign.
2. Keyboard navigation and focus visibility still work.
3. Interaction, loading, and empty states are consistent and intentional.
4. Copy tone is consistent with `docs/design-context.md`.
5. Mobile behavior is usable across common small and medium viewports.
6. No regressions were introduced in the scoped surface.

## Guardrails

- Do not re-architect flows, move major layout regions, or introduce new
  interaction patterns.
- Do not replace established components unless fixing a clear defect.
- Do not broaden scope beyond the selected surface.
- If you find structural issues, note them as follow-up work instead of
  redesigning during polish.
