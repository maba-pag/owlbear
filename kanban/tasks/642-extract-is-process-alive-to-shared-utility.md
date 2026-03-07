---
id: 642
title: Extract _is_process_alive to shared utility
status: backlog
priority: nice-to-have
created: 2026-03-07T07:56:23.9006051+01:00
updated: 2026-03-07T07:56:23.9006051+01:00
tags:
    - scope:core
    - cli
    - refactor
class: standard
---

DRY violation: _is_process_alive() is duplicated identically in cli.py (line 1016) and daemon.py (line 69). Extract to owlbear.core.process or owlbear.daemon (single canonical location), update both call sites and all test patches.

See docs/enhanced-bearclaw-status-research.md section 3.3.

## AC

- [ ] Single _is_process_alive(pid: int) -> bool in a shared module (e.g. owlbear.core.process)
- [ ] cli.py imports from shared module (no local definition)
- [ ] daemon.py imports from shared module (no local definition)
- [ ] All existing test patches updated to new import path (test_cli_daemon.py, test_daemon.py)
- [ ] All existing tests pass unchanged in behavior
- [ ] ruff clean
