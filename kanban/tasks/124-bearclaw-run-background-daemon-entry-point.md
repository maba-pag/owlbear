---
id: 124
title: bearclaw run — background daemon entry point
status: archived
priority: needed
created: 2026-02-27T14:55:03.2109768+01:00
updated: 2026-02-28T23:52:49.296776+01:00
started: 2026-02-27T16:40:10.7769684+01:00
completed: 2026-02-28T23:52:49.296776+01:00
tags:
    - phase-7
    - cli
    - daemon
depends_on:
    - 122
    - 151
class: standard
---

Long-running daemon process that listens on a configured channel and dispatches to OwlBearAgent. See docs/daemon-entrypoint-research.md.

## AC
- [ ] File: src/owlbear/daemon.py (~135 LOC)
- [ ] PidFile context manager: writes config_dir/owlbear.pid on enter, removes on exit
- [ ] PidFile stale detection: os.kill(pid, 0) to check liveness, remove stale PID file on next run
- [ ] PidFile conflict: raise RuntimeError if PID file exists and process alive
- [ ] setup_logging(log_file: Path) — stdlib logging with RotatingFileHandler (5MB maxBytes, 3 backupCount) + stderr StreamHandler
- [ ] Log format: %(asctime)s %(levelname)s %(name)s %(message)s
- [ ] run_daemon(channel, model, settings) — async loop: channel.receive() -> agent.turn() -> channel.send()
- [ ] Sentinel-based shutdown: check config_dir/owlbear.stop each iteration, clean up on detection
- [ ] Signal handling: signal.signal(SIGINT, handler) + signal.signal(SIGTERM, handler) set shutdown flag — NOT loop.add_signal_handler() (Windows compat)
- [ ] Single channel per invocation via --channel flag (no multi-channel router — YAGNI)
- [ ] File: src/bearclaw/cli.py additions (~60 LOC)
- [ ] bearclaw run [--channel cli|slack] [--model MODEL]: validate no existing daemon, setup logging, PidFile context, create channel, call run_daemon, cleanup
- [ ] bearclaw stop: read PID from config_dir/owlbear.pid, create sentinel file, poll PID removal (5s timeout), fallback to os.kill force-terminate
- [ ] bearclaw status: read PID file, check process alive via os.kill(pid, 0), report 'not running'/'running (PID X)'/'stale PID file'
- [ ] All tests from #151 pass
- [ ] ruff clean

## Architecture
- Sentinel file for cross-process shutdown — only reliable cross-platform mechanism (os.kill SIGTERM = TerminateProcess on Windows = instant kill, no cleanup)
- PidFile follows existing browser PID pattern (src/bearclaw/cli.py:371-389)
- Daemon loop mirrors _chat_loop pattern but wraps in PidFile + sentinel checks
- Single channel per invocation (YAGNI for multi-channel until proven needed)
