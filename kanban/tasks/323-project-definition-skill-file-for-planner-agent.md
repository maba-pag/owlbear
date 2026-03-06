---
id: 323
title: project-definition skill file for planner agent
status: archived
priority: needed
created: 2026-03-01T06:32:26.7107152+01:00
updated: 2026-03-01T17:09:48.1225516+01:00
started: 2026-03-01T06:32:31.849395+01:00
completed: 2026-03-01T17:09:48.1225516+01:00
tags:
    - phase-11
    - planning
    - docs
class: standard
---

## Acceptance Criteria

- [ ] Create .github/skills/project-definition/SKILL.md
- [ ] YAML frontmatter: name: project-definition, description (reference LLM-guided project scoping), user-invocable: false
- [ ] Workflow template section: 6 numbered steps (receive idea, clarify via ask_user, research via knowledge+web_search, propose definition, iterate with user, finalize)
- [ ] ProjectDefinition field reference table (field, type, required/optional) for LLM context
- [ ] Example ask_user interaction showing multi-option presentation pattern
- [ ] Skill is loadable by SkillRegistry: YAML frontmatter parses without error
- [ ] Follows .github/skills/kanban-md/SKILL.md structure (frontmatter + markdown body)

See docs/project-definition-workflow-research.md sec3.4
