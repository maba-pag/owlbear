---
id: 270
title: Update bearclaw chat to use bootstrap() - shared wiring
status: archived
priority: needed
created: 2026-02-28T14:20:59.4324713+01:00
updated: 2026-02-28T23:54:34.18269+01:00
started: 2026-02-28T15:55:13.4325089+01:00
completed: 2026-02-28T23:54:34.18269+01:00
tags:
    - phase-8
    - cli
    - agent
depends_on:
    - 267
class: standard
---

## Context

Replace manual `_chat_async` wiring with shared `bootstrap()`. Eliminates duplicated assembly code.
See docs/research/bootstrap-assembly.md S3.3.

## Acceptance Criteria

- [ ] `_chat_async()` calls `await bootstrap(settings, channel_name='cli', workspace_root=workspace_root)` instead of manual hook/toolset wiring
- [ ] `--session` naming preserved: `_build_chat_session()` resolves name and creates `SessionStore`; `result.agent.session` overridden with user-specified store post-bootstrap
- [ ] Session history loaded via `store.load()` before entering chat loop (current behavior preserved)
- [ ] `--model` override preserved: if `--model` provided, override model on `result.agent` post-bootstrap
- [ ] Banner still displays model name and session name (derive model name from `result.agent` or local variable)
- [ ] `_chat_loop()` unchanged — still receives `(agent, channel)`; no signature changes
- [ ] ~40 lines of manual wiring removed from `_chat_async()`: individual HookRegistry setup, toolset list construction, GitHub remote detection, conditional GitHubToolset
- [ ] Chat tests updated: mock `bootstrap()` return value (`BootstrapResult` with mock agent/channel) instead of mocking individual constructors (`OwlBearSettings`, `SessionStore`, `OwlBearAgent`, toolset classes)
- [ ] Dead imports removed from cli.py if no longer used elsewhere: `HookEvent`, `CommandSafetyGuard`, individual toolset classes (verify each — some may still be used by `run_cmd`)
- [ ] TDD: update test mocks before changing implementation

## Architecture Notes

- `_build_chat_session()` stays — it has chat-specific session naming logic (auto-generated timestamps, `--session` flag)
- `_detect_github_remote()` stays — still used if other CLI paths need it, or removed if only chat used it (builder verifies)
- `_read_multiline()` and `_chat_loop()` untouched — they operate on agent + channel, independent of wiring
- After bootstrap: `result.agent.session = store` overrides the default session that bootstrap creates
- Import pattern: `from owlbear.bootstrap import BootstrapResult, bootstrap` added to cli.py

## Dependencies

depends_on: [267]
