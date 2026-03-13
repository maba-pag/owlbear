---
id: 669
title: Tests for bootstrap startup summary
status: archived
priority: needed
created: 2026-03-08T02:59:39.5744675+01:00
updated: 2026-03-09T00:23:08.7140917+01:00
started: 2026-03-08T04:29:49.3129937+01:00
completed: 2026-03-09T00:23:08.7140917+01:00
tags:
    - test
    - resilience
    - scope:core
depends_on:
    - 668
class: standard
---

Write tests for the StartupSummary mechanism added in #668. AC: (1) Test all-OK summary when every component loads successfully. (2) Test FAIL entry when a configured component raises (mock _build_knowledge_infra to raise). (3) Test SKIP/WARNING entry when optional dep import fails. (4) Test channel.send is called with formatted summary text. (5) Test summary suppressed when log_startup_summary=False. (6) Test StartupSummary is present on BootstrapResult. (7) All tests pass; ruff clean. See docs/research/bootstrap-startup-summary.md.

[[2026-03-08]] Sun 23:57
Wave 3, agent: auditor

[[2026-03-09]] Mon 00:22
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| (1) all-OK summary | TestStartupSummaryDataclass::test_format_all_ok, L2209 | .97 |
| (2) FAIL entry on raise | TestBootstrapCollectsSummary::test_knowledge_infra_failure_recorded, L2345 | .97 |
| (3) SKIP/WARNING optional dep | test_web_search_failure_is_warning L2375 + test_format_shows_warnings L2246 | .97 |
| (4) channel.send with summary | test_channel_send_called_with_summary L2454, assert_called_once | .97 |
| (5) summary suppressed | test_channel_send_suppressed_when_disabled L2486, assert_not_called | .97 |
| (6) StartupSummary on BootstrapResult | test_startup_summary_on_result L2283 + test_bootstrap_returns_startup_summary L2302 | .97 |
| (7) tests pass + ruff clean | 20/20 passed, ruff All checks passed | 1.0 |

Overall: .97
