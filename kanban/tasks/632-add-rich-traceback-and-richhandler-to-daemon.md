---
id: 632
title: Add rich.traceback and RichHandler to daemon logging
status: backlog
priority: nice-to-have
created: 2026-03-07T05:27:09.1043318+01:00
updated: 2026-03-07T14:03:30.6521984+01:00
started: 2026-03-07T14:03:30.6521984+01:00
tags:
    - phase-cli
    - scope:core
    - cli
class: standard
---

Install rich.traceback.install() in bearclaw CLI app callback for better error display. Replace daemon setup_logging() stderr handler with rich.logging.RichHandler for structured console output. File handler must remain plain text (no ANSI in logs).\n\nSee docs/workflow-dashboards-devtools-research.md S3.4.\n\nAC:\n- [ ] rich.traceback.install() called in CLI app callback (affects CLI only, not daemon fork)\n- [ ] Daemon stderr handler uses RichHandler with timestamp and level coloring\n- [ ] File handler remains RotatingFileHandler with plain-text formatter (no ANSI codes)\n- [ ] Log output to file verified free of ANSI escape sequences in test\n- [ ] ruff clean
