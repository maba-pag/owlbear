---
id: 263
title: Create Quality-Runner subagent (agent.md + skill)
status: backlog
priority: needed
created: 2026-03-30T19:30:52.0129159+02:00
updated: 2026-03-30T20:34:53.7772234+02:00
tags:
    - scope:agents
    - phase-2
blocked: true
block_reason: 'Decision pending: docs/decisions/pending/228-esub-utility-subagents.md'
class: standard
---

Design and implement the Quality-Runner utility subagent per docs/research/subagent-nesting-architecture.md S3c. Assign-mode agent with pytest + ruff + coverage execution. Input/output contract defined in research doc.

AC:
- [ ] quality-runner.agent.md exists with assign-mode tools, user-invocable: false
- [ ] Encapsulates all pytest-and-linting skill pitfalls internally
- [ ] Returns structured text report (tests/lint/coverage/errors sections)
- [ ] Max 2 internal retries before reporting failure
- [ ] Timeout: 5 min full suite, 2 min scoped

Blocked by: decision request 228-esub-utility-subagents approval

[[2026-03-30]] Mon 20:34
## Research
Design validated per docs/research/quality-runner-subagent-design.md. Three refinements to #228 design:
1. 8 tools (added read/terminalLastCommand, execute/testFailure)
2. Use disable-model-invocation: true with agents array override
3. Embed top 5 pitfalls in agent body as skill-loading fallback

Refined AC proposed for architect review. Still blocked by decision 228-esub-utility-subagents.
