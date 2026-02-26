---
id: 8
title: 'P1-08: Create src/owlbear/config.py settings module'
status: done
priority: high
created: 2026-02-24T15:04:38.4330922+01:00
updated: 2026-02-26T18:14:56.9028516+01:00
started: 2026-02-24T15:16:56.5690286+01:00
completed: 2026-02-26T18:14:56.9028516+01:00
tags:
    - phase-1
    - config
    - model
depends_on:
    - 7
class: standard
---

## Acceptance Criteria
- Create src/owlbear/config.py with a Pydantic BaseSettings class 'OwlBearSettings'
- Settings fields (all with sensible defaults):
  - provider: Literal['copilot'] = 'copilot' (future: 'lm_studio')
  - copilot_token_path: Path = Path.home() / '.owlbear' / 'copilot_token.json'
  - chat_model: str = 'gpt-4o' (the model name for the Copilot API)
  - copilot_base_url: str = 'https://api.individual.githubcopilot.com'
  - debug: bool = False
- Use model_config with env_prefix='OWLBEAR_' for env var support
- Use from __future__ import annotations
- Include type hints on all fields
- Keep it minimal — no database settings, no embedding settings (YAGNI)

## Files to Create
- src/owlbear/config.py

## Verification
- from owlbear.config import OwlBearSettings; s = OwlBearSettings() succeeds
- All fields have correct types and defaults
- OWLBEAR_PROVIDER env var overrides provider field
- ruff check passes on the file
