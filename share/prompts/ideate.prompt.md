---
name: "ideate"
description: "Refine a rough idea into proposal-ready shared understanding"
argument-hint: "Rough idea to refine"
---

Ideate: ${input:idea:Rough idea to refine before proposal creation}

Read and follow `w-idea-refinement`. Use its one-question interview to shape the rough idea into
proposal-quality shared understanding. Do not create OpenSpec artifacts or edit product code.

Look up repository facts instead of asking the user. For each refinement question, provide a
recommended answer, ask only one question, and wait. Compare options only when a genuine choice
emerges. Continue until the user confirms the Proposal-Readiness Gate.

Then present the skill's complete `Refined Idea Summary` and end with:

> Next: run `/opsx:propose` with this Refined Idea Summary to create the native OpenSpec
> Proposal, Specs, Design, and advisory Tasks.

Do not create a PRD, handoff file, or parallel specification document.
