---
id: 209
title: Add stop commit guard hooks to builder and writer agents (Phase 1)
status: archived
priority: medium
created: 2026-03-30 08:52:09.122925+02:00
updated: 2026-04-04 07:10:40.902007+02:00
started: 2026-04-04 07:09:49.794291+02:00
completed: 2026-04-04 07:09:49.794291+02:00
tags:
- phase-1
- scope:agents
- hooks
- type:build
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-30]] Mon 12:56
## Builder Notes
- Files changed: scripts/hooks/stop-commit-guard.ps1 (new), agents/builder.agent.md, agents/writer.agent.md, .vscode/settings.json
- Tests: 23 passed, all TestFromAC classes green
- Lint: ruff clean
- Evidence: 23 passed in 4.28s; git commit a0aa1ca
- Fixes applied: None (clean implementation)
- Note: VS Code schema validator flags hooks as unknown attribute (Attribute hooks is not supported) but YAML parses correctly; this reflects 3/25/2026 spec adoption before extension schema update

[[2026-03-30]] Mon 13:50
## Runtime Defect Analysis

Task moved back to ideation. Two issues found that prevent builder and writer agents from dispatching.

### Issue 1: hooks use windows: instead of command: (agent crash)

The VS Code hooks API requires a base `command` property. The `windows` key is a platform-specific override, not a standalone field. When only `windows` is specified, VS Code reads `command` (undefined) and crashes with: "Cannot read properties of undefined (reading 'length')".

Evidence: VS Code docs (3/25/2026 spec) state: "Each hook entry must have type: command and at least one command property." The OS-specific section shows `windows` alongside a base `command`, with fallback behavior: "If no OS-specific command is defined, it falls back to the command property."

Affected files: agents/builder.agent.md, agents/writer.agent.md (both have `windows:` without `command:`).

Fix needed in agents: Change `windows: powershell -NoProfile -File ...` to `command: powershell -NoProfile -File ...` in both agent files. The project is Windows-only so a platform-specific override is unnecessary.

Fix needed in tests: 4 test assertions in tests/test_stop_commit_guard_hooks.py check for `windows:` in frontmatter (lines 228-231, 273-276). These must be updated to assert `command:` instead.

Fix needed in AC: AC items 2 and 3 reference `windows:` key. Must be corrected to `command:`.

### Issue 2: script blocks on ALL uncommitted changes (multi-agent design flaw)

The script runs `git status --short` globally. In the orchestration pipeline, multiple agents run concurrently (builder, writer, reviewer, test-writer). When agent A finishes its work but agent B has uncommitted changes in the same repo, agent A's Stop hook sees agent B's dirty files and blocks. This is a deadlock risk: no agent can exit until ALL agents have committed.

Root cause: The script has no concept of which files belong to which agent session. It treats the entire working tree as a single unit.

Options for redesign:
1. Scope to agent's own files: VS Code hooks receive session context via stdin JSON. If the session ID or agent name can be correlated with git changes, the script could filter. However, no such mapping exists today.
2. Remove blocking, use systemMessage: Return a warning instead of a block decision. Agents see the reminder but are not prevented from exiting.
3. Defer to agent instructions: Remove the hook entirely. The agent-common instructions already say "commit before handoff." A hook adds complexity without benefit if the agent follows its instructions.

Recommendation: Option 3 (remove hook) or Option 2 (non-blocking warning). The blocking model is incompatible with parallel agent dispatch.

### Summary of required changes

- agents/builder.agent.md: `windows:` to `command:` (or remove hooks section entirely if choosing option 3)
- agents/writer.agent.md: same
- tests/test_stop_commit_guard_hooks.py: update 4 assertions from `windows:` to `command:`; add/update tests for multi-agent scenario if redesigning
- scripts/hooks/stop-commit-guard.ps1: redesign or remove depending on chosen approach
- AC items 2 and 3: correct `windows:` to `command:`
- Research doc (docs/research/stop-commit-guard-hooks-phase1.md section 4): update recommended YAML format

[[2026-03-30]] Mon 14:13
## Architecture Review (2nd cycle)
**Verdict:** Block to ideation

### Premise Challenge: Hook model incompatible with agent architecture

Both target agents (builder, writer) have `disable-model-invocation: true` and run exclusively in the orchestration pipeline via parallel dispatch. The blocking Stop hook model creates a deadlock in this scenario:

1. Orchestrator dispatches builder + writer (+ reviewer, test-writer) in parallel
2. Builder finishes, Stop hook fires, `git status --short` sees writer's uncommitted files, blocks
3. Writer finishes, Stop hook fires, sees builder's uncommitted files, blocks
4. Neither agent can exit until ALL agents commit: deadlock

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Create stop-commit-guard.ps1 | Script exists but uses blocking model incompatible with parallel dispatch | Needs redesign or removal |
| Add hooks to builder.agent.md | Uses `windows:` instead of `command:` (API mismatch), and blocking model deadlocks | Blocked |
| Add hooks to writer.agent.md | Same issues as builder | Blocked |
| chat.useCustomAgentHooks setting | Already present (.vscode/settings.json line 70), this AC item is already satisfied | No action needed |
| Verify YAML parses | Moot until hook model is resolved | Blocked |
| Script handles 3 cases | Blocking behavior in case (b) is the root problem | Needs redesign |

### Architecture Notes

- The `windows:` vs `command:` fix (Issue 1) is trivial but moot without resolving the blocking model
- Non-blocking `systemMessage` alternative is unresearched: no confirmation it is a valid Stop hook return type per VS Code 3/25/2026 spec
- Agent-common instructions Commit discipline section already mandates committing before handoff: the hook was defense-in-depth for a defense that does not work in multi-agent contexts
- YAGNI: per-agent dirty-file scoping infrastructure does not exist and is not worth building
- The 23 existing tests assert the blocking model (decision block, windows key) and would need full rewrite for any alternative approach

### Options requiring research before re-entry

1. Validate whether systemMessage is a supported Stop hook return (VS Code hooks API)
2. If supported: does it reach the agent conversation context before session termination?
3. If both yes: is the soft reminder valuable enough for pipeline-only agents that already follow commit discipline instructions?
4. Alternative: apply Stop hooks only to user-invocable agents (none currently, but future-proofing), skip pipeline-only agents entirely

### Changes Made

- Blocked task to ideation (premise invalidated by multi-agent architecture)
- No code or test changes (architect does not write code)

### Dependencies

- #210 and #211 (Phase 2/3 hooks) depend on #209: they inherit the same multi-agent concern
- #212 (update #86 research doc) is a follow-up, not blocked by this
