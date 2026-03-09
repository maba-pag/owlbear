---
id: 650
title: Tests for httpx.AsyncClient cleanup in Copilot provider
status: done
priority: important
created: 2026-03-07T23:10:37.802564+01:00
updated: 2026-03-08T00:06:40.1069119+01:00
started: 2026-03-08T00:06:40.1069119+01:00
completed: 2026-03-08T00:06:40.1069119+01:00
tags:
    - test
    - audit
    - resilience
    - auth
class: standard
---

Test task for #514. Tests must be written before implementation (TDD).

## AC
- Test that bootstrap registers an async cleanup callable for the OpenAI client
- Test that the cleanup loop in cli.py awaits async callables (currently sync-only cb() call)
- Test that _chat_async runs cleanup on exit (currently missing)
- Test that daemon auth refresh (_handle_classified_error AUTH branch) closes the old OpenAI client before replacing
- All new tests initially fail (red phase), then pass after #514 implementation

## Scope
- tests/test_bootstrap.py  cleanup registration assertion
- tests/test_cli.py or new test file  cleanup loop awaits async
- tests/test_daemon.py  auth refresh closes old client

## Notes
Follow existing test patterns in test_bootstrap.py and test_providers_copilot.py.
