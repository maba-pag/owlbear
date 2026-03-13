---
id: 320
title: ProjectDefinitionExtractor — structured extraction from conversation
status: archived
priority: needed
created: 2026-03-01T06:31:42.3027096+01:00
updated: 2026-03-01T17:09:45.2902064+01:00
started: 2026-03-01T06:31:47.7573874+01:00
completed: 2026-03-01T17:09:45.2902064+01:00
tags:
    - phase-11
    - planning
    - agent
depends_on:
    - 319
class: standard
---

## Acceptance Criteria
- [ ] Create src/owlbear/planning/extractor.py
- [ ] ProjectDefinitionExtractor class with __init__(self, model: str | Model)
- [ ] Internal agent: Agent[None, ProjectDefinition] with output_type=ProjectDefinition
- [ ] System prompt instructs LLM to extract name, description, goals, requirements, acceptance_criteria, tech_stack, risks, open_questions from conversation text
- [ ] async extract(text: str) -> ProjectDefinition
- [ ] Empty/whitespace text returns ProjectDefinition() immediately (no LLM call)
- [ ] LLM failure caught (BLE001), returns ProjectDefinition(), logs warning via logger.warning()
- [ ] No metadata parameter — unlike EntityExtractor, this takes only text
- [ ] Follows EntityExtractor pattern exactly (src/owlbear/memory/knowledge/extractor.py)
- [ ] All tests in tests/test_project_definition_extractor.py pass

Pattern: owlbear/memory/knowledge/extractor.py EntityExtractor
See docs/research/project-definition-workflow.md sec4
