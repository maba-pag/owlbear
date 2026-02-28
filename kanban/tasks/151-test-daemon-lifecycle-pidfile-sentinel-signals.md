---
id: 151
title: Test daemon lifecycle — PidFile, sentinel, signals, logging
status: archived
priority: needed
created: 2026-02-27T16:45:51.9838766+01:00
updated: 2026-02-28T23:53:09.7263759+01:00
started: 2026-02-27T16:45:56.8333914+01:00
completed: 2026-02-28T23:53:09.7263759+01:00
tags:
    - phase-7
    - daemon
    - test
class: standard
---

TDD test task for #124 (bearclaw run daemon).

## AC
- [ ] File: tests/test_daemon.py
- [ ] Test: PidFile context manager — writes PID on __enter__, removes on __exit__
- [ ] Test: PidFile stale detection — PID file exists but process dead, cleans up and allows new run
- [ ] Test: PidFile conflict — PID file exists and process alive, raises RuntimeError
- [ ] Test: setup_logging — creates RotatingFileHandler (5MB, 3 backups) + stderr StreamHandler
- [ ] Test: sentinel file (config_dir/owlbear.stop) — run_daemon exits loop when sentinel appears
- [ ] Test: run_daemon — creates PID, receives message from mock channel, dispatches to agent.turn(), sends response, shuts down on sentinel
- [ ] Test: signal handler — SIGINT sets shutdown flag (same as sentinel check)
- [ ] Test: bearclaw stop — creates sentinel file, polls for PID removal, cleans up
- [ ] Test: bearclaw status — reports ''not running''/''running (PID X)''/''stale PID file''
- [ ] Tests use mock ChannelPlugin, tmp_path for config_dir, mock OwlBearAgent
- [ ] ruff clean

## Architecture
- PidFile is a context manager at src/owlbear/daemon.py
- Stale detection: os.kill(pid, 0) cross-platform
- Sentinel file: config_dir/owlbear.stop — daemon checks each loop iteration
- signal.signal(SIGINT/SIGTERM, handler) — NOT loop.add_signal_handler() (Windows compat)
- See docs/daemon-entrypoint-research.md for full design
