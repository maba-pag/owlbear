---
id: 211
title: Add preToolUse read-only guard hook to reviewer agent (Phase 2, 
  defense-in-depth)
status: archived
priority: medium
created: 2026-03-30 08:52:23.636729+02:00
updated: 2026-04-03 06:42:32.230415+02:00
started: 2026-04-03 06:42:10.407145+02:00
completed: 2026-04-03 06:42:10.407145+02:00
tags:
- scope:agents
- hooks
- type:build
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Context

Defense-in-depth: adds a PreToolUse hook to the reviewer agent as a secondary
guard against accidental file edits, complementing the existing tools: restriction
in the frontmatter. Uses permissionDecision: deny (platform-level, control plane).

References:
- docs/research/pretooluse-read-only-guard-feasibility.md (T1, .65 confidence)
- docs/research/hook-ac-command-execution-model.md (AC correction rationale, #213)
- docs/research/agent-scoped-hooks-pipeline-enforcement.md s4 (Candidate 5) and s6

Dependency note: Task body originally said "Depends on: #209." #209 is blocked in
ideation (Stop hook premise invalidated). The only prerequisite from #209 was the
chat.useCustomAgentHooks setting, which is already enabled at .vscode/settings.json:69.
PreToolUse uses a structurally different mechanism than Stop hooks (permissionDecision
vs systemMessage), so #209 invalidation does not affect #211.

Soft dependency: #548 (verify hook routing in subagent context) is blocked pending
user action. Proceed without waiting. Implementation cost is minimal (~20 LOC),
trivially removable if subagent routing proves non-functional.

## Acceptance Criteria

- [ ] Add PreToolUse hook section to agents/reviewer.agent.md YAML frontmatter: type: command, command: pointing to scripts/hooks/deny-writes.ps1
- [ ] Create scripts/hooks/deny-writes.ps1 that reads stdin JSON, extracts tool_name, and filters for write tools: create_file, replace_string_in_file, multi_replace_string_in_file, create_directory, apply_patch
- [ ] On write tool match: returns JSON with hookSpecificOutput.permissionDecision = "deny" and hookSpecificOutput.permissionDecisionReason explaining reviewer is read-only
- [ ] On non-write tools or missing/malformed tool_name: returns empty JSON {}
- [ ] Prerequisite: chat.useCustomAgentHooks already enabled at .vscode/settings.json:69 (verify only, no action needed)
- [ ] Hook must not conflict with existing tools: restrictions in reviewer.agent.md
- [ ] Agent file parses as valid YAML frontmatter after hook addition

[[2026-04-02]] Thu 23:11
## Research
Doc: docs/research/pretooluse-read-only-guard-feasibility.md
Classification: T1 (autonomous) â€” decision made upstream in #86 parent research.

Key findings (.65 confidence):
- PreToolUse permissionDecision: deny is platform-level enforcement (control plane, not data plane)
- Defense-in-depth behind existing tools: restriction (primary guard)
- Terminal bypass is a known limitation (reviewer needs run_in_terminal for pytest/ruff)
- Subagent PreToolUse routing unverified empirically (soft-depend on #548 spike)

Challenger: reconsider â€” lowered confidence from .80 to .65. Adopted sequencing advice and complementary static test.

Follow-up tasks created:
- #561: Add static test: reviewer tools list excludes write tools (ideation)

#211 AC is sound per corrected model (#213). Proceed to architect gate.

[[2026-04-03]] Fri 01:33
## Architecture Review
**Verdict:** Approve
**DR Verification:** N/A (T1 autonomous, decision made upstream in #86 parent research)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| PreToolUse hook in reviewer frontmatter | Clear: type: command, command: path | Kept |
| deny-writes.ps1 with 5 write tools | Expanded from 3 to 5 (added create_directory, apply_patch) to match test coverage | Refined |
| permissionDecision: deny on match | Clear: hookSpecificOutput contract well-defined | Kept |
| Empty JSON on non-match/malformed | Added malformed input handling requirement | Refined |
| chat.useCustomAgentHooks prerequisite | Already enabled at .vscode/settings.json:69, updated to verify-only | Refined |
| No tools: conflict | Reviewer tools list confirmed read-only (no write tools) | Verified |
| Valid YAML after hook addition | Clear pass/fail | Kept |

### Architecture Notes
- No existing hooks in any agent files (clean slate confirmed via grep)
- scripts/hooks/ directory exists but is empty (stop-commit-guard.ps1 from #209 was removed)
- PowerShell command-execution model (type: command) is correct per VS Code hooks API
- permissionDecision: deny is platform-level enforcement (control plane), stronger than tools: restriction (configuration plane)
- Terminal bypass is a known, documented limitation (reviewer needs run_in_terminal for pytest/ruff); cannot be mitigated without crippling core review function
- Pattern: stdin JSON with tool_name, stdout JSON with hookSpecificOutput follows VS Code hooks spec
- Single ~20 LOC script, low implementation and maintenance cost
- Existing test file: tests/test_deny_writes_hook_211.py with 17+ test cases covering all AC lines

### Changes Made
- Rewrote AC: expanded write tools from 3 to 5, clarified prerequisite as verify-only, added malformed input handling
- Removed outdated #209 dependency text, added dependency resolution note
- Removed duplicate Research section (was duplicated verbatim in body)
- Fixed tag: phase-1 corrected to phase-2 (matching task title)
- Moved to todo

### Dependencies
- #209: dependency resolved (setting already enabled; PreToolUse mechanism independent of Stop hooks)
- #548: soft dependency (subagent routing verification), blocked on user action. Not gating.
- #561: blocked as duplicate of archived #533 (static write-tool test already exists)

### Challenge Results
- Challenger: reconsider
- Confidence in original: .55
- Key challenges: C1 (unverified tool names for 2 of 5), C3 (AC must be written to body), C4 (subagent routing unverified), C5 (#209 reinterpretation undocumented), C6 (duplicate Research), C7 (phase tag mismatch)
- Architect response: accepted C1 partially (kept 5 tools, risk is asymmetric: missing a name = harmless pass-through), accepted C3 (rewrote body), overrode C4 (cost/benefit favors proceeding: ~20 LOC vs indefinite wait on blocked spike), accepted C5 (documented reinterpretation), accepted C6 (removed duplicate), accepted C7 (fixed tag)

## Test-Writer Notes
- Test file: tests/test_deny_writes_hook_211.py (pre-committed by prior test-writer run; RED verified in this pass)
- Classes: TestFromAC_ScriptExists, TestFromAC_DenyWritesBehavior, TestFromAC_ReviewerAgentHooks
- Tests per category: happy 12, edge 6, error 0, boundary 6
- Total: 24 tests, all FAIL
- ruff: clean
- AC coverage: AC1a, AC1b, AC1c, AC1d, AC2a, AC2b, AC2c, AC2d, AC2e, AC2f, AC2g, AC3a, AC3b, AC4a, AC4b, AC4c, AC6, AC7 — all lines covered

[[2026-04-03]] Fri 05:23
## Builder Notes
- Files changed: agents/reviewer.agent.md, scripts/hooks/deny-writes.ps1
- Tests: 24 passed (all TestFromAC_* classes green)
- Coverage: N/A (no Python code; PS1 script + YAML frontmatter only)
- Lint: ruff clean on test file
- Evidence: 24 passed in 13.54s
- Fixes applied: Used [Console]::In.ReadToEnd() instead of pipeline input variable (blocked stdin from subprocess)

[[2026-04-03]] Fri 06:27
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Added 'behavioral hooks' to .agent.md surface description; added hooks/ to scripts/ dir listing |
| 2 | Docstrings | No | N/A | No Python modules created or modified (PS1 script + YAML frontmatter only) |
| 3 | docs/sources/overview.md | No | Pass | Task #211 section already present with VS Code Hooks docs entries from research phase |
| 4 | README.md | No | N/A | No CLI commands added |
| 5 | Research docs | Yes | Pass | docs/research/pretooluse-read-only-guard-feasibility.md exists and is linked in task body |

### Files Updated
- .github/copilot-instructions.md (Command Surface Selection .agent.md entry + scripts/ dir listing)

### Scratch Files Cleaned
- None found (docs/scratch/211-* does not exist)

[[2026-04-03]] Fri 06:42
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: PreToolUse hook in reviewer frontmatter | reviewer.agent.md L12-14: hooks/PreToolUse/type:command/deny-writes.ps1 | PASS |
| AC2: deny-writes.ps1 filters 5 write tools | Script exists, 33 LOC, filters create_file, replace_string_in_file, multi_replace_string_in_file, apply_patch, create_directory | PASS |
| AC3: permissionDecision=deny on match | Script L24-30: hookSpecificOutput.permissionDecision=deny with reason | PASS |
| AC4: Empty JSON on non-match/malformed | Script L8-10 catches parse errors, L32 returns {} for non-write tools | PASS |
| AC5: chat.useCustomAgentHooks enabled | .vscode/settings.json:69 confirmed | PASS |
| AC6: No tools: conflict | Reviewer tools list has no write tools (verified by test AC6) | PASS |
| AC7: Valid YAML after hook | 24/24 tests pass including YAML parse and duplicate-key checks | PASS |

### Test Results
- pytest: 3168 passed, 233 failed (all failures unrelated to #211), 24/24 task-specific tests pass
- ruff: clean on task files (3 violations in unrelated files)

### Upstream Commits
- 0666e34 test: add failing tests for deny-writes hook (#211, test-writer)
- 8c8dbce feat: add preToolUse read-only guard hook to reviewer agent (#211, builder)
- 7b0a655 docs: update agent surface description and scripts layout for hooks (#211, writer)

### Architect Quality: 4/5
AC was specific and refined (3 to 5 write tools, malformed input handling added). Builder followed direction smoothly. Minor: no explicit encoding/line-ending spec (trivial).

### Deduction breakdown
- -.02 missing reviewer evidence section in task body (Review Evidence section absent)

### Confidence: .98
### Action: archive
