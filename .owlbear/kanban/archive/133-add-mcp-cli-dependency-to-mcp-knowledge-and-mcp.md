---
id: 133
title: Add mcp[cli] dependency to mcp-knowledge and mcp-project pyproject.toml
status: archived
priority: medium
created: 2026-03-29 10:27:06.281778+02:00
updated: 2026-03-29 15:40:25.084055+02:00
started: 2026-03-29 15:40:24.796220+02:00
completed: 2026-03-29 15:40:24.796220+02:00
tags:
- phase-1
- scope:mcp
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Ensure both packages declare mcp[cli]>=1.26 as a dependency.

## Acceptance Criteria
- [ ] packages/mcp-knowledge/pyproject.toml lists mcp[cli]>=1.26 in dependencies
- [ ] packages/mcp-project/pyproject.toml lists mcp[cli]>=1.26 in dependencies

## Context
Identified during #120 research (docs/research/mcp-entry-points-overlap.md). Neither #54 nor #17 explicitly include this requirement. Trivial change but blocks server startup.

[[2026-03-29]] Sun 11:08
## Research
N/A -- trivial change. Validated via research checklist (trivial path):
- Theoretical validity: Sound. Both packages need mcp[cli] to run mcp.run().
- Prior art: mcp-kanban pyproject.toml already declares mcp[cli]>=1.26.
- Technical feasibility: mcp 1.26.0 is latest on PyPI (Jan 2026).
- Architecture fit: Follows existing mcp-kanban pattern exactly.
- Implementation: Add deps section to mcp-knowledge; append to existing deps in mcp-project.
- Parent research: docs/research/mcp-entry-points-overlap.md (#120).

[[2026-03-29]] Sun 11:54
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| mcp-knowledge pyproject.toml lists mcp[cli]>=1.26 | Clear, verifiable. mcp-knowledge currently has no deps section at all. | Keep |
| mcp-project pyproject.toml lists mcp[cli]>=1.26 | Clear, verifiable. mcp-project has existing deps (pydantic). Append to list. | Keep |

### Architecture Notes
Follows established pattern from mcp-kanban/pyproject.toml exactly. Trivial config change, no code, no new interfaces.
No test task needed (type:build, dependency declaration only).

### Changes Made
- Approved as-is, AC sufficient

### Dependencies
- None required. Self-contained config change.

[[2026-03-29]] Sun 13:04
## Test-Writer Notes
- Non-implementation task (tagged type:build) -- no tests applicable.
- Architect confirmed: dependency declaration only, no code changes.
- Passing through to builder.

[[2026-03-29]] Sun 14:58
## Builder Notes
- Files changed: packages/mcp-knowledge/pyproject.toml, packages/mcp-project/pyproject.toml
- mcp-knowledge: added dependencies = [mcp[cli]>=1.26] (no deps section previously)
- mcp-project: appended mcp[cli]>=1.26 to existing dependencies list alongside pydantic
- Follows mcp-kanban pattern exactly
- Tests: N/A (type:build, dependency declaration only)
- Lint: N/A (TOML files)
- Commit: 9fb58e2

[[2026-03-29]] Sun 15:40
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| mcp-knowledge pyproject.toml lists mcp[cli]>=1.26 | Line 6: dependencies = [mcp[cli]>=1.26] | PASS |
| mcp-project pyproject.toml lists mcp[cli]>=1.26 | Line 8: mcp[cli]>=1.26 alongside pydantic | PASS |

### Test Results
- pytest: 679 passed, 90 failed (all pre-existing RED-phase tests from other tasks, none related to #133)
- ruff: N/A (TOML files only, no Python source changes)
- 4 collection errors excluded (unimplemented modules: validate_agents, voice, mcp-knowledge server)

### Commit Verification
- 9fb58e2 chore: add mcp[cli]>=1.26 to mcp-knowledge and mcp-project (#133, builder) -- correct format

### AC Quality: 5/5
AC was specific (exact package, version, files), complete, and led to clean implementation.

### Confidence: .98
### Action: archive
