---
id: 122
title: bearclaw chat — interactive CLI REPL
status: archived
priority: critical
created: 2026-02-27T14:54:37.0573892+01:00
updated: 2026-02-28T23:52:48.200072+01:00
started: 2026-02-27T15:37:56.6974334+01:00
completed: 2026-02-28T23:52:48.200072+01:00
tags:
    - phase-7
    - cli
    - agent
depends_on:
    - 149
class: standard
---

The fastest path to a working OwlBear: an interactive terminal session where the user types, OwlBear responds. Uses CLIChannel + OwlBearAgent.

See `docs/research/chat-repl.md` for detailed findings.

## Research Summary

- **Loop pattern:** Loop outside agent (receive -> turn -> send), per daemon-bootstrap-research
- **Multi-line input:** !multi/!end markers (simonw/llm pattern, no new deps)
- **Signal handling:** KeyboardInterrupt (Ctrl+C) + EOF (Ctrl+D) -> save session + exit
- **Session naming:** --session NAME -> ~/.owlbear/sessions/{NAME}.jsonl; default auto-generated
- **Cannot use Agent.to_cli()** — bypasses SessionStore, HookRegistry, UsageTracker

## AC

### CLI command

- [ ] New Typer command: `bearclaw chat [--model MODEL] [--session NAME] [--workspace PATH]`
- [ ] `--model` defaults to `OwlBearSettings().default_model`
- [ ] `--session` names the session file; if omitted, generate `chat-{YYYYMMDD-HHMMSS}`
- [ ] `--workspace` defaults to cwd (`"."`); sets workspace_root for toolsets
- [ ] Bridge: `asyncio.run(_chat_async(...))` following existing CLI pattern (see `auth login`, `browser status`)

### Agent wiring

- [ ] Creates `OwlBearAgent(model=..., session=..., hooks=..., channel=..., toolsets=[...])`
- [ ] Toolsets: pass `[SkillRegistry(skills_dir)]` at minimum; FileToolset/TerminalToolset added later when #120/#121 complete (do NOT block on them)
- [ ] Uses `CLIChannel` for I/O (`send()` for agent responses, `receive(prompt="> ")` for user input)
- [ ] `SessionStore(path)` for JSONL message persistence; load previous messages on startup
- [ ] `HookRegistry` with at least `CommandSafetyGuard` registered

### REPL loop

- [ ] Print startup banner: model name + session path + help text (`!multi`, `exit`)
- [ ] Loop: `receive -> turn -> send` (daemon-bootstrap-research Pattern A)
- [ ] Multi-line input: `!multi` starts accumulation, `!end` submits joined text
- [ ] Exit keywords: `exit`, `quit` -> save session, print goodbye, exit 0
- [ ] `KeyboardInterrupt` (Ctrl+C) -> save session, print goodbye, exit 0
- [ ] `CLIChannel.receive()` returns `None` on EOF (Ctrl+D) -> same graceful exit

### Error handling

- [ ] Auth failure (no Copilot token): print error message, `sys.exit(1)`
- [ ] Agent error during turn: print error, continue loop (don't crash)

### Tests (TDD: write tests first, see them fail, then implement)

- [ ] New file: `tests/test_cli_chat.py`
- [ ] Test startup prints banner with model and session path
- [ ] Test message round-trip: user input -> `agent.turn()` called -> response printed (mock agent)
- [ ] Test multi-line input: `!multi` + lines + `!end` -> single concatenated prompt
- [ ] Test exit keywords (`exit`, `quit`) trigger graceful shutdown
- [ ] Test `KeyboardInterrupt` triggers graceful shutdown
- [ ] Test EOF (`receive` returns `None`) triggers graceful shutdown
- [ ] Test session loaded on startup (mock SessionStore)
- [ ] ruff clean

## Dependencies

- **Hard dependency:** #149 (Add toolsets parameter to OwlBearAgent) — must complete first
- **Soft dependency:** #120 (FileToolset), #121 (TerminalToolset) — wire later as follow-up; chat works without them
