---
id: 75
title: 'Test: owlbear-project.json generation in setup script'
status: backlog
priority: needed
created: 2026-03-26T20:37:44.1881492+01:00
updated: 2026-03-26T20:54:50.8412864+01:00
tags:
    - phase-1
    - scope:cli
    - test
depends_on:
    - 68
class: standard
---

## Objective
TDD RED phase: write failing tests for owlbear-project.json generation before builder implements.

## Test Scenarios
- [ ] Generates valid owlbear-project.json with all 5 required fields
- [ ] schema_version is 1
- [ ] owlbear_path is a forward-slash relative path (even on Windows)
- [ ] created_at is timezone-aware UTC ISO 8601
- [ ] Idempotent: does not overwrite existing file
- [ ] Output validates against OwlbearProjectFile model
- [ ] Name defaults to directory name when not provided
- [ ] Type defaults to bare when not provided
- [ ] Explicit name and type override defaults

## Context
Parent impl task: #69.
Model: OwlbearProjectFile from #68.
See docs/research/setup-script-project-json-generation.md.

[[2026-03-26]] Thu 20:53
## Research
Doc: docs/research/test-project-json-generation.md

Key findings:
- CRITICAL GAP FIXED: Added depends_on [68] -- model must be importable before tests are written
- Target function signature: generate_project_json(project_dir, owlbear_dir, *, name=None, project_type='bare') returning Path
- Use tmp_path fixture for filesystem isolation, monkeypatch for time freezing (no extra deps)
- Assert both raw JSON fields and model_validate_json() round-trip
- Test cross-platform paths by asserting forward slashes in owlbear_path
- Idempotency test: pre-create file with sentinel content, call function, assert sentinel preserved

Dependency fix:
- Added depends_on: [68] (OwlbearProjectFile model must exist for import)

AC refinement recommendations for architect:
- Confirm target function signature and module location (proposed: mcp_project.setup)
- Consider whether name/type defaults should be tested in #75 or deferred to a CLI integration test
