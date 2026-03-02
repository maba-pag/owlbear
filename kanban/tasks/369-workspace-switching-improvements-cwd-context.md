---
id: 369
title: Workspace switching improvements — CWD + context reload
status: backlog
priority: important
created: 2026-03-01T20:13:00.7251343+01:00
updated: 2026-03-01T20:22:36.2101449+01:00
started: 2026-03-01T20:22:36.2101449+01:00
tags:
    - phase-13
    - agent
    - tools
class: standard
---

From #303 project-workspace-research.md. Fix switch_project so it also updates ContextManager.workspace_root and any toolsets holding workspace_root reference. CWD change for subprocess calls. Separate concern from scaffolding. AC: After switch_project, ContextManager uses new workspace root; subprocess-based tools operate in new workspace; session path updated. Depends on #303.
