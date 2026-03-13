---
id: 523
title: Eliminate post-construction patching in bootstrap
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:31.3955566+01:00
updated: 2026-03-07T00:12:22.3596401+01:00
started: 2026-03-07T00:06:03.5267617+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-14: bootstrap creates placeholder for ProjectToolset, patches real agent after construction. agent._deps.agent_registry set after agent construction. Two-phase init creates temporal coupling. Use lazy property or reorder construction. See docs/architecture-audit.md.

## AC

- [ ] No post-construction patching of agent or agent._deps
- [ ] ProjectToolset constructed before Agent, or accessed via lazy property
- [ ] Existing tests pass
- [ ] Ruff clean
