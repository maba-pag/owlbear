---
id: 366
title: 'Project templates: python-uv, python-pip, node'
status: archived
priority: important
created: 2026-03-01T20:12:37.1124285+01:00
updated: 2026-03-03T13:42:28.5980739+01:00
started: 2026-03-01T20:22:31.7060805+01:00
completed: 2026-03-03T13:42:28.5980739+01:00
tags:
    - phase-13
    - tools
    - git
class: standard
---

From #303 project-workspace-research.md. Hardcoded template functions: _scaffold_python_uv() (pyproject.toml uv-style, src/{slug}/, tests/, .python-version), _scaffold_python_pip() (pyproject.toml pip-style, requirements.txt), _scaffold_node() (package.json, src/, tsconfig.json). All share .gitignore + README + kanban from bare. AC: create_project(name, 'python-uv') produces working Python project with uv layout; same for python-pip and node templates. Depends on #303, #365.
