---
id: 319
title: Test ProjectDefinitionExtractor with TestModel
status: archived
priority: needed
created: 2026-03-01T06:31:26.863578+01:00
updated: 2026-03-01T17:09:44.4171309+01:00
started: 2026-03-01T06:31:32.1497373+01:00
completed: 2026-03-01T17:09:44.4171309+01:00
tags:
    - phase-11
    - planning
    - test
depends_on:
    - 318
class: standard
---

## Acceptance Criteria
- [ ] Create tests/test_project_definition_extractor.py
- [ ] Test: given sample conversation text, extraction produces valid ProjectDefinition with populated name, description, goals
- [ ] Test: empty/whitespace input returns default ProjectDefinition() immediately (Agent.run not called)
- [ ] Test: LLM failure (RuntimeError) returns default ProjectDefinition(), does not raise
- [ ] Test: LLM failure logs warning message
- [ ] Test: accepts model string ('test') and TestModel object
- [ ] Uses mock Agent.run() pattern from test_knowledge_extractor.py (_mock_agent_run helper)
- [ ] Tests import from owlbear.planning.extractor (fail until impl completes)

Pattern: tests/test_knowledge_extractor.py
See docs/research/project-definition-workflow.md sec3.6
