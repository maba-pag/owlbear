---
id: 294
title: Project definition workflow — structured idea-to-spec pipeline
status: archived
priority: critical
created: 2026-03-01T02:52:25.0301209+01:00
updated: 2026-03-01T06:33:08.9071653+01:00
started: 2026-03-01T06:12:48.633439+01:00
completed: 2026-03-01T06:33:08.9071653+01:00
tags:
    - phase-11
    - agent
    - planning
depends_on:
    - 293
class: standard
---

## Context
When a user says 'I have an idea: X', OwlBear needs a structured workflow to turn that into an actionable project spec. This is the CORE planning loop.

## Acceptance Criteria
- [ ] Define a ProjectDefinition Pydantic model: name, description, goals, requirements (functional/non-functional), acceptance_criteria, tech_stack, risks, open_questions
- [ ] Workflow: receive idea -> ask clarifying questions -> research feasibility -> propose definition -> iterate with user -> finalize
- [ ] Planner agent uses ask_user tool to propose options ('Here are 3 possible project scopes...')
- [ ] Uses knowledge toolset to search for prior art and relevant context
- [ ] Uses web_search to find libraries, frameworks, prior implementations
- [ ] Output: project definition document (markdown) + kanban tasks with AC
- [ ] The workflow is encode in the planner agent's system prompt + a skill file
- [ ] Integration test: mock LLM conversation showing idea -> definition flow
