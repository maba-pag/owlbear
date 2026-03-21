---
id: 633
title: Evaluate Textual TUI dashboard for Phase 11+
status: archived
priority: someday
created: 2026-03-07T05:27:17.9098384+01:00
updated: 2026-03-21T13:38:57.1522199+01:00
started: 2026-03-07T14:03:23.1149954+01:00
completed: 2026-03-21T13:38:53.1799338+01:00
tags:
    - research
    - scope:cli
    - phase-11
class: standard
---

Textual TUI evaluation complete. See docs/research/textual-tui-dashboard.md for the full analysis.

Decision: DEFER for the current Phase 11 planning window.

Textual itself is production-ready, but OwlBear does not currently expose a daemon event stream or other external IPC surface for live dashboard updates. The current single-user laptop daemon also does not justify the additional dashboard maintenance surface.

Re-evaluate only when:
- autonomous_mode is default-on with concurrent task execution, or
- another approved feature requires daemon event stream IPC for live status delivery.

This task does not approve implementation work. If it is revived later, split the work into separate tasks:
- scope:core: daemon event stream / IPC surface
- scope:cli: bearclaw dashboard TUI

## AC

- [ ] Decision documented: DEFER with rationale linked to docs/research/textual-tui-dashboard.md
- [ ] Current blockers documented: no external daemon event stream IPC and no present multi-agent monitoring need
- [ ] Re-evaluation triggers documented: concurrent autonomous orchestration or another approved daemon event stream consumer

[[2026-03-21]] Sat 06:18
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Prototype bearclaw dashboard with Textual | Not approvable as implementation AC. The research doc concludes do-not-build-now, and a prototype would couple CLI UI work to a missing core IPC surface. | Rewrote as decision-only AC |
| Layout: task panel + status panel + usage panel | Too solution-specific for a deferred research task and not independently valuable without a live data surface. | Rewrote as background note only |
| Live updates via daemon event stream | Assumes a core IPC boundary that does not exist in the current architecture. If revived later, this must be a separate scope:core task. | Rewrote as blocker and re-evaluation trigger |
| Evaluate LOC cost vs value | Valid concern, but too vague. Research already quantified the cost and current poor ROI. | Rewrote with explicit research link and blocker summary |
| Decision: adopt or reject with rationale | Correct task shape for a research evaluation item. | Kept and tightened |

### Architecture Notes
Existing CLI status and usage surfaces are point-in-time reads, not live dashboards: src/bearclaw/commands/daemon.py reads PID/config files and renders a rich Panel, and src/bearclaw/commands/usage.py reads UsageTracker JSONL and prints a static table. Progress and observability are channel/file based rather than externally queryable daemon IPC: src/owlbear/core/progress.py sends heartbeat updates through ChannelPlugin, and src/owlbear/core/observability.py appends JSONL events through EventStore. The deeper research doc at docs/research/textual-tui-dashboard.md confirms OwlBear still lacks a daemon event stream surface and recommends DEFER. This task is architecturally sound only as a non-implementation decision task. If revived later, split work into separate scope:core event-stream IPC and scope:cli dashboard tasks, each with its own TDD pair.

### Changes Made
- Rewrote the task body to reflect the completed research decision and explicit re-evaluation triggers
- Replaced prototype-style AC with verifiable decision/blocker criteria
- Approved the task as a non-implementation research/defer item

### Dependencies
- Added/Removed/Verified: no code dependencies for this decision-only task
- Added/Removed/Verified: no preceding test task required because no implementation is being approved
- Added/Removed/Verified: future revival must split scope:core event-stream IPC from scope:cli dashboard UI

[[2026-03-21]] Sat 06:30
## Test-Writer Notes
- Non-implementation task (tagged research) — no tests applicable.
- Passing through to builder.

[[2026-03-21]] Sat 06:54
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-03-21]] Sat 12:38
## Review Evidence: PASS (.95).

## Review: #633 - Evaluate Textual TUI dashboard for Phase 11+

### Test Results

- pytest scoped: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_cli_daemon.py tests/test_cli_status_rich.py tests/test_usage_cli.py -p pytest_asyncio.plugin -q --tb=short -> 43 passed, 2 warnings.

- coverage run: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/test_cli_daemon.py tests/test_cli_status_rich.py tests/test_usage_cli.py -p pytest_asyncio.plugin -p pytest_cov -q --tb=short --cov --cov-report=term-missing --cov-fail-under=0 -> 43 passed, 2 warnings.

