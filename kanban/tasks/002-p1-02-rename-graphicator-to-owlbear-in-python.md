---
id: 2
title: 'P1-02: Rename Graphicator to OwlBear in python.instructions.md'
status: done
priority: high
created: 2026-02-24T15:03:03.1833992+01:00
updated: 2026-02-26T16:34:51.7025497+01:00
started: 2026-02-24T15:16:56.373085+01:00
completed: 2026-02-26T16:34:51.7025497+01:00
tags:
    - phase-1
    - config
    - rename
class: standard
---

## Acceptance Criteria
- Replace ALL paths 'src/graphicator/' with 'src/owlbear/' in .github/instructions/python.instructions.md
- Update coverage command: --cov=src/graphicator -> --cov=src/owlbear
- Update tests example: tests/test_db/test_crud.py for src/graphicator/db/crud.py -> tests/test_db/test_crud.py for src/owlbear/db/crud.py
- Update config reference: src/graphicator/config.py -> src/owlbear/config.py
- Update COPILOT_FREE_MODELS reference if it exists
- Update Project layout section: Source: src/graphicator/ -> Source: src/owlbear/

## Files to Edit
- .github/instructions/python.instructions.md

## Verification
- grep -i 'graphicator' .github/instructions/python.instructions.md returns zero results
- File is valid Markdown with correct YAML frontmatter
