---
id: 488
title: Auto-register toolset aliases instead of hardcoded map
status: archived
priority: important
created: 2026-03-04T07:38:04.6142498+01:00
updated: 2026-03-07T18:07:55.8807944+01:00
started: 2026-03-06T21:05:41.2442635+01:00
completed: 2026-03-07T18:07:55.8807944+01:00
tags:
    - audit
    - refactor
    - scope:core
class: standard
---

ARC-15/INT-12: build_agent_registry() maintains hardcoded _aliases dict (11 entries). 4 toolsets missing. Research complete: see docs/research/toolset-alias-auto-registration.md.

Approach: Option A from research  add tool_alias class attribute to each FunctionToolset subclass. Resolver in build_agent_registry() reads it dynamically. Hardcoded _aliases dict deleted.

Exact alias mapping (15 entries):

| Class                  | tool_alias            |
|------------------------|-----------------------|
| FileToolset            | filesystem            |
| TerminalToolset        | terminal              |
| AskUserToolset         | ask_user              |
| BrowserToolset         | browser               |
| DelegationToolset      | delegation            |
| GitLocalToolset        | git_local             |
| GitHubToolset          | github                |
| KanbanToolset          | kanban                |
| KnowledgeToolset       | knowledge             |
| WebSearchToolset       | web_search            |
| BookmarkToolset        | bookmark              |
| VisualFeedbackToolset  | visual_feedback       |
| KnowledgeSourceToolset | knowledge_source      |
| ProjectToolset         | project               |
| SkillRegistry          | skills                |

AC:
- [ ] Every FunctionToolset subclass (above 15) declares tool_alias: ClassVar[str] = '...' per mapping table
- [ ] build_agent_registry() builds _aliases dict dynamically from tool_alias attrs (getattr on unwrapped inner class)
- [ ] Hardcoded _aliases dict in build_agent_registry() is deleted
- [ ] _resolve(name) still resolves both class names and aliases (existing contract preserved)
- [ ] Test: parametrized test asserts each of the 15 toolsets has non-empty tool_alias matching the mapping table
- [ ] Test: alias resolution  build_agent_registry with a mock toolset having tool_alias, verify _resolve returns it by alias
- [ ] All existing tests in test_bootstrap.py pass unchanged
- [ ] ruff clean

Patterns to follow:
- Unwrap chain: while hasattr(inner, 'wrapped'): inner = inner.wrapped (already in bootstrap.py L800-802)
- Merge alias-building into the existing tool_map loop (single pass over toolsets)
- tool_alias is a plain class attribute, not a property or descriptor

Files touched:
- src/owlbear/tools/filesystem.py, terminal.py, ask_user.py, browser/toolset.py, git_local.py, github_api.py, kanban.py, knowledge.py, web_search.py, knowledge_source.py, visual_feedback.py
- src/owlbear/memory/knowledge/bookmark_toolset.py
- src/owlbear/core/delegation.py
- src/owlbear/projects/toolset.py
- src/owlbear/skills/registry.py
- src/owlbear/bootstrap.py
- tests/test_bootstrap.py
