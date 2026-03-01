---
id: 325
title: 'Integration test: mock LLM project definition flow'
status: archived
priority: important
created: 2026-03-01T06:32:58.0284767+01:00
updated: 2026-03-01T17:09:50.3853847+01:00
started: 2026-03-01T06:33:02.8470902+01:00
completed: 2026-03-01T17:09:50.3853847+01:00
tags:
    - phase-11
    - planning
    - test
    - integration
depends_on:
    - 320
    - 322
    - 324
class: standard
---

## Acceptance Criteria
- [ ] Create tests/test_project_definition_flow.py
- [ ] pydantic_ai.models.ALLOW_MODEL_REQUESTS = False (no real LLM calls)
- [ ] Test: build a ProjectDefinition with sample data, pass to ProjectDefinitionExtractor (mock Agent.run), verify output is valid ProjectDefinition with populated name, description, goals (non-empty), requirements (>= 1)
- [ ] Test: pass ProjectDefinition to project_definition_to_markdown(), verify markdown contains section headers (Goals, Requirements, Acceptance Criteria)
- [ ] Test: verify optional empty sections are omitted from markdown output
- [ ] Test: end-to-end pipeline — mock extractor -> markdown generator -> validate markdown
- [ ] Uses _mock_agent_run pattern from test_knowledge_extractor.py
- [ ] Does NOT test planner agent multi-turn conversation (out of scope — that requires FunctionModel + tool mocking)

Dependencies: #320 (extractor impl), #322 (markdown impl), #324 (planner update)
See docs/project-definition-workflow-research.md sec3.6
