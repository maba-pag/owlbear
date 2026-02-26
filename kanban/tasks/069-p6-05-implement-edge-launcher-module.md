---
id: 69
title: 'P6-05: Implement Edge launcher module'
status: done
priority: high
created: 2026-02-26T23:30:44.111309+01:00
updated: 2026-02-27T00:07:21.5827305+01:00
started: 2026-02-26T23:43:01.1876934+01:00
completed: 2026-02-27T00:07:21.5827305+01:00
tags:
    - phase-6
    - browser
depends_on:
    - 67
    - 68
class: standard
---

## Acceptance Criteria

New file: src/owlbear/tools/browser/launcher.py

### Functions
- find_edge(executable: str | None = None) -> str | None
  Returns executable if provided; else probes standard Windows paths
  (Program Files x86 first, then Program Files). Returns None if not found.
- launch_edge_cdp(port: int = 9222, executable: str | None = None) -> int
  Calls find_edge, launches Edge with --remote-debugging-port={port} --no-first-run
  --user-data-dir={temp dir}. Returns PID. Raises FileNotFoundError if no Edge.
- is_cdp_available(port: int = 9222) -> bool
  HTTP GET to http://localhost:{port}/json/version. Returns True on 200, False otherwise.
- kill_edge(pid: int) -> None
  Terminates process by PID. Handles already-dead process (no exception).

### Implementation notes
- subprocess.Popen for launch (non-blocking)
- httpx or urllib.request for CDP health check
- Edge flags: --remote-debugging-port={port} --no-first-run --user-data-dir={tempfile.mkdtemp()}
- No browser package __init__.py export needed (internal module)
- All tests from #68 pass
