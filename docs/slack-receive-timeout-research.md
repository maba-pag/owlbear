# Slack Receive Timeout vs Daemon Shutdown

> **Owning task:** #513 — Review Slack receive timeout behavior for daemon idle
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

`SlackChannel.receive()` returns `None` after a 30s timeout (no message on queue). `daemon.py:run_daemon()` interprets `None` from any channel's `receive()` as a shutdown signal and exits. This is correct for CLI (where `None` = stdin EOF) but causes the Slack daemon to exit after 30s of idle.

**Question:** How should we distinguish "no message yet" from "shutdown requested" so the daemon stays alive on Slack idle?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Slack Socket Mode docs | <https://docs.slack.dev/apis/events-api/using-socket-mode> | .90 — Official spec for idle behavior, ping, disconnect, reconnect |
| 2 | slack_sdk SocketModeClient (aiohttp) | <https://github.com/slackapi/python-slack-sdk/blob/main/slack_sdk/socket_mode/aiohttp/__init__.py> | .95 — The actual WebSocket client we use; shows ping-pong, auto-reconnect |
| 3 | Bolt for Python AsyncBaseSocketModeHandler | <https://github.com/slackapi/bolt-python/blob/main/slack_bolt/adapter/socket_mode/async_base_handler.py> | .80 — Official framework pattern; uses event listeners + `asyncio.sleep(inf)` |
| 4 | OwlBear codebase (slack.py, daemon.py, cli.py, base.py) | (local) | 1.0 — Code under investigation |

## 3. Findings

### 3.1 Slack Socket Mode Does NOT Disconnect on Idle

The SDK's `SocketModeClient` maintains the WebSocket during idle via:

- **Ping-pong** every `ping_interval` seconds (default 10s) — SDK sends pings, checks for pong response
- **Auto-reconnect** on stale/closed sessions — `monitor_current_session()` background task
- **Connection refresh** every ~3600s — SDK handles transparently via `connect_to_new_endpoint()`

**Conclusion:** Slack idle is normal and indefinite. The WebSocket stays alive. No events arrive but the connection is healthy. Source: [1], [2].

### 3.2 Bolt Framework Pattern

Bolt's `AsyncBaseSocketModeHandler.start_async()` does `await asyncio.sleep(float("inf"))` after connecting. It never polls `receive()` — events are pushed to registered listeners by the SDK's internal `receive_messages()` loop. Source: [3].

OwlBear's SlackChannel bridges this push model to a pull model (listener → asyncio.Queue → `receive()`). The timeout-based `receive()` is our invention, not Slack's.

### 3.3 Bug Root Cause

| Channel | `receive()` returns `None` when... | Daemon interpretation | Correct? |
|---------|------------------------------------|-----------------------|----------|
| CLI | stdin EOF (process closing) | Shutdown | Yes |
| Slack | 30s timeout (no messages) | Shutdown | **No** |
| Slack | `disconnect()` queues sentinel `None` | Shutdown | Yes |

The daemon conflates two meanings of `None`: "idle timeout" and "channel closed."

### 3.4 Shutdown Path Analysis

The daemon has 3 shutdown triggers:

1. **Signal (SIGINT/SIGTERM)** → `_make_signal_handler` sets `shutdown_event` via `loop.call_soon_threadsafe`
2. **Sentinel file** → `owlbear.stop` checked each loop iteration
3. **Channel returns `None`** → `message is None → break`

Trigger 3 is the only one that fires during Slack idle. Triggers 1-2 are checked **between** `receive()` calls, so they only work when `receive()` returns (currently after 30s timeout). This is acceptable latency.

## 4. Implementation Options

| Approach | Description | Daemon change | Protocol change | Shutdown delay | KISS |
|----------|-------------|---------------|-----------------|----------------|------|
| **A. Loop in Slack receive()** | Timeout → `continue` internally; return `None` only on disconnect sentinel | None | None | ≤30s on SIGINT | High |
| **B. Daemon continues on None** | `if message is None: continue` instead of `break` | Yes | None | None | High — but CLI busy-loops on EOF |
| **C. Sentinel object** | New `IDLE` return value; `None` = shutdown only | Yes | Yes (return type) | None | Medium |
| **D. Integrate shutdown_event** | `asyncio.wait([receive_task, shutdown_wait])` | Yes | None | None | Low |

### Approach A Detail (Recommended)

```python
# SlackChannel.receive() — change 2 lines
async def receive(self, *, prompt: str | None = None) -> str | None:
    while True:
        try:
            return await asyncio.wait_for(
                self._message_queue.get(),
                timeout=self._receive_timeout,
            )
        except TimeoutError:
            continue  # Idle timeout — keep waiting
```

- **Idle:** Loops internally, never returns `None` to daemon
- **Disconnect:** `disconnect()` puts `None` on queue → `wait_for` returns `None` → daemon breaks correctly
- **SIGINT:** `shutdown_event.set()` scheduled, but `receive()` blocked. After ≤30s timeout, inner loop continues. Daemon's `while not shutdown_event.is_set()` check doesn't run until `receive()` returns (via disconnect sentinel). **Worst case: 30s delay** — acceptable for a daemon.
- **Optimization (follow-up):** Signal handler could also call `channel.disconnect()` to push sentinel, eliminating the delay.

## 5. Recommendation (.90 confidence)

**Approach A** — Loop in `SlackChannel.receive()`. Rationale:

- **Zero protocol/daemon changes** — fix is entirely within the Slack channel adapter
- **2-line diff** — replace `return None` in `except TimeoutError` with `continue`
- **Preserves timeout utility** — the 30s timeout still ensures `asyncio.wait_for` is cancellable and lets the SDK process other async tasks
- **CLI unaffected** — `CLIChannel.receive()` is unchanged; it returns `None` on EOF as before
- **KISS-aligned** — simplest fix that solves the stated problem

**Risk:** ≤30s shutdown delay on SIGINT when using Slack channel. Mitigated by follow-up task to wire `channel.disconnect()` into the signal handler or daemon cleanup.

## 6. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Fix: SlackChannel.receive() loop on idle timeout instead of returning None" --status backlog --priority needed --tags "resilience,channels,phase-13" --body "SlackChannel.receive() returns None on 30s timeout, causing daemon premature exit. Change except TimeoutError branch from 'return None' to 'continue' so receive() only returns None on disconnect sentinel. See docs/slack-receive-timeout-research.md §4-5. AC: (1) SlackChannel.receive() loops on timeout, never returns None for idle. (2) SlackChannel.receive() returns None when disconnect sentinel is queued. (3) Daemon stays alive during Slack idle periods. (4) Existing tests updated. (5) New test: receive loops past timeout until message arrives."

kanban\kanban-md.exe create "Fix: Daemon cleanup should call channel.disconnect()" --status backlog --priority important --tags "resilience,channels,phase-13" --body "daemon.py run_daemon() finally block does not call channel.disconnect(). Slack WebSocket stays open after daemon exits. Also: signal handler should call channel.disconnect() to unblock receive() immediately on SIGINT (eliminates 30s shutdown delay). See docs/slack-receive-timeout-research.md §4. AC: (1) Daemon finally block calls channel.disconnect() if method exists. (2) Signal handler triggers channel disconnect for immediate unblock. (3) Shutdown delay on SIGINT reduced from 30s to <1s."
```
