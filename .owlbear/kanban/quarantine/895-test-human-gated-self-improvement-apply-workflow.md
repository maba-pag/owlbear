---
id: 895
title: Test human-gated self-improvement apply workflow for agent definitions
status: archived
priority: someday
created: 2026-03-21T13:19:32.1388199+01:00
updated: 2026-03-21T13:19:32.1388199+01:00
tags:
    - phase-14
    - agent
    - safety
    - test
    - type:test
    - scope:core
depends_on:
    - 894
class: standard
---

Split from #146. Owns RED coverage for the human-gated review and apply half of the self-improvement pipeline. Scope is limited to agent definition files under .github/agents and must default safe on every denial or validation failure.

AC:

- Failing tests define a dedicated apply surface for approved self-improvement proposals; the workflow does not call raw write_file or create_file directly.
- Failing tests cover explicit denial and timeout returning safe no-op results with no file mutation.
- Failing tests cover preview or diff generation before any approval decision.
- Failing tests cover validation of modified agent markdown via parse_agent_definition() and rejection of invalid or non-agent targets.
