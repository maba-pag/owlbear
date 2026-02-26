---
id: 7
title: 'P1-07: Create .python-version and src/owlbear/ package skeleton'
status: done
priority: high
created: 2026-02-24T15:04:25.2220612+01:00
updated: 2026-02-26T18:14:54.6287927+01:00
started: 2026-02-24T15:16:56.5323282+01:00
completed: 2026-02-26T18:14:54.6287927+01:00
tags:
    - phase-1
    - tooling
depends_on:
    - 6
class: standard
---

## Acceptance Criteria
- Create .python-version at project root containing '3.12'
- Create directory structure:
  src/owlbear/__init__.py (with __version__ = '0.1.0')
  src/owlbear/py.typed (empty marker file for PEP 561)
  src/owlbear/auth/__init__.py (empty, docstring: 'Authentication modules.')
  src/owlbear/agent/__init__.py (empty, docstring: 'Agent loop and orchestration.')
  src/owlbear/providers/__init__.py (empty, docstring: 'LLM provider abstractions.')
- Each __init__.py should have a module-level docstring and from __future__ import annotations
- Use UTF-8 encoding, LF line endings per .editorconfig

## Files to Create
- .python-version
- src/owlbear/__init__.py
- src/owlbear/py.typed
- src/owlbear/auth/__init__.py
- src/owlbear/agent/__init__.py
- src/owlbear/providers/__init__.py

## Verification
- python -c 'import owlbear; print(owlbear.__version__)' prints '0.1.0' (after uv sync)
- All __init__.py files have from __future__ import annotations
- Directory structure matches src layout in pyproject.toml
