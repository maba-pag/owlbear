# Daemon Entry Point Research — bearclaw run / stop / status

> **Owning task:** #124 — bearclaw run — background daemon entry point
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

Task #124 requires three CLI commands (`bearclaw run`, `stop`, `status`) and daemon lifecycle management: PID file, structured logging, signal handling, and graceful shutdown. The daemon-bootstrap-research (docs/research/daemon-bootstrap.md) covers wiring agents/channels/toolsets. This research focuses on the **missing pieces**: daemon process management, cross-platform signal handling, and CLI commands.

Key question: How do we implement graceful shutdown on Windows where `loop.add_signal_handler()` is Unix-only and `os.kill(pid, SIGTERM)` calls `TerminateProcess` (instant kill, no cleanup)?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Python signal module docs | <https://docs.python.org/3/library/signal.html> | .95 | Windows signal support: SIGINT, SIGTERM, SIGBREAK; `os.kill` → `TerminateProcess` |
| Python asyncio event loop docs | <https://docs.python.org/3/library/asyncio-eventloop.html> | .90 | `add_signal_handler()` Unix-only; signal examples |
| Python logging.handlers docs | <https://docs.python.org/3/library/logging.handlers.html> | .85 | RotatingFileHandler for bounded log files |
| uvicorn/main.py | <https://github.com/encode/uvicorn/blob/master/uvicorn/main.py> | .80 | `run()` pattern: `asyncio.run(server.run())`, KeyboardInterrupt catch |
| aiohttp/web.py | <https://github.com/aio-libs/aiohttp/blob/master/aiohttp/web.py> | .75 | `run_app()`: signal handling, shutdown callback, cleanup |
| OwlBear browser PID pattern | `src/bearclaw/cli.py` lines 371-389 | .90 | Existing PID file write/read/delete for browser start/stop |
| OwlBear _chat_loop | `src/bearclaw/cli.py` lines 540-570 | .95 | Existing receive→turn→send loop with error handling |
| OwlBear daemon-bootstrap-research | `docs/research/daemon-bootstrap.md` | .95 | Daemon loop, model bridge, channel integration (§3.3–3.5) |

## 3. Analysis

### 3.1 Signal Handling — Cross-Platform Shutdown

| Mechanism | Windows | Unix | Graceful? | Complexity |
|-----------|---------|------|-----------|------------|
| `signal.signal(SIGINT, handler)` | Yes (Ctrl+C) | Yes | Yes | Low |
| `signal.signal(SIGTERM, handler)` | Yes (in-process only) | Yes | Yes | Low |
| `signal.signal(SIGBREAK, handler)` | Yes | No | Yes | Low |
| `loop.add_signal_handler()` | **No** (raises NotImplementedError) | Yes | Yes | Low |
| `os.kill(pid, SIGTERM)` | Calls `TerminateProcess` — **instant kill** | Sends SIGTERM | **No on Win** | Minimal |
| `os.kill(pid, CTRL_BREAK_EVENT)` | Only same console group | N/A | Partial | Low |
| Sentinel file (`.stop`) | Yes | Yes | Yes | Low |

**Critical finding:** On Windows, there is no cross-process graceful shutdown mechanism via signals. `os.kill(pid, SIGTERM)` calls `TerminateProcess` which kills instantly without cleanup. `CTRL_BREAK_EVENT` only works within the same console group.

**Recommendation (.90):** Dual-mechanism shutdown:

1. **In-terminal:** `signal.signal(SIGINT, ...)` + `signal.signal(SIGTERM, ...)` — handles Ctrl+C and in-process SIGTERM
2. **Cross-process:** Sentinel file `config_dir/owlbear.stop` — daemon loop checks for file existence each iteration
3. `bearclaw stop` creates sentinel file, then polls PID file removal (daemon removes it on exit). If daemon doesn't exit within 5s, falls back to `TerminateProcess`.

### 3.2 PID File Management

Existing pattern from `bearclaw browser start/stop` (cli.py:371-389):

```python
pid_file = settings.config_dir / "browser.pid"
pid_file.write_text(str(pid))  # on start
pid = int(pid_file.read_text().strip())  # on stop
pid_file.unlink()  # on stop
```

**Stale PID detection:** A PID file can become stale if the daemon crashes without cleanup. Standard approach: read PID → check if process is alive → if dead, treat as stale.

```python
def _is_process_alive(pid: int) -> bool:
    """Check if process with given PID exists (cross-platform)."""
    try:
        os.kill(pid, 0)  # signal 0 = existence check, no signal sent
        return True
    except OSError, ProcessLookupError:
        return False
```

Note: `os.kill(pid, 0)` works on both Windows and Unix for existence checks.

**Recommendation (.90):** Follow existing browser pattern. Add stale detection. PID file at `config_dir/owlbear.pid`.

