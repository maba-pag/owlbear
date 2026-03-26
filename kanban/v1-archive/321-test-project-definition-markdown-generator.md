---
id: 321
title: Test project definition markdown generator
status: archived
priority: needed
created: 2026-03-01T06:31:56.0552676+01:00
updated: 2026-03-01T17:09:46.2292821+01:00
started: 2026-03-01T06:32:01.2151367+01:00
completed: 2026-03-01T17:09:46.2292821+01:00
tags:
    - phase-11
    - planning
    - test
depends_on:
    - 318
class: standard
---

## Acceptance Criteria
- [ ] Create tests/test_project_definition_markdown.py
- [ ] Test: project_definition_to_markdown(defn) returns str
- [ ] Test: output contains h1 with project name
- [ ] Test: output contains goals as markdown bullet list
- [ ] Test: output contains requirements grouped by kind (functional/non-functional)
- [ ] Test: output contains acceptance_criteria as markdown checklist (- [ ] items)
- [ ] Test: optional empty sections (tech_stack, risks, open_questions) are omitted from output
- [ ] Test: optional non-empty sections appear when populated
- [ ] Tests import from owlbear.planning.markdown (fail until impl completes)

See docs/research/project-definition-workflow.md sec4
