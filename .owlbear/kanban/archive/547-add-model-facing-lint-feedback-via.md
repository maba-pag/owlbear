---
id: 547
title: Add model-facing lint feedback via additionalContext to builder 
  PostToolUse hook
status: archived
priority: medium
created: 2026-04-02 14:52:03.192269+02:00
updated: 2026-04-04 20:33:30.685167+02:00
started: 2026-04-04 20:33:02.909974+02:00
completed: 2026-04-04 20:33:02.909974+02:00
tags:
- scope:agents
- hooks
- type:build
depends_on:
- 210
class: standard
archival_reason: completed
archival_refs: []
---

## Context
See docs/research/posttooluse-additionalcontext-lint-feedback.md (task #547).
Empirical verification (#532) confirmed PostToolUse additionalContext reaches the subagent model context (wrapped in PostToolUse-context XML tags). The builder's lint guard (#210) uses systemMessage (user-facing only). This task adds additionalContext output so the builder model receives lint feedback and can self-correct.

## Acceptance Criteria
- [ ] When ruff finds errors, lint-changed.ps1 returns JSON with both `systemMessage` (existing) and `hookSpecificOutput` containing `hookEventName: PostToolUse` and `additionalContext` with the ruff output text
- [ ] Output JSON structure: `{ systemMessage: <ruff>, hookSpecificOutput: { hookEventName: PostToolUse, additionalContext: <ruff> } }`
- [ ] When ruff finds no errors: returns empty JSON `{}` (no additionalContext for clean results)
- [ ] Existing systemMessage behavior preserved unchanged
- [ ] Never exits with code 2 (non-blocking)
- [ ] Same ruff output text used for both systemMessage and additionalContext (no separate formatting)

## Verification Note
Model-facing delivery (additionalContext appearing as `<PostToolUse-context>` tags in Chat Debug View) requires manual observation during a live builder session. This is a post-implementation verification step, not a reviewer-testable criterion. Create an action request after builder completes if manual verification is needed.

## Implementation Notes
Output JSON structure when ruff finds errors:
`{ systemMessage: ruff_output, hookSpecificOutput: { hookEventName: PostToolUse, additionalContext: ruff_output } }`
Same ruff output for both fields (KISS). No truncation initially (YAGNI).

## Dependencies
Depends on #210 (lint-changed.ps1 must exist first).

[[2026-04-02]] Thu 16:35
## Architecture Review
**Verdict:** Approve
**DR Verification:** N/A -- T1 classification (no new capability, no architecture change). Research doc classifies as autonomous.

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| hookSpecificOutput.additionalContext with ruff output | Clear deliverable, JSON structure specified | Refined (added hookEventName, JSON schema) |
| hookEventName: PostToolUse included | NEW -- required per VS Code hooks spec and #532 probe | Added |
| Clean path returns empty JSON | NEW -- explicit clean-path criterion (no noise) | Added |
| systemMessage preserved | Verifiable via script test | Kept |
| Never exits code 2 | Deliberate non-blocking design | Kept |
| Same ruff output for both fields | KISS constraint -- no dual formatting | Added |
| Chat Debug View verification | Reframed as post-impl verification note (not reviewer-testable) | Reframed |

### Architecture Notes
- Single-file change: modifies lint-changed.ps1 output format (created by #210)
- No agent file changes needed -- hook command stays the same, script changes output JSON
- additionalContext confirmed model-facing by #532 empirical verification (N=1, create_file)
- VS Code docs unambiguous on hookSpecificOutput schema
- #546 (apply_patch filter) is orthogonal: changes WHEN lint runs, not WHAT output looks like. No ordering dependency needed.
- type:build tag correct -- testable script code changes

### Changes Made
- Rewrote AC body: 4 lines expanded to 6 precise lines with JSON schema, hookEventName, clean-path criterion
- Added Verification Note section (manual Chat Debug View check is post-impl, not AC)
- Added Implementation Notes with JSON structure
- Fixed depends_on: added #210 (was missing from frontmatter)
- Merged #549 (duplicate follow-up from research doc s5) into #547. Deleted #549.

### Dependencies
- Added: depends_on #210 (lint-changed.ps1 must exist before modification)
- Verified: #210 is in-progress (not yet complete -- #547 blocked until #210 ships)
- Orthogonal: #546 (apply_patch filter) -- no ordering dependency

### Challenge Results
- Challenger: block (.45 confidence in original)
- Key challenges: C1 (duplicate #549), C2 (missing depends_on), C3 (AC2 not testable), C4 (#546 ordering), C5 (AC not written to body), C6 (N=1 basis)
- Architect response:
  - C1 ACCEPTED: #549 deleted, merged into #547 (refined AC absorbed)
  - C2 ACCEPTED: depends_on [210] added to frontmatter
  - C3 ACCEPTED partially: AC2 reframed as post-impl verification note. Remaining AC lines are mechanically testable
  - C4 REBUTTED: #546 and #547 are order-independent. #546 tests tool_name triggering + systemMessage; #547 tests output structure. systemMessage preserved by both
  - C5 ACCEPTED: Refined AC written to task body before approval
  - C6 NOTED: N=1 is documented risk (.75 confidence in research). VS Code docs are unambiguous. Not blocking
- Confidence in original (revised): .80 -- all critical structural defects fixed in this cycle

[[2026-04-04]] Fri
## Test-Writer Notes
- Test file: tests/test_lint_feedback_547.py
- Classes: TestFromAC_LintFeedbackStructure
- Tests per category: happy 3 (hookSpecificOutput key present for all 3 edit tools), edge 1 (hookEventName == PostToolUse), error 1 (additionalContext non-empty), boundary 2 (systemMessage == additionalContext; both keys present together)
- Total: 7 tests, all FAIL
- ruff: clean
- AC coverage:
  | AC | Test(s) |
  |----|---------|
  | Errors → hookSpecificOutput key present (all 3 edit tools) | test_create/replace/multi_replace_lint_errors_returns_hook_specific_output |
  | hookSpecificOutput.hookEventName == PostToolUse | test_hook_specific_output_event_name_is_post_tool_use |
  | hookSpecificOutput.additionalContext non-empty ruff output | test_hook_specific_output_additional_context_is_nonempty |
  | Same text for systemMessage and additionalContext | test_system_message_and_additional_context_are_identical |
  | systemMessage preserved alongside hookSpecificOutput | test_lint_errors_output_has_both_system_message_and_hook_specific_output |

[[2026-04-04]] Sat 17:01
## Builder Notes

**Files changed:** `scripts/hooks/lint-changed.ps1` (1 file, +9/-3 lines)

**Change:** In the `ruff_exit -eq 1` branch, replaced the single-key response `{ systemMessage = $ruff_output }` with a three-key response that adds `hookSpecificOutput` containing `hookEventName = 'PostToolUse'` and `additionalContext = $ruff_output`. Same `$ruff_output` string used for both fields (KISS). Added `-Depth 3` to `ConvertTo-Json` to serialise the nested object.

**Test results:** 7/7 passed (`TestFromAC_LintFeedbackStructure`). All tests were FAILED before the change (RED verified).

**Lint:** `ruff check tests/test_lint_feedback_547.py` — All checks passed.

**Commit:** `ee1a793` feat: add hookSpecificOutput.additionalContext to lint-changed.ps1 (#547)

**Coverage target:** Single PS1 file — no Python coverage applicable. Python test file at 100% (7 tests, all AC lines covered).

**Builder-discovered tests:** None needed — the AC was precise and fully covered by `TestFromAC_LintFeedbackStructure`.

**Manual verification note:** The `additionalContext` appearing as `<PostToolUse-context>` tags in Chat Debug View is a post-implementation verification step (per AC Verification Note). An action request can be created after reviewer approval if needed.

[[2026-04-04]] Sat 19:37
## Review Evidence

**pytest (task-specific):** 7 passed / 0 failed (`TestFromAC_LintFeedbackStructure`)  
**pytest (regression #210):** 6 passed / 0 failed — clean-path and exit-code ACs re-verified  
**ruff:** All checks passed (test file; PS1 skipped — not Python)  
**Coverage:** 100% on Python test layer; PS1 not Python-coverage-able (not applicable)  
**Builder cycle count:** 1 — CLEAN  
**TestFromAC_ modifications:** None — builder only touched `scripts/hooks/lint-changed.ps1`  
**Commit:** `ee1a793` — 1 file, +9/-3 lines, scope correct

---

### AC Compliance

| AC Line | Evidence | Mapped Test(s) | Status |
|---------|----------|----------------|--------|
| Errors → both `systemMessage` + `hookSpecificOutput` w/ `hookEventName` + `additionalContext` | `lint-changed.ps1` lines 71–80: `$response` hash with both keys | `test_lint_errors_output_has_both_system_message_and_hook_specific_output` | PASS |
| JSON structure: `{ systemMessage, hookSpecificOutput: { hookEventName: PostToolUse, additionalContext } }` | `lint-changed.ps1` lines 73–79: exact schema | `test_hook_specific_output_event_name_is_post_tool_use`, `test_hook_specific_output_additional_context_is_nonempty` | PASS |
| Clean path → `{}` (no `additionalContext`) | `lint-changed.ps1` line 83: `Write-Output '{}'` in else; `test_create/replace/multi_replace_file_clean_returns_empty_json` assert `output == {}` in #210 suite | #210 AC3b/AC3d/AC3f | PASS |
| Existing `systemMessage` preserved unchanged | `lint-changed.ps1` line 73: `systemMessage = $ruff_output` (unchanged assignment) | `test_lint_errors_output_has_both_system_message_and_hook_specific_output` | PASS |
| Never exits code 2 | `lint-changed.ps1` line 86: `exit 0`; all try/catch paths exit 0 | #210 AC6a/AC6b `test_exit_code_never_2_*` — PASS | PASS |
| Same text for both fields | `lint-changed.ps1` lines 73+78: both use `$ruff_output` | `test_system_message_and_additional_context_are_identical`: `assert system_msg == additional_context` | PASS |

### Test Quality

| Check | Rating | Notes |
|-------|--------|-------|
| Assertion specificity | ADEQUATE | `assert "hookSpecificOutput" in output`, equality checks on `hookEventName` and `additionalContext` content; truthy check on `additional_context` compensated by identity test |
| Error/negative-path coverage | STRONG | Clean path and exit-code covered by #210 regression suite; test-writer docstring notes AC5/AC10 as cross-covered |
| Mutation resistance | STRONG | Removing hookSpecificOutput key, changing hookEventName value, or splitting ruff text would each break at least one test |
| Test independence | STRONG | All tests use `tmp_path` fixtures; no shared mutable state |
| Descriptive names | STRONG | All names accurately describe scenario and expectation |

### Security: No issues. Script processes VS Code hook tokens; no user-controlled input to shell commands.

### Deductions: 0

**Confidence: .95 → PASS**

[[2026-04-04]] Sat 19:46
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Only `scripts/hooks/lint-changed.ps1` changed — this is a hook output format change at script level. `copilot-instructions.md` has no documentation of hook output schemas; only the `scripts/` directory entry (`Setup, validation, hooks`) exists. No update needed. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Change is entirely in a PowerShell (.ps1) file. |
| 3 | External attribution | Yes | Updated | Research doc Section 2 cites 2 new external sources not yet in overview.md: `claude-plugins-official #317` and `microsoft/vscode #296189`. Added new section `## PostToolUse additionalContext Lint Feedback (Task #547)` to `docs/sources/overview.md`. Commit: `57cd5c3`. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `docs/research/posttooluse-additionalcontext-lint-feedback.md` exists and is linked from task body (`See docs/research/posttooluse-additionalcontext-lint-feedback.md (task #547)`). Follow-up task (#547 itself) was created from Section 5 of the research doc — confirmed. |

### Files Updated
- `docs/sources/overview.md` — added Task #547 attribution section (2 rows)

### Scratch Files Cleaned
- None (no `docs/scratch/547-*` files found)

[[2026-04-04]] Sat 20:32
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Errors: both systemMessage + hookSpecificOutput w/ hookEventName + additionalContext | lint-changed.ps1 L71-80; tests 7/7 PASS | PASS |
| JSON structure: { systemMessage, hookSpecificOutput: { hookEventName: PostToolUse, additionalContext } } | lint-changed.ps1 L73-79; event_name + additional_context tests | PASS |
| Clean path returns empty JSON {} | lint-changed.ps1 L83; #210 regression 22/22 PASS | PASS |
| Existing systemMessage preserved unchanged | lint-changed.ps1 L73; both_system_message_and_hook test | PASS |
| Never exits code 2 | lint-changed.ps1 L86 exit 0; #210 AC6 tests PASS | PASS |
| Same ruff text for both fields | lint-changed.ps1 L73+78 both use ruff_output; identical test | PASS |

### Test Results
- pytest (task-specific): 7 passed, 0 failed
- pytest (#210 regression): 22 passed, 8 failed (all #546 RED, not #547)
- pytest (full suite): 2826 passed, 401 failed. All failures pre-existing RED tests. Zero cross-task regressions.
- ruff: All checks passed

### Architect Quality: 4/5
Original 4 vague AC lines expanded to 6 precise testable criteria. Handled challenger well. Minor gap: untestable Chat Debug View criterion reframed.

### Deduction Breakdown
- AC lines with no evidence: 0 (6/6 verified) = 0
- Lint violations: 0 = 0
- AC quality 4/5 (> 3) = 0
- Reviewer evidence: present, detailed, PASS = 0
- Full-suite failures in task scope: 0 = 0

### Confidence: .98
### Action: archive

[[2026-04-04]] Sat 20:33
6/6 AC verified with test evidence. Full suite 2826 passed, 0 regressions in scope. Confidence .98.

[[2026-04-04]] Sat 20:33
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 7cfaf53 | test | tests/test_lint_feedback_547.py | #547 |
| ee1a793 | feat | scripts/hooks/lint-changed.ps1 | #547 |
| 57cd5c3 | docs | docs/sources/overview.md | #547 |
| d7723a9 | chore | kanban board files | #547 |
