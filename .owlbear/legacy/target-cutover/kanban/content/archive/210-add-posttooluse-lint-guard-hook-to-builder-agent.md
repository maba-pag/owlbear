---
id: 210
title: Add postToolUse lint guard hook to builder agent (Phase 2)
status: archived
priority: medium
created: 2026-03-30 08:52:17.140436+02:00
updated: 2026-04-04 06:38:56.786147+02:00
started: 2026-04-04 06:38:09.117674+02:00
completed: 2026-04-04 06:38:09.117674+02:00
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

See docs/research/agent-scoped-hooks-pipeline-enforcement.md section 4 (Candidate 1) and section 6 for full guidance.
See docs/research/hook-ac-command-execution-model.md for the AC correction rationale (#213).
See docs/research/posttooluse-lint-guard-feasibility.md for feasibility analysis and empirical update (section 6).

Add a PostToolUse lint guard hook to builder.agent.md that fires after file edits and runs ruff automatically. Uses the command-execution model (type: command) with systemMessage as the user-facing output channel. Model-facing additionalContext is handled by follow-up #547. apply_patch tool_name support is handled by follow-up #546.

## Acceptance Criteria

- [ ] Add PostToolUse hook to agents/builder.agent.md frontmatter: type: command, command: key pointing to scripts/hooks/lint-changed.ps1
- [ ] Create scripts/hooks/lint-changed.ps1 that reads stdin JSON and extracts tool_name
- [ ] Script runs ruff only for file-edit tool_names: create_file, replace_string_in_file, multi_replace_string_in_file
- [ ] On lint errors: returns JSON with systemMessage containing ruff output (non-blocking design; script must never exit with code 2)
- [ ] On non-edit tools or clean lint: returns empty JSON {}
- [ ] All script output must be valid JSON (no plain text, no partial output)
- [ ] chat.useCustomAgentHooks: true already present at .vscode/settings.json (no action needed)
- [ ] No duplicate YAML keys in builder.agent.md frontmatter; file parses as valid YAML

[[2026-04-02]] Thu 23:29
## Architecture Review
**Verdict:** Approve
**DR Verification:** N/A -- not research-driven. Parent research #86 produced phased rollout plan; this is a T1 implementation task.

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| PostToolUse hook in frontmatter | Clear, verifiable; type: command + script path | Kept |
| Create lint-changed.ps1 | Deliverable; testable via subprocess | Kept |
| Filter on 3 edit tool_names | Precise list matching VS Code tool names; apply_patch deferred to #546 | Tightened (removed stale exit code 2 option) |
| systemMessage with ruff output | User-facing output; model-facing additionalContext is #547 scope | Tightened (non-blocking constraint explicit) |
| Non-edit/clean returns {} | Verifiable via test | Kept |
| Valid JSON output | Verifiable via test | Added (was implicit) |
| useCustomAgentHooks present | Already at settings.json line 70; no action needed | Simplified (removed stale #209 reference) |
| No duplicate keys, valid YAML | Verifiable via test | Consolidated (was 2 lines) |

### Architecture Notes
- builder.agent.md has no hooks: section (clean addition, no conflict risk)
- scripts/hooks/ directory exists but is empty (first hook script in project)
- Follows VS Code command-execution hook model (3/25/2026 spec)
- Non-blocking design: systemMessage only, no exit code 2 (tests enforce this)
- apply_patch deferred to #546 (tool_input format unknown per docs/research/apply-patch-lint-guard-filter.md)
- additionalContext deferred to #547 (already at todo, depends on #210)
- Security: script reads stdin JSON from VS Code hook context (trusted), runs ruff on file paths (no user-input boundary)
- Note: phase-1 tag is stale (this was Phase 2 of hooks rollout; Phase 1 was invalidated). Tag editing not supported by kanban-md; planner should clean up.

### Changes Made
- Rewrote AC body: removed stale exit code 2 option (AC3), stale #209 prerequisite text (AC5), stale Phase 1 Stop hook reference (AC6)
- Added explicit valid-JSON criterion, consolidated YAML validation lines
- Updated context section with feasibility and empirical research references

### Dependencies
- No blockers (depends_on empty; #375 already cleared #209 dependency)
- #546 (apply_patch filter) depends on #210: correct ordering
- #547 (additionalContext output) depends on #210: correct ordering
- #548 (exit code 2 -File verification) is informational, not blocking

### Challenge Results
- Challenger: block (.35 confidence in original)
- Key challenges: C1 (AC not yet written), C2 (test-AC mismatch if switching to additionalContext), C5 (scope collision with #547), C6 (apply_patch format unknown)
- Architect response:
  - C1 ACCEPTED: AC written to body before approval (standard workflow)
  - C2 ACCEPTED: kept systemMessage design (existing tests remain valid)
  - C3 ACCEPTED: stale #209 reference cleaned up
  - C4 MOOT: not switching to additionalContext
  - C5 ACCEPTED: keeping systemMessage, #547 adds additionalContext later
  - C6 ACCEPTED: apply_patch stays in #546
  - Alternative angle ADOPTED: ship original systemMessage scope, iterate via #546/#547
- Confidence in original (revised): .85

[[2026-04-03]] Fri 19:48
## Builder Notes
- Files changed: agents/builder.agent.md (hooks: PostToolUse added), scripts/hooks/lint-changed.ps1 (new)
- Tests: 22 passed, ruff clean
- Evidence: all TestFromAC_* GREEN -- AC1a/b, AC2, AC3a-f, AC5, AC6a-d, AC7, AC8a-c, AC9, AC10
- Fixes: pre-filter with Test-Path for missing files (AC5); --ignore INP001 for temp file false positive

[[2026-04-03]] Fri 20:00
## Review Evidence

### Test Results
- pytest: 22 passed, 0 failed (tests/test_lint_guard_hook_210.py)

### Lint
- ruff: All checks passed! (scripts/hooks/ + test file)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1a: lint-changed.ps1 exists | TestFromAC_ScriptExists::test_lint_changed_ps1_exists | Yes — asserts exists() | COVERED |
| AC1b: script is non-empty | TestFromAC_ScriptExists::test_script_is_nonempty | Yes — asserts stat().st_size > 0 | COVERED |
| AC2: non-edit tools return {} | 3 tests (read_file, semantic_search, unknown) | Yes — asserts output == {} | COVERED |
| AC3a-f: edit tools behavior (lint/clean) | 6 tests cover all 3 tool_names x 2 states | Yes — asserts systemMessage or {} | COVERED |
| AC5: nonexistent file returns {} | test_ruff_failure_nonexistent_file_returns_empty_json | Yes — asserts output == {} | COVERED |
| AC6a-c: exit code never 2 | 3 tests (clean/lint/non-edit) | Yes — asserts code != 2 | COVERED |
| AC6d: all output valid JSON | test_output_is_always_valid_json | Yes — json.loads() must not raise | COVERED |
| AC7: hooks: in builder.agent.md | test_frontmatter-has_hooks_section | Yes — regex on frontmatter | COVERED |
| AC8a: PostToolUse entry | test_frontmatter-has_posttooluse_entry | Yes — asserts "PostToolUse" in fm | COVERED |
| AC8b: type: command | test_posttooluse_hook_type_is_command | Yes — regex r"type:\s*command" | COVERED |
| AC8c: command references lint-changed.ps1 | test_posttooluse_hook_command_references_lint_changed | Yes — asserts "lint-changed.ps1" in fm | COVERED |
| AC9: no duplicate YAML keys | test_frontmatter-no_duplicate_keys | Yes — tracks seen keys | COVERED |
| AC10: valid YAML | test_frontmatter-is_parseable_yaml_with-posttooluse_hook | Yes — yaml.safe_load must not raise | COVERED |
| AC-settings: useCustomAgentHooks present | Verified: .vscode/settings.json L69 | N/A (no-action AC) | COVERED |

No MISSING, no LAX entries.

#### Security Review
- No hardcoded secrets. Script reads VS Code hook stdin (trusted input).
- File paths come from VS Code tool_input passed as array args to ruff (not shell string) — no injection risk.
- Test-Path guard prevents processing of non-existent paths.
- No new Python dependencies.
- Script exits 0 in all paths (non-blocking). Clean.

#### Test Integrity — TestFromAC Comparison
Builder files: agents/builder.agent.md (+hooks section), scripts/hooks/lint-changed.ps1 (new).
Test file NOT modified by builder (verified via git log). All TestFromAC_* classes: PRESERVED.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | output == {} exact check; exit code != 2; systemMessage non-empty check |
| Negative/error-path coverage | STRONG | AC5 (nonexistent file), AC6 (never exit 2), AC2 (non-edit tools) |
| Mutation reasoning | STRONG | Remove Test-Path or add exit 2 path — AC5, AC6a-c fail immediately |
| Test independence | STRONG | Each test uses tmp_path; no shared mutable state |
| Descriptive names | STRONG | All names describe scenario and expected outcome |

#### Data Safety
No LLM output, no races, no multi-step operations, no unbounded input. Clean.

#### Implementation-Aware Gaps
Minor defensive paths not explicitly tested: malformed JSON input, empty filePath. Both indirectly covered by AC6d and AC6a-c. Not significant gaps.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Commit attribution gap: lint-changed.ps1 and builder.agent.md hooks section are in commit 522d3c4 labeled "test: add failing tests for quality-runner wiring (#264, test-writer)". No feat: (#210, builder) commit exists. Deliverables ARE present and tested — mislabeled commit, not a missing artifact. Auditor should handle per pipeline commit-leftovers protocol.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| PostToolUse hook in builder.agent.md | agents/builder.agent.md L11-14: hooks: PostToolUse type:command powershell ... lint-changed.ps1 | AC7, AC8a-c tests PASS | PASS |
| Create scripts/hooks/lint-changed.ps1 | File exists (78 lines), reads stdin via [Console]::In.ReadToEnd() | TestFromAC_ScriptExists PASS | PASS |
| Filter on 3 edit tool_names | L15-19: edit_tools array with 3 names | AC3a-f tests PASS | PASS |
| systemMessage with ruff output, exit!=2 | L55-62: ruff_exit==1 path produces systemMessage; L65: exit 0 | AC3a,c,e + AC6a-c tests PASS | PASS |
| Non-edit/clean returns {} | Multiple {} return paths in script | AC2, AC3b,d,f, AC5 tests PASS | PASS |
| All output valid JSON | exit 0 all paths, ConvertTo-Json or literal {} | AC6d test PASS | PASS |
| useCustomAgentHooks present | .vscode/settings.json L69: "chat.useCustomAgentHooks": true | Verified via grep | PASS |
| No duplicate keys, valid YAML | No duplicates found; yaml.safe_load succeeds | AC9, AC10 tests PASS | PASS |

### Confidence: .97
### Verdict: PASS

[[2026-04-04]] Sat 02:50
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | builder.agent.md gained PostToolUse hook (agent-level impl detail). copilot-instructions.md scripts/ row already reads `Setup, validation, hooks` -- no system-convention update needed. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Changed files: agents/builder.agent.md, scripts/hooks/lint-changed.ps1 (PowerShell). |
| 3 | External attribution | Yes | Verified | docs/sources/overview.md L3536 has ## PostToolUse Lint Guard Feasibility (Task #210) entry with VS Code Hooks docs attribution. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | All three referenced research docs exist and are linked in task body: agent-scoped-hooks-pipeline-enforcement.md, hook-ac-command-execution-model.md, posttooluse-lint-guard-feasibility.md. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/210-* files found)

[[2026-04-04]] Sat 06:37
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| PostToolUse hook in builder.agent.md | builder.agent.md L11-14: hooks PostToolUse type:command lint-changed.ps1 | PASS |
| Create scripts/hooks/lint-changed.ps1 | File exists (78 lines), reads stdin JSON | PASS |
| Filter on 3 edit tool_names | lint-changed.ps1 L15-19: edit_tools array with 3 names | PASS |
| systemMessage with ruff output, never exit 2 | lint-changed.ps1 L72-75: systemMessage path; L78: exit 0 always | PASS |
| Non-edit/clean returns {} | Multiple {} return paths verified in script | PASS |
| All output valid JSON | Every path outputs {} or ConvertTo-Json | PASS |
| useCustomAgentHooks present | .vscode/settings.json L60 confirmed | PASS |
| No duplicate keys, valid YAML | Frontmatter clean; AC9/AC10 tests pass | PASS |

### Test Results
- pytest (task): 22 passed, 0 failed
- pytest (full suite): 2790 passed, 315 failed, 8 skipped. Zero failures in task scope. All 315 failures are pre-existing from other tasks.
- ruff: All checks passed (scripts/hooks/ + test file)

### Architect Quality: 4/5
AC lines were specific, testable, and well-scoped. Architect cleaned up stale references, tightened criteria, and incorporated challenger feedback. Minor builder discoveries (Test-Path guard, INP001 ignore) are reasonable implementation details, not AC failures. Dependency chain with #546/#547 is clean.

### Reviewer Evidence
Present, thorough, PASS verdict (.97). Full AC coverage table, security review, test integrity, and process quality. Noted commit attribution gap (deliverables in 522d3c4 labeled #264). Trusted for code-level findings.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 8 verified) = no deduction
- Lint violations: 0 = no deduction
- AC quality score 4 (> 3) = no deduction
- Reviewer evidence section: present and detailed = no deduction
- Full-suite task-scope failures: 0 = no deduction
- Note: commit attribution gap (builder deliverables in #264 commit) is process note, not in rubric

### Confidence: 1.00
### Action: archive


## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4df8594 | chore | kanban/activity.jsonl, kanban/tasks/210-*.md | #210 |
