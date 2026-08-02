---
id: 913
title: Nuclear reset — delete all existing test files
status: archived
priority: medium
created: 2026-04-17T11:51:47.965070+00:00
updated: 2026-04-17T20:04:08.489869+00:00
tags:
- test-quality
- type:user-action
- scope:test
parent: 912
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #912

## AC

- All `tests/test_*.py` files deleted
- `tests/__init__.py` retained (package marker)
- Root `conftest.py` evaluated — keep if shared fixtures have lasting value, delete if task-coupled
- `git status` confirms only test file deletions
- Committed as `chore: delete all existing test files (#912)`

## Note

One-time human action. No pipeline processing needed.
