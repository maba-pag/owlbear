# HeartbeatRunner for Proactive Agent Autonomy

> **Owning task:** #616 — Implement HeartbeatRunner for proactive agent autonomy
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear's daemon is purely reactive — it only works when a user sends a message. Task #616 proposes a HeartbeatRunner: an asyncio background task that periodically wakes the agent with a workspace checklist (HEARTBEAT.md), enabling proactive behavior like checking for stale tasks, running pending reviews, or updating knowledge sources. Questions: Is a heartbeat the right abstraction? How should it integrate with the daemon? What are the timezone, testing, and concurrency considerations?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| OpenClaw Heartbeat docs | <https://docs.openclaw.ai/gateway/heartbeat> | .90 |
| OpenClaw skills research (OwlBear) | docs/research/openclaw-skills.md S3a | .90 |
| OpenClaw ecosystem research (OwlBear) | docs/research/openclaw-ecosystem.md S3a | .90 |
| Python asyncio.TaskGroup docs | <https://docs.python.org/3.12/library/asyncio-task.html#task-groups> | .85 |
| APScheduler user guide | <https://apscheduler.readthedocs.io/en/latest/userguide.html> | .70 |
| Poll-dispatch-reconcile research (OwlBear) | docs/research/poll-dispatch-reconcile.md | .85 |
| OwlBear daemon.py (current) | src/owlbear/daemon.py | .95 |
| OwlBear config.py (current) | src/owlbear/config.py | .95 |

## 3. Analysis

### 3a. Is a Heartbeat the Right Abstraction?

| Criterion | Heartbeat (.90) | Cron/APScheduler (.65) | Poll loop extension (.50) |
|-----------|-----------------|----------------------|--------------------------|
| Complexity | ~80 LOC, single class | New dependency (APScheduler) | Adds to already-complex #614 |
| Separation of concerns | Own module, own config | Scheduler framework overhead | Entangled with poll-dispatch |
| Self-scheduling | Agent edits HEARTBEAT.md | Requires job store | Not applicable |
| Idle suppression | `HEARTBEAT_OK` contract | Must implement manually | Must implement manually |
| KISS | ✅ Simple async loop | ❌ Full scheduler framework | ❌ Overloads daemon loop |
| YAGNI | ✅ Only what we need | ❌ 90% of APScheduler unused | ✅ But couples concerns |
| Testability | Mock sleep + file I/O | Mock scheduler | Hard to isolate |

