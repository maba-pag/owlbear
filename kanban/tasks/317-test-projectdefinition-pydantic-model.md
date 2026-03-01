---
id: 317
title: Test ProjectDefinition Pydantic model
status: archived
priority: needed
created: 2026-03-01T06:30:59.474415+01:00
updated: 2026-03-01T17:09:42.5612872+01:00
started: 2026-03-01T06:31:05.8432349+01:00
completed: 2026-03-01T17:09:42.5612872+01:00
tags:
    - phase-11
    - planning
    - test
class: standard
---

## Acceptance Criteria
- [ ] Create tests/test_project_definition_models.py
- [ ] Test ProjectDefinition with all required fields (name, description, goals, requirements, acceptance_criteria) passes validation
- [ ] Test ProjectDefinition with optional fields omitted (tech_stack, risks, open_questions) defaults to empty lists
- [ ] Test Requirement sub-model: description (str) + kind (Literal['functional', 'non-functional']) valid
- [ ] Test Requirement with invalid kind raises ValidationError
- [ ] Test ProjectDefinition with missing required field (name) raises ValidationError
- [ ] Test both models are frozen (ConfigDict(frozen=True)) — assignment raises ValidationError
- [ ] Tests import from owlbear.planning.models (will fail until impl task completes)

See docs/project-definition-workflow-research.md sec3.3
Follows test_knowledge_extractor.py structure.
