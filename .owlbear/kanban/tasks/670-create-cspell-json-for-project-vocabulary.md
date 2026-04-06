---
id: 670
title: Create .cspell.json for project vocabulary
status: todo
priority: nice-to-have
created: 2026-04-06T22:22:52.1798651+02:00
updated: 2026-04-06T22:42:02.9799046+02:00
tags:
    - scope:ci
    - type:config
parent: 672
class: standard
---

## Objective\nCreate a .cspell.json config with project-specific vocabulary so the cspell linter in MegaLinter produces meaningful results instead of noise.\n\n## Context\nMegaLinter config enables SPELL_CSPELL for .md, .py, .ps1 files. Without a custom dictionary, every project term (OwlBear, kanban, MCP, ruff, pyproject, frontmatter, etc.) will be flagged as a spelling error. The first run would be unusable.\n\n## Acceptance Criteria\n- [ ] .cspell.json created at repo root\n- [ ] Custom words list covers project vocabulary (OwlBear, kanban, MCP, ruff, pyproject, uv, frontmatter, megalinter, etc.)\n- [ ] Language set to en\n- [ ] Ignore patterns for generated/vendored paths (.venv, v1, __pycache__, .egg-info, uv.lock)\n- [ ] Validated: `npx cspell lint --config .cspell.json` runs without excessive false positives on a sample file\n\n## Files Affected\n- .cspell.json (new file)
