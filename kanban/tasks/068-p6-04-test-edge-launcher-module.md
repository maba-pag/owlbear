---
id: 68
title: 'P6-04: Test Edge launcher module'
status: done
priority: high
created: 2026-02-26T23:30:35.1325412+01:00
updated: 2026-02-26T23:59:13.4471964+01:00
started: 2026-02-26T23:43:00.8241248+01:00
completed: 2026-02-26T23:59:13.4471964+01:00
tags:
    - phase-6
    - test
    - browser
class: standard
---

## Acceptance Criteria

Test file: tests/test_browser_launcher.py (new file)
Module under test: src/owlbear/tools/browser/launcher.py

### find_edge() tests
- Returns path when msedge.exe exists at Program Files (x86) standard location
- Returns path when msedge.exe exists at Program Files standard location
- Returns None when neither path exists
- Respects explicit executable parameter (returns override path as-is)
- Mock Path.exists() for filesystem isolation

### launch_edge_cdp() tests
- Calls subprocess.Popen with --remote-debugging-port={port} flag
- Returns subprocess PID
- Raises FileNotFoundError if executable path not found
- Mock subprocess.Popen for isolation

### is_cdp_available() tests
- Returns True when GET http://localhost:{port}/json/version returns 200
- Returns False on ConnectionError
- Returns False on timeout
- Mock httpx or urllib for isolation

### kill_edge() tests
- Terminates process with given PID
- Handles already-dead process gracefully (no exception)
- Mock os/subprocess for isolation
