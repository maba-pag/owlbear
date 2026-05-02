---
id: 1298
title: 'P1-02: Doc/skill reference cleanup — remove Copilot CLI and ACP references
  from docs'
status: todo
priority: important
created: 2026-05-02T19:40:07.788907+00:00
updated: 2026-05-02T19:40:47.955929+00:00
tags:
- cleanup
parent: 1296
depends_on:
- 1297
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Remove all Copilot CLI / ACP orchestrator references from documentation, skills, prompts, and setup guides. Regenerate the doc-index.

Brief: see parent #1296 and `.owlbear/briefs/draft-dead-code-sweep/brief.md`

## Scope

### Edit
- `README.md` — remove Copilot CLI prerequisite, orchestrator directory row, orchestrator description paragraph, CLI commands section
- `README-consumer.md` — remove `owlbear-project.json` from setup output mention
- `.github/copilot-instructions.md` — change "built around Copilot CLI" to "built around VS Code and GitHub Copilot agents"
- `share/skills/r-architecture-standards/SKILL.md` — remove ACP dispatch intro paragraph and orchestrator row from package table
- `share/skills/w-research/SKILL.md` — change "Copilot CLI" to "VS Code" in stack check reference
- `share/prompts/arch-audit.prompt.md` — remove/replace `serve/orchestrator/` as example audit unit
- `setup/setup-guide.md` — remove `owlbear-project.json` table row
- `setup/sharing-guide.md` — remove `owlbear-project.json` table row

### Regenerate
- Run `uv run doc-index` to regenerate `.owlbear/doc-index.md`

### Out of scope
- `.owlbear/research/` files (historical record — preserved)
- References to the live VS Code `orchestrator.agent.md` or `w-orchestration` skill — those stay
- Code changes (done in #1297)

## AC

1. `grep -r "serve/orchestrator" README.md README-consumer.md .github/ share/skills/ share/prompts/ setup/` returns zero hits
2. `grep -r "Copilot CLI" . --include="*.md"` returns zero hits outside `.owlbear/research/`, `.owlbear/kanban/`, `.owlbear/scratch/`, `.owlbear/briefs/`
3. `grep -r "owlbear-project.json" setup/ README-consumer.md` returns zero hits
4. `.owlbear/doc-index.md` is regenerated and does not reference `serve/orchestrator`
5. `uv run ruff check` passes on all touched Python files (if any)
6. No references to the live VS Code orchestrator agent are removed (spot-check `share/agents/orchestrator.agent.md` still exists and is not modified)