---
id: 579
title: Register owlbear-memory server in .vscode/mcp.json
status: archived
priority: medium
created: 2026-04-03 12:03:12.299597+02:00
updated: 2026-04-03 12:40:58.210374+02:00
started: 2026-04-03 12:40:57.745940+02:00
completed: 2026-04-03 12:40:57.745940+02:00
tags:
- scope:config
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

owlbear-memory MCP server is also missing from .vscode/mcp.json (same gap as #577). setup.py generates the entry for consumer projects and the package has __main__.py.

AC:
- .vscode/mcp.json includes owlbear-memory server entry matching existing pattern:
  type: stdio, command: uv, args: [run, python, -m, owlbear_mcp_memory]

[[2026-04-03]] Fri 12:04
Duplicate of #570 (owlbear-memory registration already tracked). Created in error by researcher during #577 investigation.

[[2026-04-03]] Fri 12:40
## Audit
### Duplicate Verification
- #579 AC: register owlbear-memory in mcp.json
- #570 AC: identical goal + kebab-case naming fix + test updates (strictly superset)
- #570 status: archived (work pending)
- #579 body states: Duplicate of #570, created in error by researcher during #577 investigation
- No deliverables produced (correct for duplicate)

### Test Results
- pytest: 1 collection error (test_set_approval_state_569.py ImportError) pre-existing, unrelated to #579
- ruff: not applicable (no source changes)

### Confidence: 1.0
Duplicate correctly identified. No work product expected or produced. #570 tracks the real work.

### Action: archive (duplicate)
