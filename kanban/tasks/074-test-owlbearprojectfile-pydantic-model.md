---
id: 74
title: 'Test: OwlbearProjectFile Pydantic model'
status: in-progress
priority: needed
created: 2026-03-26T20:30:19.6232649+01:00
updated: 2026-03-28T01:13:38.3674958+01:00
tags:
    - phase-1
    - scope:mcp
    - test
depends_on:
    - 41
class: standard
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