### Lint Results

- ruff: uv run ruff check src/bearclaw/commands/daemon.py src/bearclaw/commands/usage.py src/owlbear/core/progress.py src/owlbear/core/observability.py -> All checks passed.

### Coverage

- Informational only for this non-implementation task. Scoped run reported daemon.py 79 percent, usage.py 99 percent, progress.py 0 percent, observability.py 36 percent.

### Pass 1 - CRITICAL

#### Security Review

- No security issues found. Task output is decision and research documentation only; no new executable code or dependency changes.

#### Test Integrity (TestFromAC comparison)

- Not applicable: no TestFromAC_* classes in task-scoped test files.

#### Test Quality

| Dimension | Rating | Evidence |

|---|---|---|

| Assertion specificity | ADEQUATE | test_output_contains_uptime, test_detail_shows_model, test_active_project_shown, and test_force_kill_fallback assert concrete values and call arguments. |

| Negative or error paths | ADEQUATE | test_missing_file_shows_message and test_last_hour_excludes_old_records cover absent data and filtering behavior. |

| Mutation reasoning | ADEQUATE | Regressions in status labels, uptime formatting, and usage window filtering would fail targeted assertions. |

| Test independence | STRONG | tmp_path fixtures and per-test patching isolate mutable state. |

| Descriptive names | STRONG | Test names describe scenario and expected outcome clearly. |

#### Data Safety

- No data safety issues found. AC scope records decision and trigger criteria only.

### Pass 2 - INFORMATIONAL

- Plain pytest initially interrupted during third-party plugin import. Using PYTEST_DISABLE_PLUGIN_AUTOLOAD with explicit plugins produced stable and repeatable runs.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |

|---|---|---|---|

| Decision documented: DEFER with rationale linked to docs/research/textual-tui-dashboard.md | kanban/tasks/633-evaluate-textual-tui-dashboard-for-phase-11.md:20 documents DEFER; kanban/tasks/633-evaluate-textual-tui-dashboard-for-phase-11.md:18 links the research doc; docs/research/textual-tui-dashboard.md:83 contains reject/defer rationale. | N/A (documentation AC) | PASS |

| Current blockers documented: no external daemon event stream IPC and no present multi-agent monitoring need | kanban/tasks/633-evaluate-textual-tui-dashboard-for-phase-11.md:22 states no daemon event stream and single-user constraint; docs/research/textual-tui-dashboard.md:91 and docs/research/textual-tui-dashboard.md:92 reinforce blockers. | N/A (documentation AC) | PASS |

| Re-evaluation triggers documented: concurrent autonomous orchestration or another approved daemon event stream consumer | kanban/tasks/633-evaluate-textual-tui-dashboard-for-phase-11.md:24 plus lines 25-26 list triggers; docs/research/textual-tui-dashboard.md:95 mirrors triggers. | N/A (documentation AC) | PASS |

### Verdict: PASS (confidence .95)

### Action Taken: advancing review -> docs.

[[2026-03-21]] Sat 13:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Decision documented: DEFER with rationale linked to docs/research/textual-tui-dashboard.md | Task body L20 states DEFER; L18 links research doc; research doc S4 has .35 confidence defer rationale | PASS |
| Current blockers documented: no external daemon event stream IPC and no present multi-agent monitoring need | Task body L22 states no daemon event stream and single-user constraint; research doc S3.2 details infra gap table | PASS |
| Re-evaluation triggers documented: concurrent autonomous orchestration or another approved daemon event stream consumer | Task body L24-26 lists triggers; research doc S3.5 and S4 mirror triggers | PASS |

### Research Task Verification
- Research doc exists: docs/research/textual-tui-dashboard.md (150 lines, complete)
- Follow-up tasks: Research doc S5 explicitly states 'No implementation tasks recommended at this time - defer is the recommendation.' Valid no-action justification.

### Test Results
- pytest full suite: 3702 passed, 105 failed, 20 skipped (--ignore=test_security_audit_log.py)
- All 105 failures are pre-existing and unrelated to #633 (numpy API, bootstrap refactoring, etc.)
- ruff: pre-existing warnings only, none related to #633
- No code changes produced by this non-implementation research task

### Confidence: .97
### Action: archive
