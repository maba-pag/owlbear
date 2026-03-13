---
id: 150
title: Test AskUserToolset — free-text, options, timeout, retries
status: archived
priority: needed
created: 2026-02-27T16:45:33.9413947+01:00
updated: 2026-02-28T23:53:09.0995348+01:00
started: 2026-02-27T16:45:40.4350804+01:00
completed: 2026-02-28T23:53:09.0995348+01:00
tags:
    - phase-7
    - tools
    - test
class: standard
---

TDD test task for #123 (AskUserToolset).

## AC
- [ ] File: tests/test_ask_user.py
- [ ] Test: ask_user free-text question — sends formatted prompt via channel.send(), returns channel.receive() response
- [ ] Test: ask_user with options — formats numbered list prompt: ''[1] opt1\n[2] opt2\nChoose [1-2]:''
- [ ] Test: ask_user with options — accepts index input (''1'') and returns corresponding option text
- [ ] Test: ask_user with options — accepts text input (case-insensitive match)
- [ ] Test: ask_user with options — re-asks on invalid input (up to max_retries=3)
- [ ] Test: ask_user options exhausts retries + TimeoutAction.ABORT — raises AskUserTimeoutError
- [ ] Test: ask_user options exhausts retries + TimeoutAction.SKIP — returns default_response
- [ ] Test: ask_user timeout + TimeoutAction.ABORT — raises AskUserTimeoutError
- [ ] Test: ask_user timeout + TimeoutAction.SKIP — returns default_response
- [ ] All tests use AsyncMock for ChannelPlugin.send() and .receive()
- [ ] ruff clean

## Architecture
- Follow existing test patterns in tests/test_terminal_tools.py (async tests, mock injection)
- AskUserToolset constructor: channel, timeout_seconds=120.0, max_retries=3, timeout_action=TimeoutAction.ABORT, default_response=''(no response)''
- Tool signature: ask_user(question: str, options: list[str] | None = None) -> str
- See docs/research/ask-user-tool.md for full design
