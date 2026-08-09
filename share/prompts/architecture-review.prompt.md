---
description: "Review a codebase for module-deepening opportunities and explore one selected design"
---

# Architecture Review

Review scope: ${input:scope:Repository, package, or module scope}

Find architectural friction that can be reduced by deepening modules: increasing behavior available
through a smaller interface, improving locality, and testing through the same seam callers use.
This is a read-only review. Do not edit production code.

## Step 1 - Load Context

Read and follow:

1. `../skills/h-module-design/SKILL.md`
2. `../skills/h-codebase-orientation/SKILL.md`
3. `../skills/h-visual-output/SKILL.md`
4. `../skills/w-idea-refinement/SKILL.md`

Use an existing project glossary and relevant ADRs when present. Their absence does not block the
review, and this prompt does not create or require `CONTEXT.md`, `CONTEXT-MAP.md`, or `docs/adr/`.

## Step 2 - Explore Friction

Orient through the smallest useful indexes and targeted source reads. Treat navigation aids as
candidates, then verify every claim against source. Look for:

- one concept requiring repeated movement across shallow modules;
- interfaces nearly as complex as their implementations;
- change or bug knowledge duplicated across callers;
- tests that bypass the caller-facing interface;
- tightly coupled modules whose responsibilities leak across a seam;
- speculative seams with only one adapter.

Apply the deletion test. A useful module concentrates complexity behind its interface; deleting it
would spread that complexity back across callers. Do not recommend consolidation merely because two
files are small.

## Step 3 - Present Candidates

Write a self-contained HTML report under `.owlbear/scratch/` using `h-visual-output`. Each candidate
must include:

- affected modules and verified source anchors;
- current friction in terms of interface, depth, leverage, locality, or seam placement;
- a plain-language deepening direction, without committing to a final interface;
- before/after visualization;
- expected testing effect;
- dependency category from `h-module-design`;
- recommendation strength: `strong`, `worth exploring`, or `speculative`.

End with one top recommendation and why it has the best evidence-to-effort ratio. Open the report and
ask which candidate the user wants to explore. Do not edit production code.

## Step 4 - Explore the Selected Design

Use `w-idea-refinement` to sharpen the selected architecture idea: constraints, seam placement,
hidden behavior, dependency strategy, and the test surface. When materially different interfaces remain plausible, dispatch at
least three parallel design explorations with different goals: minimum interface, maximum
flexibility, and trivial common case. Compare results by depth, locality, seam placement, and
dependency cost, then recommend one design or a deliberate hybrid.

Finish with the confirmed Refined Idea Summary. Tell the user that `/design` resumes or creates the
native Specification session and carries the reviewed idea through explicit admission. Do not create
a second specification format or Delivery work manually.
