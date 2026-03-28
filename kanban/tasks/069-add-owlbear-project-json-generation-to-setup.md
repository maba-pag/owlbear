---
id: 69
title: Add owlbear-project.json generation to setup script
status: backlog
priority: needed
created: 2026-03-26T20:05:10.7303339+01:00
updated: 2026-03-26T20:39:31.1828251+01:00
tags:
    - phase-1
    - scope:cli
depends_on:
    - 68
    - 75
class: standard
---

## Objective
Setup script (#12) must write owlbear-project.json using the OwlbearProjectFile model.

## Acceptance Criteria
- [ ] Setup script writes owlbear-project.json with all 5 required fields
- [ ] schema_version set to 1
- [ ] owlbear_path computed as relative path from project root to owlbear installation
- [ ] created_at set to current UTC time in ISO 8601
- [ ] Idempotent: does not overwrite existing file (respects #12 AC)
- [ ] Validates output against OwlbearProjectFile model before writing

## Context
Depends on OwlbearProjectFile model task (#68). See docs/research/owlbear-project-json-schema.md.

[[2026-03-26]] Thu 20:38
## Research
Doc: docs/research/setup-script-project-json-generation.md

Key findings:
- Use os.path.relpath() + PurePath.as_posix() for cross-platform owlbear_path computation
- Accept name/type via argparse with defaults (dirname, bare) for automation safety
- Pydantic construct-then-serialize pattern for validation (no separate validate step)
- Simple Path.exists() guard for idempotency
- Added depends_on: [68, 75]

Follow-up tasks created:
- #75 Test: owlbear-project.json generation in setup script (ideation)

AC refinement recommendations for architect:
- Add AC for cross-platform path: owlbear_path must use forward slashes in JSON
- Consider adding optional --name/--type CLI args to setup script (currently unspecified in #12 AC)
- Note: os.path.relpath raises ValueError on Windows cross-drive paths (document as constraint)
