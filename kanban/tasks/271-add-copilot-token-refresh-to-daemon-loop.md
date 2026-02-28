---
id: 271
title: Add Copilot token refresh to daemon loop
status: archived
priority: needed
created: 2026-02-28T14:21:07.7375231+01:00
updated: 2026-02-28T23:54:34.8971686+01:00
started: 2026-02-28T15:55:13.9178582+01:00
completed: 2026-02-28T23:54:34.8971686+01:00
tags:
    - phase-8
    - agent
    - auth
depends_on:
    - 266
    - 269
class: standard
---

## Context

Copilot tokens expire (~30 min). Daemon must catch 401/403, rebuild model, retry.
See docs/bootstrap-assembly-research.md S3.6.

## Acceptance Criteria

- [ ] `_is_auth_error(exc: Exception) -> bool` helper in `daemon.py` returns True for: `httpx.HTTPStatusError` with status 401 or 403, `openai.AuthenticationError`, `openai.PermissionDeniedError`; False for all other exceptions
- [ ] `run_daemon()` inner try/except around `agent.turn()` catches auth errors: (1) calls `create_copilot_model(settings)` to get fresh model, (2) calls `agent.update_model(new_model)` to hot-swap, (3) retries `agent.turn(message)` once
- [ ] If the refresh itself fails (e.g. no network), the error is logged and sent to channel — no infinite retry loop
- [ ] If retry after refresh also fails with auth error, error is logged and sent to channel — single retry only
- [ ] Non-auth exceptions handled as before: logged via `logger.exception()` + `Error: {exc}` sent to channel
- [ ] `run_daemon()` uses `settings` parameter (added by #269) to call `create_copilot_model(settings)`
- [ ] Unit test in `test_daemon.py`: mock `agent.turn` to raise auth error on first call, succeed after `update_model`; verify `create_copilot_model` and `update_model` called
- [ ] Unit test: non-auth `RuntimeError` -> no refresh attempt, error sent to channel as before
- [ ] Unit test: refresh itself raises -> error sent to channel, loop continues
- [ ] TDD: write failing tests before implementing

## Architecture Notes

- `_is_auth_error()` in `daemon.py` (KISS — collocated with its only caller); extract to `auth/` if reused later
- Import `create_copilot_model` from `owlbear.providers.copilot` and `httpx`, `openai` for exception types
- Pattern from research doc S3.6:
  `python
  try:
      response = await agent.turn(message)
  except Exception as exc:
      if _is_auth_error(exc):
          model = await create_copilot_model(settings)
          agent.update_model(model)
          response = await agent.turn(message)  # retry once
      else:
          raise
  `  
- The outer except in run_daemon still catches any unhandled error and sends to channel

## Dependencies

depends_on: [266, 269]
