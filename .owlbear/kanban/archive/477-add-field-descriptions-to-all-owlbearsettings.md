---
id: 477
title: Add Field descriptions to all OwlBearSettings config fields
status: archived
priority: needed
created: 2026-03-04T07:37:55.648052+01:00
updated: 2026-03-06T19:28:25.6615813+01:00
started: 2026-03-06T16:37:30.5156274+01:00
completed: 2026-03-06T19:28:25.6615813+01:00
tags:
    - audit
    - docs
    - config
class: standard
---

## Acceptance Criteria

- [ ] All 30+ fields in OwlBearSettings use `Field(description=...)`  
- [ ] Descriptions include units where applicable (e.g. 'Seconds before...', 'Token budget...')
- [ ] Descriptions include valid ranges where applicable (e.g. '>= 0', '0.01.0')
- [ ] Descriptions include behavioral implications where not obvious from name/type alone
- [ ] Existing validators, defaults, and model_config preserved unchanged
- [ ] `test_config.py` gains one regression test: iterate `OwlBearSettings.model_fields` and assert every field has a non-empty `description`  
- [ ] All existing tests pass unchanged (`uv run pytest tests/test_config.py -q --tb=short`)
- [ ] `uv run ruff check src/owlbear/config.py` passes

## Implementation Notes

- Use `Field(default=..., description='...')` pattern  see research table in task body for per-field description text
- Follow existing `field_validator` / `model_validator` locations  don't move them
- Import `Field` from `pydantic` (already available via pydantic-settings)
- ~60-line diff (30 fields  ~2 lines each for Field() wrapping)

## Research

See original research findings below and docs/documentation-audit.md for context.
