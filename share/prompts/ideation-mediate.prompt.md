---
description: "Start Phase 2 ideation — synthesize discovery artifacts into an approved Brief and hand off to the pipeline"
agent: ideation-mediator
---

Mediate: ${input:draft_path_or_context:Working Directory path or brief context — e.g. '.owlbear/briefs/draft-export-surface/' or 'continue from the export surface discovery'}

## Interaction Protocol

Use the user's language unless they ask otherwise. When presenting options, decisions, or continuation choices, present exactly one decision item at a time before calling `askQuestions`.

Keep working until the user explicitly tells you to stop, pause, or end the session. Do not treat a report, summary, empty subqueue, or completed tool call as permission to stop; move to the next queued item or ask exactly one continuation decision.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.

## When to use this

Use this prompt when you have completed Phase 1 discovery and these artifacts exist in the Working Directory:

- `context.md` — narrow problem snapshot
- `decisions.md` — choices made so far with rejected options
- `research-notes.md` — verified findings, candidate implications, open questions

If these don't exist yet, use `/ideation-discover` first.

## What happens

1. **Phase 2 Start** — the agent reads discovery artifacts in a fresh context
2. **M3: Landscape** — research findings are presented with attribution; gaps trigger targeted follow-up research
3. **Late Domain Panel** — architect, data, end-user, and security panelists evaluate approaches in parallel, then a pragmatist convergence produces `synthesis.md`
4. **M4: Decision Support** — panel findings are presented with expectation-fidelity framing; you make real choices with full trade-off framing
5. **Critic Validation (O15)** — adversarial stress-test findings are triaged before affecting the recommendation, including whether the plan preserves what was wanted rather than merely satisfying bare function
6. **M5: Brief Drafting** — walkthrough or self-review of the Brief before approval; after approval the Brief is the binding product promise
7. **M6: Handoff** — parent kanban task created, planner dispatched

## Tips

- If discovery artifacts are too thin, the agent will explain the gap and ask whether to return to `/ideation-discover`
- You control disclosure depth: summaries first, then specifics, then verbatim evidence on demand
- Critic findings are never bulk-accepted — you can reclassify or reject each one
