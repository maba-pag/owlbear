---
id: 123
title: Channel-based ask_user tool — agent asks, user answers
status: archived
priority: needed
created: 2026-02-27T14:54:50.1024749+01:00
updated: 2026-02-28T23:52:48.7371628+01:00
started: 2026-02-27T16:39:13.5515586+01:00
completed: 2026-02-28T23:52:48.7371628+01:00
tags:
    - phase-7
    - tools
    - agent
depends_on:
    - 122
    - 150
class: standard
---

Implement the human-in-the-loop mechanism. Uses the active ChannelPlugin for I/O. See docs/ask-user-tool-research.md.

## AC
- [ ] File: src/owlbear/tools/ask_user.py (~80 LOC)
- [ ] Class: AskUserToolset(FunctionToolset) — follows FileToolset/TerminalToolset/BrowserToolset pattern
- [ ] Constructor: channel: ChannelPlugin, timeout_seconds: float = 120.0, max_retries: int = 3, timeout_action: TimeoutAction = TimeoutAction.ABORT, default_response: str = '(no response)'
- [ ] Enum: TimeoutAction(StrEnum) with ABORT and SKIP — in same module
- [ ] Exception: AskUserTimeoutError(TimeoutError) — in same module
- [ ] Tool: ask_user(question: str, options: list[str] | None = None) -> str — registered via add_function()
- [ ] Prompt formatting: numbered list '[1] opt\n[2] opt\nChoose [1-N]:' when options provided; bare question otherwise
- [ ] Option validation: accept index ('1') or text (case-insensitive .lower() match), re-ask on invalid up to max_retries
- [ ] After max_retries exhausted: ABORT raises AskUserTimeoutError, SKIP returns default_response
- [ ] Timeout: wrap channel.receive() in asyncio.wait_for(timeout=timeout_seconds)
- [ ] On timeout: ABORT raises AskUserTimeoutError, SKIP returns default_response
- [ ] Wire into bearclaw chat: add AskUserToolset(channel) to toolsets list in _chat_async (src/bearclaw/cli.py)
- [ ] All tests from #150 pass
- [ ] ruff clean

## Architecture
- Follows Option A from research: single FunctionToolset subclass, constructor injection of channel
- Channel decoupled from agent — toolset created alongside other toolsets, not inside OwlBearAgent
- No deps_type change (YAGNI — OwlBearDeps is a P8 concern)
