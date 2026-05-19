---
id: 896
title: Implement human-gated self-improvement apply workflow for agent definitions
status: archived
priority: someday
created: 2026-03-21T13:19:37.5344372+01:00
updated: 2026-03-21T13:19:37.5344372+01:00
tags:
    - phase-14
    - agent
    - safety
    - type:build
    - scope:core
depends_on:
    - 895
class: standard
---

Split from #146. Owns GREEN implementation for the human-gated review and apply half of the self-improvement pipeline. Scope is limited to agent definition files under .github/agents and must preserve the existing safety model.

AC:

- Add a dedicated self-improvement apply surface that only mutates .github/agents/*.md and rejects any target outside that tree.
- Reuse the existing human-approval path before any file write and present the user with a preview or diff summary of the proposed change.
- Approved changes are validated by re-parsing the modified agent definition; invalid proposals abort without persisting a broken file.
- Denied, timed out, or invalid proposals leave files unchanged and return a safe no-op result.
- Unit tests from #895 pass.
