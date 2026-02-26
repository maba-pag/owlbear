---
id: 40
title: Implement SkillRegistry with progressive loading
status: done
priority: high
created: 2026-02-26T15:56:51.5667047+01:00
updated: 2026-02-26T20:48:36.4337208+01:00
started: 2026-02-26T19:41:55.6455363+01:00
completed: 2026-02-26T20:48:36.4337208+01:00
tags:
    - phase-2
    - agent
depends_on:
    - 39
class: standard
---

## Research findings (See docs/pydantic-ai-integration-research.md §3.2)

PydanticAI has no skill/progressive loading concept. pydantic-deepagents provides SkillsToolset(FunctionToolset) — markdown files with YAML frontmatter, list_skills + load_skill tools, directory scanning. Nanobot uses summary + lazy loader pattern.

**Decision:** Build as PydanticAI FunctionToolset. Skills are markdown files with YAML frontmatter (name, description). Registry provides list_skills (summaries in system prompt) and load_skill (full content on demand).

**Prior art:**
- pydantic-deepagents toolsets/skills/ — 7 files, comprehensive implementation
- nanobot — SKILL.md with summary + lazy loader
- VS Code GitHub Copilot — skills defined as markdown in .github/skills/

## AC
Src: src/owlbear/skills/registry.py with SkillRegistry(FunctionToolset). Skills as markdown with YAML frontmatter. list_skills and load_skill tools. Tests verify progressive loading.
