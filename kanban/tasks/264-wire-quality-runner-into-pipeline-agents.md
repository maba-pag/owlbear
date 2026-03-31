---
id: 264
title: Wire Quality-Runner into pipeline agents
status: todo
priority: needed
created: 2026-03-30T19:31:12.4867876+02:00
updated: 2026-03-30T21:25:20.0315131+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 263
    - 430
class: standard
---

Wire Quality-Runner subagent into the 4 pipeline agents that run pytest/ruff directly. See docs/research/quality-runner-wiring.md for full analysis.

## Acceptance Criteria

- [ ] builder.agent.md frontmatter `agents` includes `quality-runner`
- [ ] reviewer.agent.md frontmatter `agents` includes `quality-runner`
- [ ] auditor.agent.md frontmatter `agents` includes `quality-runner`
- [ ] test-writer.agent.md frontmatter `agents` includes `quality-runner`
- [ ] tdd-workflow SKILL.md Steps 3, 4, 5, 7 replace direct `uv run pytest/ruff` commands with Quality-Runner subagent invocation pattern (mode: scoped, test_paths, lint_paths, optional coverage_modules)
- [ ] code-review SKILL.md Steps 3, 4, 5 replace direct commands with Quality-Runner subagent invocation
- [ ] task-verification SKILL.md Step 2 replaces direct commands with Quality-Runner subagent invocation (mode: full)
- [ ] tdd-red SKILL.md Step 5 replaces direct commands with Quality-Runner subagent invocation
- [ ] Each updated skill retains a fallback section with direct `uv run` commands referencing the pytest-and-linting skill for when Quality-Runner is unavailable
- [ ] No existing `execute/*` tools removed from any agent's `tools` list
- [ ] Existing `agents: []` replaced (not appended) so no empty array remains

## Files to modify

- agents/builder.agent.md (frontmatter only)
- agents/reviewer.agent.md (frontmatter only)
- agents/auditor.agent.md (frontmatter only)
- agents/test-writer.agent.md (frontmatter only)
- skills/tdd-workflow/SKILL.md (Steps 3, 4, 5, 7)
- skills/code-review/SKILL.md (Steps 3, 4, 5)
- skills/task-verification/SKILL.md (Step 2)
- skills/tdd-red/SKILL.md (Step 5)

[[2026-03-30]] Mon 21:25
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Agent frontmatter agents: [quality-runner] (x4) | Clear, verifiable, one-line change each | Keep |
| tdd-workflow Steps 3/4/5/7 QR invocation | Specific steps named, pattern defined | Keep |
| code-review Steps 3/4/5 QR invocation | Specific steps named | Keep |
| task-verification Step 2 QR invocation (mode: full) | Mode specified, single step | Keep |
| tdd-red Step 5 QR invocation | Specific step named | Keep |
| Fallback section per skill | Ensures graceful degradation if QR unavailable | Keep |
| No execute/* tools removed | Explicit negative constraint, prevents scope creep | Keep |
| agents: [] replaced cleanly | Prevents leftover empty arrays | Keep |

### Architecture Notes
- All 4 agents confirmed to have agents: [] currently, ready for wiring
- Existing test pattern in tests/test_disable_model_invocation.py provides frontmatter parsing helpers (_get_frontmatter, AGENTS_DIR) for the test task
- L2 nesting depth (orchestrator to pipeline to QR) is well within the max 5 limit
- Skill changes are documentation-level (replacing command examples), not code
- No module layering concerns: agent.md and SKILL.md files are configuration, not source
- No new security surface introduced
- Single domain: scope:agents (pipeline agent configuration)

### Changes Made
- Added depends_on: [263] (QR must exist before wiring)
- Created #430 (test task, todo, depends_on: [263])
- Added depends_on: [430] to #264 (TDD: tests precede impl)
- Rewrote body with 11-line verifiable AC
- Listed all 8 files to modify

### Dependencies
- Verified: #263 (Create Quality-Runner) in backlog, blocked by decision 228-esub-utility-subagents
- Created: #430 (Test: Wire Quality-Runner) in todo, depends_on: [263]
- Chain: decision 228 unblocks #263 unblocks #430 unblocks #264
