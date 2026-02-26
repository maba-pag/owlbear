---
id: 12
title: 'P1-12: Create README.md'
status: done
priority: medium
created: 2026-02-24T15:05:40.8404347+01:00
updated: 2026-02-26T18:15:07.0246125+01:00
started: 2026-02-24T15:16:56.6885366+01:00
completed: 2026-02-26T18:15:07.0246125+01:00
tags:
    - phase-1
    - docs
depends_on:
    - 4
class: standard
---

## Acceptance Criteria
- Create README.md at project root
- Content:
  - # OwlBear heading with a brief tagline
  - ## Overview: 2-3 sentence project description (from copilot-instructions.md purpose)
  - ## Quick Start: uv sync, uv run bearclaw --help, uv run bearclaw auth login
  - ## CLI (BearClaw): brief description that the CLI is called BearClaw
  - ## Architecture: mention nanobot-inspired, Copilot OAuth, PydanticAI agents
  - ## Inspiration: link to HKUDS/nanobot, openclaw/openclaw, and docs/sources.md for full attribution
  - ## Development: uv run pytest, uv run ruff check, pre-commit install
  - ## License: TBD or state the intended license
- Keep it under 80 lines — concise, not verbose
- Use proper Markdown formatting

## Files to Create
- README.md

## Verification
- README.md exists at project root
- Contains all required sections
- No broken links
- markdownlint passes
