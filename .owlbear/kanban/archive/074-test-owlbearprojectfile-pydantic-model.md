---
id: 74
title: 'Test: OwlbearProjectFile Pydantic model'
status: archived
priority: medium
created: 2026-03-26 20:30:19.623265+01:00
updated: 2026-03-29 09:15:17.053764+02:00
started: 2026-03-29 09:15:12.628466+02:00
completed: 2026-03-29 09:15:12.628466+02:00
tags:
- phase-1
- scope:mcp
- test
depends_on:
- 41
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

TDD RED phase: write failing tests for OwlbearProjectFile model before builder implements.

## Test Scenarios

- [ ] Valid model construction with all 5 required fields
- [ ] Extra fields preserved (extra='allow' verified via model_extra)
- [ ] Invalid schema_version (0, 2, -1) rejected
- [ ] Empty name rejected; name >100 chars rejected
- [ ] Invalid type enum value rejected
- [ ] Empty owlbear_path rejected
- [ ] Naive datetime (no timezone) rejected
- [ ] Invalid datetime string rejected
- [ ] model_validate_json round-trip works
- [ ] Missing required field raises ValidationError (parametrize over all 5 fields)
- [ ] Each valid type value accepted (bare, python-uv, python-pip, node)

## Context

Parent impl task: #68.
Test file location: packages/mcp-project/tests/test_models.py
Import: from owlbear_mcp_project.models import OwlbearProjectFile (ImportError expected in RED)
See docs/research/owlbear-project-file-model-impl.md for implementation details.
Model spec: docs/research/owlbear-project-json-schema.md section 3.7.

## Research

Doc: docs/research/owlbear-project-file-tests.md

Key findings:

- Test file location: packages/mcp-project/tests/test_models.py (v2 package-local convention)
- Added depends_on: [41] for correct TDD ordering (scaffold then tests then impl)
- 2 test scenario gaps found and added: missing-required-field + valid-type-values
- AwareDatetime confirmed to reject naive datetimes (Pydantic docs)
- Import: from owlbear_mcp_project.models import OwlbearProjectFile (ImportError expected in RED)
- v1 prior art patterns validated (test_project_model.py, test_project_definition_models.py)

Total test scenarios: 11 (was 9, added 2)

[[2026-03-29]] Sun 08:11
## Builder Notes
- Files changed: packages/mcp-project/src/owlbear_mcp_project/models.py
- Tests: 37 passed, coverage 100% on models.py
- Lint: ruff clean
- Evidence: 37 FAILED (stub) turned GREEN after implementation
- Fixes applied: Full OwlbearProjectFile model with Literal[1], name Field constraints, Literal type enum, AwareDatetime, ConfigDict extra=allow

[[2026-03-29]] Sun 08:45
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Package already listed; no behavior/convention change |
| 2 | Docstrings complete | Yes | Pass | models.py: module docstring + OwlbearProjectFile class docstring covering behavior and extra='allow'; __init__.py: module docstring |
| 3 | docs/sources/overview.md | Yes | Updated | Added Pydantic v2 Models, Fields, AwareDatetime, Literal docs — 4 rows under new section for Tasks #68/#74 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research docs linked | Yes | Pass | owlbear-project-file-tests.md and owlbear-project-file-model-impl.md both exist and linked in task body |
| 6 | Scratch files | None | Pass | No docs/scratch/74-* files found |

### Files Updated
- docs/sources/overview.md (committed db9d07a)

### Scratch Files Cleaned
- None
