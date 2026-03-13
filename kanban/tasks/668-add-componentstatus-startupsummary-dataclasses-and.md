---
id: 668
title: Add ComponentStatus/StartupSummary dataclasses and collection to bootstrap
status: archived
priority: needed
created: 2026-03-08T02:59:32.1762923+01:00
updated: 2026-03-09T00:24:21.5913067+01:00
started: 2026-03-08T04:03:44.8832304+01:00
completed: 2026-03-09T00:24:21.5913067+01:00
tags:
    - resilience
    - scope:core
class: standard
---

Add ComponentStatus(name, loaded, error, level) and StartupSummary(components, workspace, project, channel) dataclasses to bootstrap.py. Modify each of the 9 _build_* helpers to append a ComponentStatus to a summary list. Classify failures: ERROR when user-configured component fails (e.g. github_token set but GitHubToolset init fails), WARNING when optional dep missing (e.g. ddgs not installed). Emit the assembled StartupSummary via logger.info at the end of bootstrap(). Gate channel.send behind log_startup_summary config setting (default True). AC: (1) ComponentStatus and StartupSummary are frozen dataclasses in bootstrap.py. (2) All 9 exception sites (knowledge infra, knowledge toolset, bookmark toolset, knowledge source toolset, web search, skill registry, github toolset, MCP registry, project toolset) append to the summary. (3) bootstrap() returns StartupSummary on BootstrapResult. (4) Single logger.info call at end with formatted multi-line summary. (5) channel.send called with formatted summary when log_startup_summary is True. (6) ERROR level for user-configured-but-failed components, WARNING for optional-dep-missing. (7) All existing tests pass; ruff clean. See docs/research/bootstrap-startup-summary.md.

[[2026-03-08]] Sun 23:57
Wave 3, agent: auditor

[[2026-03-09]] Mon 00:24
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| AC1: frozen dataclasses | _types.py: both @dataclass(frozen=True); tests verify AttributeError on assign (3 tests) | .97 |
| AC2: 9 exception sites append | toolsets.py: KnowledgeInfra/Toolset/Bookmark/Source/WebSearch/SkillRegistry/GitHub; registry.py: MCPRegistry; toolsets.py: ProjectToolset — all append ComponentStatus; 6 error-site tests pass | .97 |
| AC3: BootstrapResult.startup_summary | _types.py L99: startup_summary field; __init__.py passes it in return; test_bootstrap_returns_startup_summary passes | .97 |
| AC4: single logger.info | __init__.py: logger.info('Bootstrap complete:\n%s', summary_text); test_summary_logged passes | .97 |
| AC5: channel.send gated | __init__.py: if settings.log_startup_summary: await channel.send(); test_channel_send_called + _suppressed both pass | .97 |
| AC6: ERROR vs WARNING levels | GitHub/MCP/KnowledgeInfra/Project=ERROR; WebSearch/Bookmark/Source/Skill=WARNING; test_github_failure_is_error + test_web_search_failure_is_warning pass | .97 |
| AC7: tests pass, ruff clean | 145/146 pass (1 pre-existing slack_sdk failure); ruff all checks passed | .97 |

### Commit Log
No new commits needed — code already committed by prior agents.

### Push: pending (no new commits)
