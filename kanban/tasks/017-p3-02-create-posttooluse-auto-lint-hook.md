---
id: 17
title: 'P3-02: Create PostToolUse auto-lint hook'
status: ideation
priority: medium
created: 2026-02-24T15:10:07.746675+01:00
updated: 2026-02-26T18:52:59.0362649+01:00
tags:
    - phase-3
    - hooks
    - tooling
depends_on:
    - 16
    - 11
class: standard
---

AC: Create .github/hooks/post-tool-use-lint.json (or appropriate format per P3-01 research). Hook fires after file-edit tools. Runs 'uv run ruff check --fix' on edited Python files. Include backing script (PowerShell or Python via uv run). Handle: only trigger for .py files, skip non-Python edits. If VS Code hooks not yet stable, comment out config with explanation. Test manually by editing a .py file in Copilot. Files: .github/hooks/post-tool-use-lint.json + backing script.
