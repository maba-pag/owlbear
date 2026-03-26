---
id: 269
title: Update bearclaw run to use bootstrap() - full wiring
status: archived
priority: needed
created: 2026-02-28T14:20:51.4401328+01:00
updated: 2026-02-28T23:54:33.5260009+01:00
started: 2026-02-28T15:55:12.9300221+01:00
completed: 2026-02-28T23:54:33.5260009+01:00
tags:
    - phase-8
    - cli
    - agent
depends_on:
    - 267
class: standard
---

## Context

Replace bare OwlBearAgent in `bearclaw run` with fully-wired `bootstrap()`. Eliminates the 10%% wiring problem.
See docs/research/bootstrap-assembly.md S3.3.

## Acceptance Criteria

- [ ] `run_cmd()` calls `await bootstrap(settings, channel_name=channel, workspace_root=Path.cwd())` instead of manual channel/agent construction
- [ ] `--model` override preserved: if `--model` provided, override model on `result.agent` post-bootstrap (via `update_model()` or bootstrap param)
- [ ] MCP lifecycle managed in `run_cmd()`: if `result.mcp_registry`, call `start_all()` before `run_daemon()` and `stop_all()` in finally block
- [ ] `result.cleanup` callbacks invoked in finally block (browser teardown, etc.)
- [ ] `run_daemon()` receives `settings: OwlBearSettings` parameter for downstream token refresh (#271)
- [ ] `run_cmd()` still owns PidFile and `setup_logging()` — not bootstrap's concern
- [ ] Manual channel creation, bare `SessionStore`, bare `OwlBearAgent(model=model_name, session=store)` all removed from `run_cmd()`; replaced by single `bootstrap()` call
- [ ] Dead manual-wiring imports removed from run_cmd path if no longer used elsewhere in cli.py
- [ ] Existing daemon tests pass; run_cmd integration test added (mock `bootstrap()`, verify PidFile + lifecycle wiring)
- [ ] TDD: write/update tests before changing implementation

## Architecture Notes

- `bootstrap()` handles: hooks (7 hooks), channel dispatch, all toolsets (wrapped in HookedToolset), MCP registry, agent registry, Copilot model, session, context, tracker
- `run_cmd()` retains: PidFile, setup_logging, `--model` override, `--channel` dispatch (passed as `channel_name`)
- `run_daemon()` signature gains `settings` param — needed by #271 for `create_copilot_model()` during token refresh
- Pattern: `result = await bootstrap(...); run_daemon(channel=result.channel, agent=result.agent, settings=settings, config_dir=...)`; finally cleanup

## Dependencies

depends_on: [267]