**Verdict (.90):** Heartbeat is the right abstraction. APScheduler is massive overkill — we need a single periodic timer, not a job store + executor + trigger framework. Extending the poll loop (#614) would couple proactive wakeups with autonomous task dispatch, violating separation of concerns.

### 3b. Integration with Daemon — Standalone vs TaskGroup

| Criterion | Standalone `asyncio.create_task` (.75) | TaskGroup sibling (#614 pattern) (.85) |
|-----------|---------------------------------------|---------------------------------------|
| Shutdown propagation | Manual: must cancel + await | Automatic: TaskGroup cancels children |
| Error isolation | Unhandled exception kills task silently | TaskGroup surfaces exceptions |
| Alignment with #614 | Different pattern from poll_loop | Same pattern — channel_loop + poll_loop + heartbeat |
| Complexity | Simpler for standalone daemon | Needs #614's TaskGroup extraction first |
| Dependency on #614 | None | Soft — can use same pattern independently |

**Recommendation (.85):** Use `asyncio.create_task` for now (no #614 dependency). When #614 lands and refactors `run_daemon()` into a TaskGroup, the heartbeat becomes a third sibling coroutine. The HeartbeatRunner class API is the same either way — only the launch site changes.

### 3c. HEARTBEAT.md Format and Response Contract

| Aspect | OpenClaw pattern | Recommended for OwlBear |
|--------|-----------------|------------------------|
| File location | Workspace root | Workspace root (HEARTBEAT.md) |
| Content | Free-form checklist | Markdown checklist — items the agent should check |
| Missing file | Skip tick, log warning | Same — no file = no action (not an error) |
| Response parsing | Substring match `HEARTBEAT_OK` | Same — case-insensitive substring in agent response |
| Agent edits file | Yes — self-scheduling | Yes — agent can add/remove checklist items |
| Channel output | Suppressed on OK | Suppressed on OK, sent to channel otherwise |

**Key design decision:** When `HEARTBEAT_OK` is NOT in the response, the heartbeat should send the response to the channel so the user sees proactive findings. This requires the HeartbeatRunner to hold a channel reference.

### 3d. Active Hours and Timezone

| Option | Pros | Cons | Confidence |
|--------|------|------|------------|
| A. UTC-only tuple `(8, 22)` | Simple, no tz dependency | User must mentally convert | .70 |
| B. Local time via `datetime.now().hour` | Intuitive for single-user | Breaks on DST transitions | .65 |
| C. IANA timezone string in config | Correct, explicit | Adds `zoneinfo` import | .80 |

**Recommendation (.80):** Option A (UTC) for v1 — KISS. The AC already specifies UTC. Add IANA timezone support later only if user requests it. A single-user laptop daemon with UTC is acceptable.

**Edge case — wrap-around hours:** `active_hours: (22, 6)` means "10 PM to 6 AM". Implementation must handle `start > end` as overnight window.

### 3e. Testing Strategy

| Test case | Approach | Notes |
|-----------|----------|-------|
| Timer tick fires | Patch `asyncio.sleep`, assert `agent.turn()` called | Verify sleep duration = interval |
| HEARTBEAT_OK suppression | Mock agent returning "HEARTBEAT_OK", assert `channel.send()` NOT called | Core contract test |
| Non-OK response | Mock agent returning findings, assert `channel.send()` called | Proactive output delivery |
| Active hours skip | Set current UTC hour outside window, assert `agent.turn()` NOT called | Patch `datetime.now(UTC)` |
| Active hours wrap-around | Set `active_hours: (22, 6)`, test midnight hour | `start > end` edge case |
| Missing HEARTBEAT.md | Remove file, assert tick logged warning, no crash | Graceful degradation |
| Shutdown mid-sleep | Set `shutdown_event` during sleep, assert clean exit | `asyncio.wait_for` or event check |
| Exception in agent.turn() | Mock agent raising, assert logged + continues | Runner must not crash |

## 4. Recommendation (.85 confidence)

Implement HeartbeatRunner as a standalone class in `src/owlbear/heartbeat.py` (~80 LOC):

- `__init__(agent, channel, interval_seconds, active_hours, shutdown_event, heartbeat_path)`
- `async run()`: infinite loop — check active hours → read HEARTBEAT.md → `agent.turn()` → parse response → optionally `channel.send()` → sleep
- Config: `heartbeat_enabled` (bool, default False), `heartbeat_interval` (int, default 1800), `heartbeat_active_hours` (tuple, default (8, 22))
- Launch: `asyncio.create_task(runner.run())` in `run_daemon()`, guarded by `heartbeat_enabled`
- Missing HEARTBEAT.md: skip tick, log at DEBUG
- Exception handling: log + continue (never crash the runner)

**Risks:**

1. Token waste on empty heartbeats — mitigated by `HEARTBEAT_OK` suppression + active hours window
2. Concurrent access if heartbeat runs during user turn — low risk, PydanticAI Agent is not inherently thread-safe but asyncio is single-threaded so turns are sequential
3. #614 refactor changes launch site — low impact, runner API is unchanged

**AC refinements suggested:**

- Add `heartbeat_enabled` (bool) config field — heartbeat should be opt-in
- Add `channel` parameter to HeartbeatRunner — needed to deliver proactive findings
- Add `heartbeat_path` parameter (default: workspace `HEARTBEAT.md`) — testability
- Handle missing HEARTBEAT.md gracefully (skip, don't crash)
- Handle overnight `active_hours` wrap-around (start > end)
- Handle exceptions in `agent.turn()` — log and continue

## 5. Follow-up Tasks

Commands below for user review — **do not execute**.

```powershell
# Move #616 from ideation to backlog (research complete)
kanban\kanban-md.exe move 616 backlog

# Update AC with research findings
kanban\kanban-md.exe edit 616 --body "Implement HeartbeatRunner: asyncio task alongside daemon receive-loop. Configurable interval (default 30m) and active-hours window. Reads workspace HEARTBEAT.md as prompt context. HEARTBEAT_OK in response suppresses further action.

Integration: starts as asyncio.create_task in run_daemon(), guarded by heartbeat_enabled. When #614 lands, becomes a TaskGroup sibling.

See docs/research/heartbeat-runner.md for full analysis.

AC:
- [ ] HeartbeatRunner class in src/owlbear/heartbeat.py
- [ ] __init__(agent, channel, interval_seconds, active_hours, shutdown_event, heartbeat_path)
- [ ] async run() loop: check active_hours -> read HEARTBEAT.md -> agent.turn(content) -> check HEARTBEAT_OK
- [ ] active_hours: tuple[int, int] (start_hour, end_hour UTC) -- handles overnight wrap (start > end)
- [ ] HEARTBEAT_OK substring suppresses channel.send(); non-OK response sent to channel
- [ ] Missing HEARTBEAT.md: skip tick, log at DEBUG (no crash)
- [ ] Exception in agent.turn(): log warning, continue loop (never crash runner)
- [ ] Config fields in OwlBearSettings: heartbeat_enabled (bool, default False), heartbeat_interval (int, default 1800), heartbeat_active_hours (tuple, default (8, 22))
- [ ] run_daemon() starts HeartbeatRunner via asyncio.create_task when heartbeat_enabled=True
- [ ] Respects shutdown_event for clean exit (checked after each sleep)
- [ ] Tests: timer tick, HEARTBEAT_OK suppression, non-OK channel delivery, active-hours skip, overnight wrap, missing file, shutdown mid-sleep, exception resilience"
```
