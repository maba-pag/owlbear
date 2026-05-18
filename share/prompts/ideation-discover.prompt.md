---
description: "Start Phase 1 ideation — sharpen a raw idea, fuzzy problem, or overscoped request into a bounded problem statement and research bridge"
agent: ideation-discoverer
---

Discover: ${input:idea_or_problem:Describe your idea, problem, or feature request — a sentence or two is enough to start}

## Interaction Protocol

Use the user's language unless they ask otherwise. When presenting options, decisions, or continuation choices, present exactly one decision item at a time before calling `askQuestions`.

Keep working until the user explicitly tells you to stop, pause, or end the session. Do not treat a report, summary, empty subqueue, or completed tool call as permission to stop; move to the next queued item or ask exactly one continuation decision.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.

## When to use this

Use this prompt when you have:

- a raw idea that needs shaping
- a fuzzy problem you can't quite articulate yet
- a feature request that might be overscoped
- a hunch that something should change but you're not sure what

You do NOT need a polished problem statement. The discovery phase will help you find it.

## What happens

1. **Setup** — a Working Directory is created at `.owlbear/briefs/draft-{name}/`
2. **M1: Understanding** — the agent probes your request, challenges assumptions, and records the problem in `context.md`
3. **M2: Outcomes + Early Challenge** — outcomes and an Expectation Signal are defined, including the First Useful Step as sequencing rather than replacement scope; early challengers (simplifier, first-principles, optionally outsider) pressure-test scope and framing
4. **Research Bridge** — a targeted research pass produces `research-notes.md`
5. **Commit + Handoff** — the Working Directory is committed and you get a paste-ready `/ideation-mediate` command to continue in a new chat

## Tips

- Drop reference files (screenshots, specs, prior art) into the `input/` folder before starting — the agent will read them
- Be honest about what you don't know; the agent is built to probe, not to agree
- If you already have discovery artifacts (`context.md`, `decisions.md`, `research-notes.md`), use `/ideation-mediate` instead
