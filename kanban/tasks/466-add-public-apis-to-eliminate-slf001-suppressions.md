---
id: 466
title: Add public APIs to eliminate SLF001 suppressions
status: ideation
priority: needed
created: 2026-03-04T07:37:46.2112012+01:00
updated: 2026-03-04T07:37:46.2112012+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-05/INT-16: 10 instances of private attribute mutation across bootstrap, delegation, projects/toolset, knowledge/dedup. Needed: OwlBearDeps.set_agent_registry(), delegation_depth property, ProjectToolset.bind_agent(), toolsets update_workspace_root(), GraphStore.merge_entities() or connection property. AC: zero SLF001 suppressions remain. See docs/architecture-audit.md, docs/integration-audit.md.
