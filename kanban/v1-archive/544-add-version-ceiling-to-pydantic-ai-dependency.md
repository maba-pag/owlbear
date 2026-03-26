---
id: 544
title: Add version ceiling to pydantic-ai dependency
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:48.087624+01:00
updated: 2026-03-22T19:17:40.009551+01:00
started: 2026-03-07T00:45:03.3239141+01:00
completed: 2026-03-22T19:17:40.009551+01:00
tags:
    - audit
    - config
    - deps
blocked: true
block_reason: 'Stale backlog regression: HEAD already contains pydantic-ai>=1.0.0,<2.0.0 via commit b543620 (#544); do not redispatch to builder.'
class: standard
---

F-02: pydantic-ai >=0.1.0 with no ceiling. See docs/config-dependency-audit.md.

Research (2026-03-07): N/A -- trivial version pin.
- Installed: v1.63.0, latest: v1.67.0, v1.0.0 released 2025-09-04
- Version policy: no breaking changes until V2 (April 2026 earliest)
- Current floor >=0.1.0 is wrong -- 0.1.x lacks Toolsets, RetryConfig, OpenAIChatModel
- Recommendation (.90): change to >=1.0.0,<2.0.0
- Risk: two private API imports (_agent_graph.HistoryProcessor, _run_context.RunContext) not covered by semver guarantee -- separate task needed

AC: Change pyproject.toml dep from pydantic-ai>=0.1.0 to pydantic-ai>=1.0.0,<2.0.0

[[2026-03-21]] Sat 04:13
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Change pyproject.toml dep from pydantic-ai>=0.1.0 to pydantic-ai>=1.0.0,<2.0.0 | Already satisfied in committed repo state: HEAD pyproject.toml contains pydantic-ai>=1.0.0,<2.0.0, and git history includes commit b543620 (chore: add version ceiling to pydantic-ai dependency (#544, builder)) | Do not dispatch; block stale backlog card |

### Architecture Notes
- Scope is atomic and config-only, but the implementation contract is already complete in repository history.
- docs/config-dependency-audit.md identified the dependency-risk class; this task's research updated the target contract to post-1.0 bounds, and HEAD already matches that contract.
- Current working tree has a pyproject.toml modification, but git diff shows it only touches Ruff per-file ignores; the pydantic-ai spec remains satisfied.
- The separate semver-risk follow-up is already represented by #852 with RED partner #854, so no new split or follow-up task is needed here.
- TDD check: no dedicated RED predecessor is discoverable for the original config pin, but because the requested change is already committed, creating a fresh RED/GREEN pair now would duplicate closed work rather than improve coverage.

### Changes Made
- Claimed #544 as architect.
- Appended this architecture review.
- Blocking the task in ideation to prevent duplicate builder dispatch against already-completed work.

### Dependencies
- Verified: committed repo state already satisfies the AC in pyproject.toml.
- Verified: follow-up compatibility risk is tracked separately by #852 and #854.
- No additional dependencies or splits required.
