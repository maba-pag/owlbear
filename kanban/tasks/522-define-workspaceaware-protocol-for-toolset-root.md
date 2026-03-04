---
id: 522
title: Define WorkspaceAware protocol for toolset root updates
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:30.7335607+01:00
updated: 2026-03-04T07:38:30.7335607+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-06: _update_toolset_roots() walks toolsets mutating _workspace_root and _root by hasattr check. New toolsets with different attr names break silently. Define WorkspaceAware protocol with public update_workspace(root). AC: all workspace toolsets implement protocol, no hasattr checks. See docs/architecture-audit.md.
