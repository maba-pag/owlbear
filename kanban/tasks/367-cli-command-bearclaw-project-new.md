---
id: 367
title: 'CLI command: bearclaw project new'
status: backlog
priority: important
created: 2026-03-01T20:12:45.0169078+01:00
updated: 2026-03-01T20:22:33.2874319+01:00
started: 2026-03-01T20:22:33.2874319+01:00
tags:
    - phase-13
    - cli
    - tools
    - git
class: standard
---

From #303 project-workspace-research.md. Add 'bearclaw project new <name> --template <t>' CLI command that calls ProjectWorkspace.create_project(). Template choices: bare, python-uv, python-pip, node. Resolves workspace path from settings.project_root + slugify(name). AC: 'bearclaw project new my-proj --template python-uv' creates scaffolded project at project_root/my-proj; registered in project store; prints path. Depends on #303, #365.
