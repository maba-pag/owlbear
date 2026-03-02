---
id: 365
title: ProjectWorkspace core + project_root config + bare template
status: backlog
priority: needed
created: 2026-03-01T20:12:28.4216838+01:00
updated: 2026-03-01T20:22:29.9344732+01:00
started: 2026-03-01T20:22:29.9344732+01:00
tags:
    - phase-13
    - tools
    - git
    - config
class: standard
---

From #303 project-workspace-research.md. Add project_root: Path to OwlBearSettings (default ~/projects). Create ProjectWorkspace class in src/owlbear/projects/workspace.py with create_project(name, template) -> Path. Implements bare template (.gitignore, README.md, kanban/ via kanban-md init). Orchestrates: resolve dir, scaffold, git init, kanban-md init, register in ProjectStore. AC: ProjectWorkspace.create_project('my-proj', 'bare') creates dir with git repo, kanban board, README; project registered in store; project_root config field validated. Depends on #303.
