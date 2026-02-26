---
id: 5
title: 'P1-05: Update tech stack table in copilot-instructions.md'
status: done
priority: high
created: 2026-02-24T15:03:51.8977003+01:00
updated: 2026-02-26T16:35:02.1789928+01:00
started: 2026-02-24T15:16:56.4543599+01:00
completed: 2026-02-26T16:35:02.1789928+01:00
tags:
    - phase-1
    - config
    - docs
depends_on:
    - 4
class: standard
---

## Acceptance Criteria
- Update the tech stack table in .github/copilot-instructions.md
- Clear all 'TODO: (old data, update if used)' markers
- Set actual values for OwlBear:
  | Component | Technology | Notes |
  | Language | Python 3.12+ | uv package manager, never bare pip |
  | LLM | GitHub Copilot OAuth | Individual API (api.individual.githubcopilot.com), future LM Studio support |
  | CLI | Typer | BearClaw CLI — subcommands: auth, run, (more TBD) |
  | Agents | PydanticAI | Structured output, dependency injection |
  | Retry | tenacity | Exponential backoff, jitter, max 5 attempts |
  | Database | None (file-based) | YAGNI — MVP uses file storage only |
  | Task board | kanban-md | Go CLI binary in kanban/, file-based kanban |
- Remove or comment out rows for: Parsing, Visualization, Embeddings (not needed yet)

## Files to Edit
- .github/copilot-instructions.md (tech stack table only)

## Verification
- No 'TODO' markers remain in the tech stack table
- Table has correct values for Language, LLM, CLI, Agents, Retry, Database, Task board
- The rest of the file is unchanged
