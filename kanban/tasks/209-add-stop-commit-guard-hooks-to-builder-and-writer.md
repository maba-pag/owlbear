---
id: 209
title: Add stop commit guard hooks to builder and writer agents (Phase 1)
status: in-progress
priority: nice-to-have
created: 2026-03-30T08:52:09.122925+02:00
updated: 2026-03-30T10:18:16.716867+02:00
tags:
    - phase-1
    - scope:agents
    - hooks
    - type:build
class: standard
---

## Context

See docs/research/stop-commit-guard-hooks-phase1.md for full analysis.
See docs/research/agent-scoped-hooks-pipeline-enforcement.md section 6 for rollout guidance.

Phase 1 of VS Code agent-scoped hooks adoption: add a Stop hook to builder and writer agents that blocks session end when uncommitted work exists. Uses the command-execution model (type: command), not prompt injection.

## Acceptance Criteria

- [ ] Create scripts/hooks/stop-commit-guard.ps1 that:
  - Reads stdin JSON for hook context
  - Returns immediately (empty JSON) if stop_hook_active is true (loop prevention)
  - Runs git status --short to detect uncommitted changes
  - If dirty: returns JSON with decision block and reason
  - If clean: returns empty JSON
- [ ] Add hooks section to agents/builder.agent.md YAML frontmatter with a Stop hook entry (type: command, windows: powershell -NoProfile -File scripts/hooks/stop-commit-guard.ps1)
- [ ] Add identical hooks section to agents/writer.agent.md YAML frontmatter
- [ ] Add chat.useCustomAgentHooks: true to .vscode/settings.json if not already present
- [ ] Verify both agent files have valid YAML frontmatter (no parse errors in VS Code Problems panel)
- [ ] Verify the script handles three cases: (a) clean working tree returns empty JSON, (b) dirty working tree returns block decision JSON, (c) stop_hook_active true in stdin returns immediately without blocking

[[2026-03-30]] Mon 09:29
## Architecture Review
**Verdict:** Approve

### AC Assessment

Original AC used outdated prompt-injection model. Researcher identified the correct command-execution model in Phase 1 research (docs/research/stop-commit-guard-hooks-phase1.md). AC has been rewritten to match.

All 6 AC lines are now verifiable pass/fail:
1. Script creation: file exists + 3 behavioral checks
2. Builder frontmatter: hooks section present with correct YAML
3. Writer frontmatter: identical hooks section
4. Settings.json: key present
5. YAML parse validation: no VS Code Problems panel errors
6. Script behavior: 3 test cases specified

### Architecture Notes

- No existing hooks in any agent files (clean slate, confirmed via grep)
- scripts/hooks/ directory is new, follows project convention (scripts/ for tooling)
- PowerShell script is the correct approach: testable, handles loop prevention, produces structured JSON
- Single shared script referenced by both agents avoids duplication (DRY)
- No Python code involved, TDD compliance waived (YAML + PowerShell + JSON config only)
- Pattern: Stop hook with type: command + script path follows VS Code hooks API (3/25/2026 spec)
- Security surface: script runs git status only (read-only operation, no user input parsing)

### Changes Made
- Rewrote AC body to match command-execution hook model (was prompt-injection)
- Removed outdated AC item about documenting in Builder Notes (that is Channel B convention, not AC)
- Added explicit script deliverable and behavioral verification criteria

### Dependencies
- None required (clean slate)
- #212 (update #86 research doc) is a follow-up, not a dependency
- #210 and #211 (Phase 2/3 hooks) depend on #209 for the settings.json prerequisite

[[2026-03-30]] Mon 10:18
## Test-Writer Notes\n- Test file: tests/test_stop_commit_guard_hooks.py\n- Classes: TestFromAC_StopCommitGuardScript, TestFromAC_BuilderAgentHooks, TestFromAC_WriterAgentHooks, TestFromAC_VscodeSettings\n- Total: 23 tests, all FAIL on current HEAD\n- ruff: clean\n- AC6 behavioral tests marked @pytest.mark.slow
