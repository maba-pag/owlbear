---
id: 311
title: Update orchestrator system prompt with intent routing rules
status: archived
priority: critical
created: 2026-03-01T06:16:50.5609847+01:00
updated: 2026-03-01T17:09:36.0539444+01:00
started: 2026-03-01T06:16:55.8988765+01:00
completed: 2026-03-01T17:09:36.0539444+01:00
tags:
    - phase-12
    - agent
    - routing
depends_on:
    - 310
class: standard
---

Add structured intent routing section to src/owlbear/agents/orchestrator.md:

- [ ] Intent-to-agent mapping table in system prompt:
      | Intent   | Target agent | When to use |
      | plan     | planner      | idea, plan, break down, new feature, decompose |
      | build    | coder        | fix, implement, code, add test, refactor, debug |
      | research | researcher   | research, investigate, compare, best way to, evaluate |
      | review   | reviewer     | review, check, verify, is this correct, quality |
      | status   | (self)       | status, progress, board, standup, what's next |
      | question | ask_user     | ambiguous, unclear, general question |
- [ ] Decision framework: 'Read the user message. Classify intent. Delegate to the matching agent via delegate_to_agent.
- [ ] Mid-conversation rerouting rule: 'Re-evaluate intent each turn. If user redirects, switch agent.'
- [ ] Fallback rule: 'If intent is ambiguous, use ask_user to clarify before delegating.'
- [ ] Include one-line description for each agent (planner, coder, researcher, reviewer, writer) so the LLM knows capabilities
- [ ] Keep total system prompt under 1500 tokens
- [ ] Do NOT create a dedicated RouterAgent — orchestrator IS the router
- [ ] No new Python code — only edit orchestrator.md
- [ ] ruff check not applicable (markdown only)

See docs/research/conversation-router.md S4 for recommendation details
