---
id: 578
title: Register owlbear-project server in workspace mcp.json
status: archived
priority: medium
created: 2026-04-03 11:38:44.931713+02:00
updated: 2026-04-03 14:28:31.814612+02:00
started: 2026-04-03 14:28:09.396623+02:00
completed: 2026-04-03 14:28:09.396623+02:00
tags:
- scope:config
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

owlbear-project is missing from .vscode/mcp.json (same gap as owlbear-memory fixed by #570). No agent tool patterns use owlbear-project/* yet, so this is lower priority. Add when agents need project MCP tools.
AC:
- [ ] .vscode/mcp.json includes owlbear-project entry
- [ ] Entry format matches existing servers

[[2026-04-03]] Fri 13:01
## Research
Validation pass: prior research at docs/research/register-mcp-project-server.md (owned by #577) fully covers this scope. Current mcp.json confirmed still missing owlbear-project. #577 is at todo (architect-approved, refined AC). #578 is an exact duplicate of #577 per both the research doc and architect review. No new findings. Recommend archiving #578 as duplicate.

[[2026-04-03]] Fri 14:28
## Audit
### Duplicate Closure
Confirmed duplicate of #577. Both the researcher (on #578) and the architect (on #577) independently identified duplication. Canonical task #577 is at todo with refined AC and architect approval.

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| mcp.json includes owlbear-project entry | Verified via terminal: entry absent. Work superseded by #577 (todo, architect-approved) | SUPERSEDED |
| Entry format matches existing servers | No entry added. Superseded by #577 | SUPERSEDED |

### Test Results
- pytest: Pre-existing failures from other in-progress tasks; #578 has zero code changes, no regressions possible
- ruff: N/A (no source changes)

### Reviewer Evidence
No Review Evidence section (task went through research-only duplicate path, not full pipeline).

### AC Quality Score: 4
AC was clear and specific. Issue was task-level duplication, not AC quality. Architect on #577 caught the duplication.

### Deduction breakdown
- Start: 1.00
- Missing reviewer evidence section (expected for duplicate path): -.02
### Confidence: .98
### Action: archive (duplicate of #577)
