---
id: 48
title: Implement builder/validator agent roles
status: archived
priority: medium
created: 2026-02-26T15:57:37.7600531+01:00
updated: 2026-02-27T10:00:17.3144993+01:00
started: 2026-02-26T20:32:13.4334905+01:00
completed: 2026-02-27T10:00:17.3144993+01:00
tags:
    - phase-3
    - agent
depends_on:
    - 39
    - 40
    - 45
class: standard
---

See docs/research/agent-patterns.md para 3.3. Depends on agent loop (#45).

## Research required (gate: ideation to backlog)

1. **Theoretical validity** - Is builder/validator a good role split for OwlBear, or does the new researcher/architect/dev/reviewer/writer pipeline make this redundant?
2. **Prior art** - Study disler builder/validator team pattern, CrewAI agent roles, AutoGen agent configurations
3. **Technical feasibility** - How to enforce read-only mode for validator? Tool access controls in PydanticAI?
4. **Architecture fit** - These roles overlap with the new pipeline roles (researcher, architect, dev, reviewer, writer). Should this task be reconsidered?
5. **Implementation approach** - PydanticAI agent config with restricted tool sets vs separate agent definitions

## AC
Builder agent config with full tool access. Validator agent config with read-only tools. Tests verify validator cannot write.
