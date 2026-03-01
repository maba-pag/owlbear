---
id: 318
title: ProjectDefinition Pydantic model and Requirement sub-model
status: archived
priority: needed
created: 2026-03-01T06:31:13.8632061+01:00
updated: 2026-03-01T17:09:43.5003798+01:00
started: 2026-03-01T06:31:18.9871562+01:00
completed: 2026-03-01T17:09:43.5003798+01:00
tags:
    - phase-11
    - planning
    - agent
depends_on:
    - 317
class: standard
---

## Acceptance Criteria
- [ ] Create src/owlbear/planning/__init__.py (empty)
- [ ] Create src/owlbear/planning/models.py
- [ ] Requirement model: description (str, required), kind (Literal['functional', 'non-functional'], required), priority (str, default 'important')
- [ ] ProjectDefinition model: name (str), description (str), goals (list[str]), requirements (list[Requirement]), acceptance_criteria (list[str]), tech_stack (list[str], default=[]), risks (list[str], default=[]), open_questions (list[str], default=[])
- [ ] All optional list fields use Field(default_factory=list)
- [ ] Both models use ConfigDict(frozen=True) following ExtractionResult pattern
- [ ] All tests in tests/test_project_definition_models.py pass

Patterns: owlbear/memory/knowledge/extractor.py ExtractionResult, owlbear/memory/knowledge/models.py Entity
See docs/project-definition-workflow-research.md sec3.3