| Lifecycle event | Action |
|-----------------|--------|
| `bearclaw run` start | Check for existing PID file → stale check → fail if alive, remove if dead → write new PID |
| Daemon running | PID file exists with current PID |
| Graceful shutdown | Save session, disconnect channels, remove PID file, remove sentinel |
| Crash (no cleanup) | PID file remains → stale → next `run` detects and cleans up |

### 3.3 Structured Logging

| Option | Description | Complexity | KISS |
|--------|-------------|------------|------|
| A. stdlib `logging` + `RotatingFileHandler` | JSON formatter, file rotation | Low | High |
| B. `structlog` | Structured logging library, rich formatting | Medium | Medium |
| C. `loguru` | Drop-in replacement, rotation built-in | Medium | Medium |

No new deps in the tech stack. YAGNI — stdlib logging works fine.

**Recommendation (.85):** stdlib `logging` with `RotatingFileHandler`:

- File: `config_dir/owlbear.log`
- Format: `%(asctime)s %(levelname)s %(name)s %(message)s`
- maxBytes: 5MB, backupCount: 3
- Also log to stderr when running interactively (dual handler)
- ~15 LOC setup function

### 3.4 bearclaw stop — Process Termination

```
bearclaw stop
  1. Read PID from config_dir/owlbear.pid
  2. Create sentinel file config_dir/owlbear.stop
  3. Poll for PID file removal (daemon removes on exit), timeout 5s
  4. If timeout: os.kill(pid, SIGTERM) — force kill on Windows
  5. Clean up PID file and sentinel file if still present
```

### 3.5 bearclaw status — Health Check

| Check | Method | Output |
|-------|--------|--------|
| PID file exists? | `pid_file.exists()` | "Not running" if missing |
| Process alive? | `os.kill(pid, 0)` | "Stale PID file" if dead |
| Process alive | — | "Running (PID {pid})" |

~15 LOC. Matches existing `bearclaw browser status` pattern.

### 3.6 bearclaw run — Entry Point Structure

The `bearclaw run` command needs to:

1. Load settings
2. Validate no daemon already running (PID check)
3. Set up logging (file + stderr)
4. Write PID file
5. Create channel (CLI or Slack based on `--channel` flag)
6. Call `run_daemon()` from daemon-bootstrap-research pattern
7. On exit: cleanup PID file, sentinel file, disconnect channel

**Recommendation (.85):** Structure as:

- `src/owlbear/daemon.py` — `run_daemon()` async loop (~80 LOC), `setup_logging()` (~15 LOC), `PidFile` context manager (~40 LOC)
- `src/bearclaw/cli.py` — `run`, `stop`, `status` commands (~60 LOC total)

Total new code: ~195 LOC. This excludes the DevToolset and model bridge from daemon-bootstrap (separate tasks).

### 3.7 Channel Selection for MVP

For the initial `bearclaw run`, the daemon starts with ONE channel at a time (`--channel cli|slack`). Multi-channel routing is YAGNI until we actually need simultaneous channels.

## 4. Recommendation (.88 confidence)

**Minimal viable daemon with cross-platform graceful shutdown:**

| Deliverable | Location | LOC | Description |
|-------------|----------|-----|-------------|
| Daemon module | `src/owlbear/daemon.py` | ~135 | `run_daemon()`, `setup_logging()`, `PidFile` ctx manager, sentinel-based shutdown |
| CLI commands | `src/bearclaw/cli.py` | ~60 | `run`, `stop`, `status` Typer commands |
| Tests | `tests/test_daemon.py` | ~150 | PID lifecycle, shutdown signal, sentinel, logging setup |

**Key design decisions:**

1. **Sentinel file for cross-process shutdown** — only reliable cross-platform mechanism
2. **`signal.signal()` over `loop.add_signal_handler()`** — cross-platform compatibility
3. **stdlib logging** — no new dependencies (YAGNI)
4. **Single channel per invocation** — `--channel cli|slack`, not multi-channel (YAGNI)
5. **PID file with stale detection** — follows existing browser pattern

**Risks and mitigations:**

| Risk | Severity | Mitigation |
|------|----------|------------|
| Sentinel file not checked fast enough | Low | Daemon loop checks every iteration (~30s max with Slack timeout) |
| PID file left after crash | Low | Stale detection on next `run` invocation |
| Logging fills disk | Low | RotatingFileHandler with 5MB × 3 backups = 15MB max |

## 5. Follow-up Tasks

Implementation should be split into 3 focused tasks (matching AC groups):

1. **Daemon module** — `run_daemon()`, `setup_logging()`, `PidFile`, sentinel shutdown
2. **CLI commands** — `bearclaw run`, `stop`, `status`
3. **Daemon tests** — startup/shutdown cycle, PID lifecycle, sentinel, logging

The daemon-bootstrap-research's DevToolset and model bridge tasks (#125+) are prerequisites listed in that document — they are NOT duplicated here. This task depends on the OwlBearAgent and channels already working (which they do as of #122).
