---
id: 430
title: 'Test: Wire Quality-Runner into pipeline agents'
status: todo
priority: needed
created: 2026-03-30T21:24:44.6433602+02:00
updated: 2026-03-30T21:24:49.8656872+02:00
tags:
    - scope:agents
    - phase-2
    - test
depends_on:
    - 263
class: standard
---

Test task for #264. Verify Quality-Runner wiring in agent frontmatter and skill files.

## Acceptance Criteria

- [ ] Test verifies builder, reviewer, auditor, test-writer agent.md files have quality-runner in agents array
- [ ] Test verifies agents array is not empty (no leftover agents: [])
- [ ] Test verifies tdd-workflow, code-review, task-verification, tdd-red SKILL.md files contain Quality-Runner invocation references
- [ ] Test verifies each updated skill retains fallback section with direct uv run commands
- [ ] Test verifies no execute/* tools were removed from any of the 4 agents
- [ ] All tests fail before #264 implementation (RED phase)

## Files to create

- tests/test_quality_runner_wiring_264.py

## Patterns to follow

- tests/test_disable_model_invocation.py (frontmatter parsing, AGENTS_DIR, _get_frontmatter helper)
