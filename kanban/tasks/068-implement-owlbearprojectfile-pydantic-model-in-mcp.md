---
id: 68
title: Implement OwlbearProjectFile Pydantic model in mcp-project
status: backlog
priority: needed
created: 2026-03-26T20:05:03.2636263+01:00
updated: 2026-03-26T20:32:58.6512496+01:00
tags:
    - phase-1
    - scope:mcp
depends_on:
    - 41
    - 74
class: standard
---

## Objective
Create OwlbearProjectFile Pydantic model per schema spec in docs/research/owlbear-project-json-schema.md.

## Acceptance Criteria
- [ ] Pydantic model with schema_version, name, type, owlbear_path, created_at
- [ ] extra='allow' for forward compatibility
- [ ] Validation: schema_version=1, name non-empty <=100 chars, type enum, owlbear_path non-empty, created_at ISO 8601
- [ ] Unit tests for valid and invalid payloads
- [ ] Model importable from mcp_project package

## Context
See docs/research/owlbear-project-json-schema.md for full specification.

[[2026-03-26]] Thu 20:32
## Research
Doc: docs/research/owlbear-project-file-model-impl.md

Key findings:
- Use AwareDatetime (from pydantic) for created_at to enforce timezone requirement per schema spec
- Keep owlbear_path validation simple (min_length=1); path traversal checks are YAGNI
- Dependency chain: #7 (monorepo) then #41 (scaffold) then #74 (tests) then #68 (impl)
- Added depends_on: [41, 74]
- model_validate_json() recommended for consumers (server resource handler)

Follow-up tasks created:
- #74 Test: OwlbearProjectFile Pydantic model (ideation)

AC refinement recommendation for architect:
- AC3: clarify created_at uses AwareDatetime (timezone-aware only)
- AC4: confirm owlbear_path validation scope (min_length=1 vs path traversal check)
