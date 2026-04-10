---
id: 575
title: Close minor test coverage gaps across modules
status: archived
priority: someday
created: 2026-03-04T07:39:17.2171749+01:00
updated: 2026-03-22T19:17:48.5889079+01:00
started: 2026-03-07T04:52:07.8327597+01:00
completed: 2026-03-22T19:17:48.5889079+01:00
tags:
    - audit
    - test
blocked: true
block_reason: 'Superseded by archived #830/#831; #575 is a stale umbrella task and current repo tests already implement the coverage work.'
class: standard
---

Coverage gaps verified 2026-03-07. github_api already at 100% (gap closed). Remaining: 27 lines across 5 modules. See docs/research/close-test-coverage-gaps.md for exact lines and test strategies. Split into 2 follow-up tasks: bootstrap handlers (14 lines) + quick wins (13 lines across browser config, ask_user, filesystem, usage).

## AC

- [x] Research doc at docs/research/close-test-coverage-gaps.md
- [x] Verified remaining 27 lines across 5 modules
- [x] Split into 2 follow-up tasks: bootstrap handlers (14 lines) + quick wins (13 lines)

[[2026-03-21]] Sat 06:18
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Research doc at docs/research/close-test-coverage-gaps.md | Valid historical research, but no longer safe as a builder contract. The doc still points the bootstrap work at src/owlbear/bootstrap.py even though the code now lives under src/owlbear/bootstrap/. | Keep as traceability only; do not route to builder. |
| Verified remaining 27 lines across 5 modules | Historical snapshot across bootstrap, browser config, ask_user, filesystem, and usage. This is an audit summary spanning assembly, tools, and memory layers, not a single executable task. | Treat as stale umbrella scope. |
| Split into 2 follow-up tasks: bootstrap handlers (14 lines) + quick wins (13 lines) | Completed. Child tasks #830 and #831 were created from this research and are both archived, and the repo already contains the delivered tests in tests/test_bootstrap.py, tests/test_browser_config.py, tests/test_ask_user.py, tests/test_filesystem_tools.py, and tests/test_usage_tracker.py. | Park the parent task and point future readers at the child lineage. |

### Architecture Notes
- Single-responsibility: #575 bundles bootstrap assembly, browser config, ask_user, filesystem, and usage. That was useful as research, but it is not approval-ready for builder flow.
- Repository drift: docs/research/close-test-coverage-gaps.md still references src/owlbear/bootstrap.py, but the current codebase uses the src/owlbear/bootstrap/ package (knowledge.py, toolsets.py, registry.py). Approving this parent would dispatch stale work against the wrong seam.
- TDD/lineage: the executable contracts already existed as #830 and #831, and both are archived with test-writer, builder, reviewer, and auditor evidence.
- Current repo evidence: tests/test_bootstrap.py contains TestFromAC_KnowledgeToolsetExceptPath, TestFromAC_BookmarkToolsetExceptPath, and TestFromAC_WireKnowledgeToolsetsOuterExcept; tests/test_browser_config.py, tests/test_ask_user.py, tests/test_filesystem_tools.py, and tests/test_usage_tracker.py contain the quick-win coverage tests from #831.
- Architectural decision: do not approve or refine this parent into todo. Block it and return it to ideation as a stale duplicate/traceability card so it stays out of dispatch rotation.

### Changes Made
- Claimed task #575 as architect.
- Appended this Architecture Review section.
- Added a block reason so planners do not redispatch already-completed child scope.

### Dependencies
- Verified: docs/research/close-test-coverage-gaps.md
- Verified successor lineage: #830 and #831 are archived.
- Verified repo evidence: tests/test_bootstrap.py, tests/test_browser_config.py, tests/test_ask_user.py, tests/test_filesystem_tools.py, tests/test_usage_tracker.py
- Verified bootstrap layout drift: src/owlbear/bootstrap/ exists; src/owlbear/bootstrap.py does not.
