---
id: 374
title: 'Remove #209 stop commit guard artifacts (script, tests, hooks YAML)'
status: backlog
priority: nice-to-have
created: 2026-03-30T20:46:30.37835+02:00
updated: 2026-03-30T23:51:15.7719769+02:00
tags:
    - scope:agents
    - hooks
    - type:build
class: standard
---

## Context
See docs/research/stop-hook-multi-agent-viability.md for full analysis.
#209 blocking Stop hook model is incompatible with parallel subagent dispatch. Artifacts from the invalidated implementation should be removed.

## Acceptance Criteria
- [ ] Delete scripts/hooks/stop-commit-guard.ps1
- [ ] Delete tests/test_stop_commit_guard_hooks.py
- [ ] Remove hooks: section from agents/builder.agent.md YAML frontmatter
- [ ] Remove hooks: section from agents/writer.agent.md YAML frontmatter
- [ ] Verify both agent files still parse with valid YAML frontmatter
- [ ] Verify test suite passes without the deleted test file
