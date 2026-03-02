---
id: 368
title: 'Agent tool: workspace_create_project on ProjectToolset'
status: backlog
priority: important
created: 2026-03-01T20:12:51.8220161+01:00
updated: 2026-03-01T20:22:34.7598239+01:00
started: 2026-03-01T20:22:34.7598239+01:00
tags:
    - phase-13
    - agent
    - tools
    - git
class: standard
---

From #303 project-workspace-research.md. Extend ProjectToolset with workspace_create_project(name, template) tool that delegates to ProjectWorkspace.create_project(). AC: Agent can call workspace_create_project to scaffold a new project; returns path and confirmation. Depends on #303, #365.
