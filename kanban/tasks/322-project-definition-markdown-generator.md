---
id: 322
title: Project definition markdown generator
status: archived
priority: needed
created: 2026-03-01T06:32:09.6927721+01:00
updated: 2026-03-01T17:09:47.0815822+01:00
started: 2026-03-01T06:32:14.954307+01:00
completed: 2026-03-01T17:09:47.0815822+01:00
tags:
    - phase-11
    - planning
    - agent
depends_on:
    - 321
class: standard
---

## Acceptance Criteria
- [ ] Create src/owlbear/planning/markdown.py
- [ ] Function: project_definition_to_markdown(defn: ProjectDefinition) -> str
- [ ] Output sections: h1 project name, description paragraph, Goals (h2 + bullet list), Requirements (h2 + grouped by kind with sub-headers Functional / Non-Functional), Acceptance Criteria (h2 + checklist with '- [ ]' items), Tech Stack (h2 + bullet list), Risks (h2 + bullet list), Open Questions (h2 + bullet list)
- [ ] Omit optional sections (tech_stack, risks, open_questions) when their lists are empty — no empty headings
- [ ] Requirements grouped by Requirement.kind: functional items under '### Functional', non-functional items under '### Non-Functional'
- [ ] Each requirement line includes priority if not 'important' (the default)
- [ ] Pure function — no I/O, no side effects, no imports beyond typing and owlbear.planning.models
- [ ] All tests in tests/test_project_definition_markdown.py pass

Pattern: string formatting, no Jinja — keep it simple
See docs/project-definition-workflow-research.md sec4
