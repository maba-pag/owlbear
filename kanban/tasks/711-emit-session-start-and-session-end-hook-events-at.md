---
id: 711
title: Emit SESSION_START and SESSION_END hook events at session boundaries
status: backlog
priority: needed
created: 2026-03-09T15:27:59.494595+01:00
updated: 2026-03-09T19:17:39.5208205+01:00
started: 2026-03-09T18:11:48.8691043+01:00
tags:
    - scope:core
    - hooks
depends_on:
    - 713
class: standard
---

Emit SESSION_START and SESSION_END lifecycle events from `daemon.py:run_daemon()` so existing hook consumers start receiving data.

depends_on: #713

## Acceptance Criteria

- [ ] `run_daemon()` emits `HookEvent.SESSION_START` with `{session_id: str(agent.session.path), workspace_root: str(workspace_root)}` immediately after `DAEMON_STARTUP` emission
- [ ] `run_daemon()` emits `HookEvent.SESSION_END` with `{session_id: str(agent.session.path), messages: <loaded>}` in the `finally` block, before signal handler restoration
- [ ] `workspace_root` is available in `run_daemon()`  either add a `workspace_root: Path` parameter (preferred, called from cli.py which already knows it) or derive from `agent.context._root` via a public accessor
- [ ] `SESSION_END` payload: `messages` loaded via `agent.session.load()` wrapped in try/except  falls back to `[]` on any error (session file may not exist)
- [ ] `ContextInjectionHook` fires on SESSION_START and populates `data[context]` (integration verified by test task #713)
- [ ] `TestVerificationHook` fires on SESSION_END and populates `data[test_results]` (integration verified by test task #713)
- [ ] No changes to `core/hooks.py`, `core/context_hook.py`, or `core/test_hook.py`  consumers are already wired
- [ ] Emission ordering: DAEMON_STARTUP  SESSION_START  (loops)  SESSION_END  signal restore

## Architecture Notes

- **Pattern:** follows existing `DAEMON_STARTUP` emit at daemon.py L824. SESSION_START goes on the line after, SESSION_END goes in the `finally` block.
- **workspace_root access:** `run_daemon()` currently lacks this parameter. Add `workspace_root: Path | None = None` to the signature. Both call sites in `bearclaw/cli.py` (`_run_daemon_cmd` and `_chat_cmd`) already resolve workspace_root  pass it through. If None, fall back to `Path.cwd()`.
- **Error isolation:** `HookRegistry.emit()` wraps each handler in try/except (hooks.py L80+). No additional error handling needed at the emission site, except for session.load() in SESSION_END payload construction.
- **Module layering:** daemon.py is assembly layer  importing from core/hooks is valid (top-down).
- See docs/research/session-hook-emission-research.md for full analysis.

[[2026-03-09]] Mon 19:17
## Architecture Review
**Verdict:** REFINE (AC tightened, test task created)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| daemon.py or agent.py emits SESSION_START | Imprecise  pinned to daemon.py:run_daemon() | Rewritten |
| daemon.py or agent.py emits SESSION_END | Same  pinned to finally block in run_daemon() | Rewritten |
| ContextInjectionHook fires | Verifiable integration criterion | Kept, linked to #713 |
| Existing tests updated | Vague  no test scenarios specified | Replaced with #713 test task |
| No behavioral change to consumers | Valid negative constraint | Kept |
| (missing) workspace_root access | run_daemon() lacks this param  critical gap | Added AC + architecture note |
| (missing) session.load() error handling | SESSION_END finally may fail on missing session | Added AC for try/except fallback |
| (missing) emission ordering | Not specified | Added explicit ordering AC |

### Architecture Notes
- Pattern: follows DAEMON_STARTUP emit in daemon.py L824. Minimal diff (2 emit calls + 1 new param).
- workspace_root: not currently available in run_daemon(). Add Path parameter; both cli.py call sites already know it.
- Module layering: daemon.py (assembly) -> core/hooks (valid top-down).
- Error isolation: HookRegistry.emit() wraps handlers in try/except. Only session.load() needs guarding.
- Single domain: daemon lifecycle only.

### Changes Made
- Rewrote AC body with 8 precise, verifiable criteria
- Created test task #713 (TDD RED)
- Added depends_on: #713 to #711
- Added depends_on: #711 to #622 (downstream consumer)

### Dependencies
- Added: #711 depends_on #713 (test task  TDD compliance)
- Verified: #622 depends_on #711 (SessionMemoryHook needs these events)
