---
id: 589
title: Add PreToolUse path guard hook to test-writer agent (Phase 3)
status: archived
priority: medium
created: 2026-04-04 07:55:54.280674+02:00
updated: 2026-04-05 19:04:51.379219+02:00
started: 2026-04-05 19:04:51.379219+02:00
completed: 2026-04-05 19:04:51.379219+02:00
tags:
- scope:agents
- hooks
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Context
See docs/research/agent-scoped-hooks.md §3.3 for boundary enforcement analysis.
Phase 3 of VS Code agent-scoped hooks adoption. The test-writer's most common boundary violation is writing source code in `packages/` instead of limiting writes to `tests/`.

## Acceptance Criteria
1. Create `scripts/hooks/deny-src-writes.ps1` — PreToolUse hook that normalizes `\` to `/` in extracted paths, then extracts file paths from `tool_input.filePath`, `tool_input.dirPath`, and `tool_input.replacements[*].filePath`; denies when ANY extracted path does not start with `tests/` (allow-list approach)
2. Write-tool gate: script checks paths only for `tool_name` in `{create_file, replace_string_in_file, multi_replace_string_in_file, create_directory}`; all other `tool_name` values return `{}`
3. Add PreToolUse hook to `test-writer.agent.md` frontmatter using same command pattern as reviewer agent (`powershell -NoProfile -NonInteractive -File scripts/hooks/deny-src-writes.ps1`)
4. Remove `edit/rename` from test-writer's tools list — bypass prevention; test-writer never legitimately renames files
5. Script returns `{}` for: non-write tools (per AC2), missing/empty paths after extraction, empty/missing `tool_name`, malformed stdin JSON
6. Agent file parses as valid YAML frontmatter after both changes (hook addition + tools list edit)
7. Prerequisite: `chat.useCustomAgentHooks` already enabled (#209, archived)

## Known Limitations
- `run_in_terminal` bypasses PreToolUse hooks (terminal writes are opaque). Not addressable at hook layer.
- `apply_patch` excluded from write-tools list — `tool_input` schema unverified for path extraction. Low risk: rarely invoked by test-writer.

## Research
- Research doc: docs/research/pretooluse-test-writer-path-guard.md
- Sources: 5 studied, 5 high-relevance (all in-repo or already attributed)
- Recommendation: Allow-list approach (tests/ only) instead of deny-list (packages/). Remove edit/rename from tools list. Script extracts paths from filePath, dirPath, and replacements[].filePath. (confidence: .75)
- Follow-up tasks created: none (existing #590, #591 remain valid)
- Decision requests: none

## Challenge Results (Research Phase)
- Challenger: block (confidence in original: 0.35)
- Key challenges: rename tool bypass (C1), multi_replace nested paths (C2), dirPath vs filePath (C4), deny-list vs allow-list (C5)
- Researcher response: accepted C1/C2/C4/C5, revised AC — allow-list approach, remove rename from tools list, multi-field path extraction

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: path guard for test-writer. Tools list edit is ancillary defense for same boundary. |
| Interface clarity | PASS | Inputs (tool_input fields), outputs (deny/pass-through JSON), allow-list logic specified in AC. |
| Dependency correctness | PASS | #209 (prerequisite) archived. Phase 2 pattern (deny-writes.ps1) deployed. No runtime deps. |
| Module layering | PASS | Standalone PS1 script + agent config. No Python module imports. |
| TDD compliance | PASS | Test-writer processes at `todo`. Established pattern: test_deny_writes_hook_211.py (26 tests). |
| KISS/YAGNI | PASS | Allow-list simpler than deny-list. No hypothetical requirements. |
| Premise challenge | PASS | No existing path-scoped guard. Phase 2 only has blanket deny (reviewer). |
| Pattern consistency | PASS | Follows Phase 2: PS1 in scripts/hooks/, hook frontmatter, JSON I/O, write-tools array. |
| Security surface | PASS | Stdin JSON from VS Code (trusted). Allow-list more restrictive. Path normalization in AC. |
| Single domain | PASS | Agent configuration domain exclusively. |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| JSON parse stdin | Malformed JSON | ConvertFrom-Json error | Yes (AC5) | Pass-through (safe) |
| Path extraction | No path fields | N/A | Yes (AC5) | Pass-through (safe) |
| Path normalization | Backslash paths | N/A | Yes (AC1) | Normalized before comparison |
| Array iteration | Empty replacements | N/A | Yes (AC5) | Pass-through (no paths) |
| Unknown write tool | Not in list | N/A | Pass-through | Acceptable risk |

### Challenge Results
- Challenger: FALLBACK — no challenger subagent available in session
- Prior challenger output (research phase): block at 0.35 confidence. All concerns (C1-C5) addressed in revised AC.
- Architect response: accepted prior revisions. Added path normalization (AC1) and explicit write-tools list (AC2).

### Verdict: APPROVE (via REFINE)
### Action Taken
- Consolidated duplicate AC (original + revised) into single authoritative set
- Added path normalization requirement to AC1
- Explicit write-tools list in AC2 (removes ambiguity on "non-write tools")
- Separated known limitations into own section
- Advanced to todo

[[2026-04-04]] Sat 16:18
Architecture review complete. Refined AC: consolidated duplicate AC, added path normalization (AC1), explicit write-tools list (AC2), separated known limitations. All 10 criteria PASS. Challenger FALLBACK — prior research-phase challenger output (C1-C5) already addressed in revised AC.

[[2026-04-04]] Sat 17:03
## Test-Writer Notes
- Test file: tests/test_deny_src_writes_hook_589.py
- Classes: TestFromAC_ScriptExists, TestFromAC_PathGuardBehavior, TestFromAC_TestWriterAgentHooks
- Tests per category: happy 6, edge 8, error 5, boundary 3 + 13 structural (agent file) = 35 total
- Total: 35 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC1a (backslash normalization) | test_create_file_backslash_tests_path_is_allowed, test_create_file_backslash_packages_path_is_denied |
| AC1b/c (create_file filePath routing) | test_create_file_tests_path_is_allowed, test_create_file_packages_path_is_denied, test_create_file_src_path_is_denied |
| AC1d/e (replace_string_in_file routing) | test_replace_string_in_file_tests_path_is_allowed, test_replace_string_in_file_packages_path_is_denied |
| AC1f/g (multi_replace replacements array) | test_multi_replace_all_tests_paths_is_allowed, test_multi_replace_any_non_tests_path_is_denied |
| AC1h/i (create_directory dirPath) | test_create_directory_tests_dirpath_is_allowed, test_create_directory_packages_dirpath_is_denied |
| AC2 (write-tool gate + apply_patch excluded) | test_apply_patch_is_not_gated_and_returns_empty_json, test_run_in_terminal_returns_empty_json, test_read_file_returns_empty_json, test_unknown_tool_name_returns_empty_json |
| AC3a-d (agent hooks frontmatter) | test_frontmatter_has_hooks_section, test_frontmatter_has_pretooluse_entry, test_pretooluse_hook_type_is_command, test_pretooluse_hook_command_references_deny_src_writes |
| AC4 (edit/rename removed) | test_tools_list_does_not_contain_edit_rename |
| AC5a-e (malformed/missing input safety) | test_malformed_stdin_json_returns_empty_json, test_empty_tool_name_returns_empty_json, test_missing_tool_name_key_returns_empty_json, test_write_tool_with_no_paths_returns_empty_json, test_write_tool_with_empty_string_filepath_returns_empty_json |
| AC6 (valid YAML, no duplicates) | test_frontmatter_is_parseable_yaml_with_pretooluse_hook, test_frontmatter_no_duplicate_keys |
| Boundaries | test_path_starting_with_tests_not_tests_slash_is_denied, test_multi_replace_empty_replacements_returns_empty_json, test_deny_response_has_hook_specific_output_key, test_deny_reason_is_nonempty, test_stdout_is_always_valid_json_* |

[[2026-04-05]] Sun 01:26
## Builder Notes

### Files Changed
- `scripts/hooks/deny-src-writes.ps1` — new allow-list path guard hook
- `share/agents/test-writer.agent.md` — removed `edit/rename` from tools, added PreToolUse hook
- `.github/agents/test-writer.agent.md` — copy of modified agent at pre-migration path (tests reference `.github/agents/`; task #608 will update test paths to `share/agents/`)
- `pyproject.toml` — added `pyyaml>=6.0` to dev dependencies (required by `test_frontmatter_is_parseable_yaml_with_pretooluse_hook` which imports `yaml`)

### Test Results
35 passed, 0 failed — all `TestFromAC_*` tests pass.

### Lint
ruff: All checks passed (tests/test_deny_src_writes_hook_589.py)

### AC Evidence
| AC | Status | Evidence |
|----|--------|---------|
| AC1 | PASS | Script normalizes `\\` to `/`, extracts filePath/dirPath/replacements[*].filePath, denies outside tests/ |
| AC2 | PASS | Only create_file, replace_string_in_file, multi_replace_string_in_file, create_directory gated; apply_patch/others pass-through |
| AC3 | PASS | test-writer.agent.md has `hooks: PreToolUse: - type: command command: powershell ... deny-src-writes.ps1` |
| AC4 | PASS | `edit/rename` removed from test-writer tools list |
| AC5 | PASS | Malformed JSON/missing keys/empty paths all return `{}` |
| AC6 | PASS | YAML parses cleanly, no duplicate keys |

### Path Migration Note
Tests reference `.github/agents/test-writer.agent.md` (written before task #600 migrated agents to `share/agents/`). Created copy there to satisfy tests. Task #608 AC1 will update `_AGENT_PATH` to `share/agents/` and the `.github/agents/` copy becomes cleanup scope for #608.

### Commit
`e136832` — feat(agents): add deny-src-writes.ps1 path guard hook to test-writer (#589)
Note: commit incidentally included two pre-staged data/→store/ renames (from migration queue); unrelated to #589 functionality.

[[2026-04-05]] Sun 09:59
## Review Evidence

### Test Results
- pytest: 35 passed, 0 failed

### Lint
ruff: clean (tests/test_deny_src_writes_hook_589.py)

### Coverage
N/A — PowerShell script; coverage tooling not applicable

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1a (backslash normalization) | test_create_file_backslash_tests_path_is_allowed, test_create_file_backslash_packages_path_is_denied | Yes | COVERED |
| AC1b/c (create_file routing) | test_create_file_tests_path_is_allowed, test_create_file_packages_path_is_denied, test_create_file_src_path_is_denied | Yes | COVERED |
| AC1d/e (replace_string_in_file) | test_replace_string_in_file_tests_path_is_allowed, test_replace_string_in_file_packages_path_is_denied | Yes | COVERED |
| AC1f/g (multi_replace array) | test_multi_replace_all_tests_paths_is_allowed, test_multi_replace_any_non_tests_path_is_denied | Yes | COVERED |
| AC1h/i (create_directory dirPath) | test_create_directory_tests_dirpath_is_allowed, test_create_directory_packages_dirpath_is_denied | Yes | COVERED |
| AC2 (write-tool gate) | test_apply_patch_is_not_gated_and_returns_empty_json, test_run_in_terminal_returns_empty_json, test_read_file_returns_empty_json, test_unknown_tool_name_returns_empty_json | Yes | COVERED |
| AC3a-d (agent hooks frontmatter) | test_frontmatter_has_hooks_section, test_frontmatter_has_pretooluse_entry, test_pretooluse_hook_type_is_command, test_pretooluse_hook_command_references_deny_src_writes | Yes | COVERED |
| AC4 (edit/rename removed) | test_tools_list_does_not_contain_edit_rename | Yes | COVERED |
| AC5a-e (error safety) | test_malformed_stdin_json_returns_empty_json, test_empty_tool_name_returns_empty_json, test_missing_tool_name_key_returns_empty_json, test_write_tool_with_no_paths_returns_empty_json, test_write_tool_with_empty_string_filepath_returns_empty_json | Yes | COVERED |
| AC6 (valid YAML) | test_frontmatter_is_parseable_yaml_with_pretooluse_hook, test_frontmatter_no_duplicate_keys | Yes | COVERED |

#### Security Review — VIOLATION FOUND (OWASP A01: Broken Access Control)

**File:** `.owlbear/hooks/deny-src-writes.ps1`, allow-list check line:
```powershell
$isInTests = $normalized.StartsWith('tests/') -or ($normalized -match '/tests/')
```

The `-or ($normalized -match '/tests/')` OR clause creates a bypass in the security guard it is meant to enforce. Any path with `/tests/` appearing as a non-root segment passes as "allowed":
- `packages/tests/evil.py` → matches `/tests/` → **incorrectly allowed** — guard defeated
- `src/lib/tests/backdoor.py` → matches `/tests/` → **incorrectly allowed**

AC1 states: "denies when ANY extracted path does not start with `tests/`". The second OR clause directly contradicts this requirement. The correct check is `$normalized.StartsWith('tests/')` exclusively.

No test exercises this bypass path. `test_path_starting_with_tests_not_tests_slash_is_denied` tests `testscripts/foo.py` (no `/tests/` component) — does not catch this.

#### Test Integrity — TestFromAC Comparison
All TestFromAC_* classes preserved. No tests weakened or removed. PASS.

#### Test Quality
- Assertion specificity: STRONG — precise equality (`== {}`) for allow; `_is_denied()` checks exact `hookSpecificOutput.permissionDecision == "deny"` for deny.
- Negative/error-path coverage: STRONG — 8 edge + 5 error cases.
- Mutation sensitivity: STRONG for existing tests. **GAP:** no test for `packages/tests/evil.py` pattern — mutating the `/tests/` OR clause would not be caught.
- Test independence: STRONG.
- Naming: STRONG.

#### Data Safety
No shared state, no async, no LLM output. PASS.

#### Implementation-Aware Test Gap
One untested code path in the allow-list logic: the `-or ($normalized -match '/tests/')` branch is only reachable by paths that do NOT start with `tests/` but do contain `/tests/`. No test exercises this branch. The gap is consequential — it is the exact security bypass.

### Deductions
- Security: broken access control (allow-list bypass via `/tests/` OR clause): −0.20

**Confidence: 0.80 → FAIL**

### Fix Instructions for Builder
In `.owlbear/hooks/deny-src-writes.ps1`, replace the allow-list check:
```powershell
# WRONG — second clause bypasses the allow-list
$isInTests = $normalized.StartsWith('tests/') -or ($normalized -match '/tests/')

# CORRECT — allow-list requires prefix only
$isInTests = $normalized.StartsWith('tests/')
```
Remove the `-or ($normalized -match '/tests/')` clause entirely. After fixing, verify that `packages/tests/evil.py` is correctly denied.

[[2026-04-05]] Sun 11:24
## Builder Notes (Review Fix Pass)

### Security Fix Applied
Removed broken access control bypass from `.owlbear/hooks/deny-src-writes.ps1`:
```powershell
# BEFORE (insecure — packages/tests/evil.py bypassed guard)
$isInTests = $normalized.StartsWith('tests/') -or ($normalized -match '/tests/')

# AFTER (correct — prefix-only allow-list)
$isInTests = $normalized.StartsWith('tests/')
```

### Builder-Discovered Tests Added
`TestBuilderDiscovered` class (2 tests) in `tests/test_deny_src_writes_hook_589.py`:
- `test_packages_tests_subdir_path_is_denied` — `packages/tests/evil.py` must be denied
- `test_src_lib_tests_subdir_path_is_denied` — `src/lib/tests/backdoor.py` must be denied

Both were verified RED against the pre-fix script (old OR clause allowed them), now GREEN.

### Test Results
37 passed (35 original TestFromAC_* + 2 TestBuilderDiscovered), 0 failed

### Lint
ruff: clean (tests/test_deny_src_writes_hook_589.py)

### Commit
`cda615a` — fix(agents): remove /tests/ OR bypass from deny-src-writes.ps1 allow-list (#589)

[[2026-04-05]] Sun 13:20
## Review Evidence

### Test Results
pytest: **37 passed, 0 failed** (verified independently)

### Lint
ruff: **clean** — `tests/test_deny_src_writes_hook_589.py` ✅

### Coverage
N/A — PowerShell script; Python coverage tooling not applicable.

### Pass 2 — AC Compliance Table

| AC Line | Mapped Test(s) | Would Fail If Violated? | Verdict |
|---------|---------------|------------------------|---------|
| AC1a (backslash normalization) | test_create_file_backslash_tests_path_is_allowed, test_create_file_backslash_packages_path_is_denied | Yes | COVERED |
| AC1b/c (create_file routing) | test_create_file_tests_path_is_allowed, test_create_file_packages_path_is_denied, test_create_file_src_path_is_denied | Yes | COVERED |
| AC1d/e (replace_string_in_file) | test_replace_string_in_file_tests_path_is_allowed, test_replace_string_in_file_packages_path_is_denied | Yes | COVERED |
| AC1f/g (multi_replace array) | test_multi_replace_all_tests_paths_is_allowed, test_multi_replace_any_non_tests_path_is_denied | Yes | COVERED |
| AC1h/i (create_directory dirPath) | test_create_directory_tests_dirpath_is_allowed, test_create_directory_packages_dirpath_is_denied | Yes | COVERED |
| AC2 (write-tool gate) | test_apply_patch_is_not_gated_and_returns_empty_json, test_run_in_terminal_returns_empty_json, test_read_file_returns_empty_json, test_unknown_tool_name_returns_empty_json | Yes | COVERED |
| AC3a-d (agent hooks frontmatter) | test_frontmatter_has_hooks_section, test_frontmatter_has_pretooluse_entry, test_pretooluse_hook_type_is_command, test_pretooluse_hook_command_references_deny_src_writes | Yes | COVERED |
| AC4 (edit/rename removed) | test_tools_list_does_not_contain_edit_rename | Yes | COVERED |
| AC5a-e (error safety) | test_malformed_stdin_json_returns_empty_json, test_empty_tool_name_returns_empty_json, test_missing_tool_name_key_returns_empty_json, test_write_tool_with_no_paths_returns_empty_json, test_write_tool_with_empty_string_filepath_returns_empty_json | Yes | COVERED |
| AC6 (valid YAML) | test_frontmatter_is_parseable_yaml_with_pretooluse_hook, test_frontmatter_no_duplicate_keys | Yes | COVERED |

### Pass 1 Security Fix Verification

**Fix examined** in `.owlbear/hooks/deny-src-writes.ps1`:
```powershell
# AFTER (correct — prefix-only allow-list)
$isInTests = $normalized.StartsWith('tests/')
```
The `-or ($normalized -match '/tests/')` bypass clause is **gone**. Fix is correct.

**TestBuilderDiscovered coverage** — class preserved and both tests pass:
- `test_packages_tests_subdir_path_is_denied` — `packages/tests/evil.py` → denied ✅
- `test_src_lib_tests_subdir_path_is_denied` — `src/lib/tests/backdoor.py` → denied ✅

Both tests use `_is_denied()` helper asserting `permissionDecision == "deny"` — assertion specificity is STRONG, would catch if the bypass were re-introduced.

### TestFromAC Integrity
All 35 original `TestFromAC_*` tests preserved — none removed or weakened. TestBuilderDiscovered (2 tests) added as net-new coverage for the security fix. Total: 37 tests. PASS.

### Commit Scope Review
- `cda615a` (fix commit): clean — `.owlbear/hooks/deny-src-writes.ps1` (1-line removal) + `tests/test_deny_src_writes_hook_589.py` (TestBuilderDiscovered class, 37 lines). No scope creep.
- **AC path deviation noted**: AC1 specifies `scripts/hooks/deny-src-writes.ps1` but file lives at `.owlbear/hooks/deny-src-writes.ps1`. Fully explained by git history: commit `bbba9e5` (#609 post-migration cleanup) renamed `{scripts => .owlbear}/hooks/deny-src-writes.ps1` after the build commit. Test paths were updated by commit `46a8f1d`. The hook command in `test-writer.agent.md` points to `.owlbear/hooks/deny-src-writes.ps1`. Implementation, test paths, and hook command are all self-consistent. Not a violation.

### Deductions
None. Security bypass from Pass 1 correctly fixed. Fix is minimal, narrowly scoped, and backed by two mutation-sensitive tests.

**Confidence: .96 → PASS**

[[2026-04-05]] Sun 14:32
## Docs Gate

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|---------|
| 1 | Behavior/API change → copilot-instructions.md | Applies | No update needed | `.github/copilot-instructions.md` is a 5-line project-identity stub; no agent catalog or hooks table exists to update |
| 2 | Module docstrings | N/A | — | No Python modules created or modified; only `.ps1`, `.md`, `pyproject.toml` touched |
| 3 | External attribution | Applies | Already attributed | VS Code hooks docs URL already in `.owlbear/sources/overview.md` line 55 (under Task #37 section). Task body confirms all 5 sources in-repo or already attributed |
| 4 | CLI changes | N/A | — | No CLI commands added or modified |
| 5 | Research doc | Applies | Verified | `.owlbear/research/pretooluse-test-writer-path-guard.md` exists. Follow-ups: none declared (existing #590, #591 noted as valid) |
| 6 | No impact | — | — | Items 1 and 3 applied but required no changes |

**Files updated:** none
**Scratch files cleaned:** none found (`589-*` search returned empty)
**Commit required:** no (no doc files changed)

[[2026-04-05]] Sun 19:04
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 (path normalization + extraction + allow-list) | deny-src-writes.ps1:L57 `$normalized.StartsWith('tests/')`, backslash normalize at L56; 37 tests pass | PASS |
| AC2 (write-tool gate) | deny-src-writes.ps1:L16-21 `$write_tools` array; apply_patch/run_in_terminal/read_file/unknown all return `{}` | PASS |
| AC3 (PreToolUse hook in frontmatter) | share/agents/test-writer.agent.md:L11-14 hooks: PreToolUse: command: powershell ... deny-src-writes.ps1 | PASS |
| AC4 (edit/rename removed) | share/agents/test-writer.agent.md:L9 tools list — no edit/rename present | PASS |
| AC5 (safety pass-through) | deny-src-writes.ps1:L8-11 try/catch, L24 empty tool_name, L50 empty paths; 5 error tests pass | PASS |
| AC6 (valid YAML) | test_frontmatter_is_parseable_yaml + test_frontmatter_no_duplicate_keys both PASS | PASS |
| AC7 (prerequisite) | N/A — #209 archived, pre-condition | PASS |

### Test Results
- pytest (task-scoped): 37 passed, 0 failed
- pytest (full suite): 2919 passed, 430 failed, 8 skipped — 0 failures in #589 scope
- ruff: clean

### Commits Verified
- e46f121 test: add failing tests (#589, test-writer)
- e136832 feat(agents): add deny-src-writes.ps1 path guard hook (#589)
- cda615a fix(agents): remove /tests/ OR bypass (#589)

### Architect Quality: 4/5
AC well-specified after research challenge. Minor gap (packages/tests/ bypass) caught by reviewer, fixed by builder.

### Deduction Breakdown
- AC lines without evidence: 0
- Lint violations: 0
- AC quality 4/5: no deduction
- Reviewer evidence: present and detailed
- Full-suite failures in task scope: 0

### Confidence: .98
### Action: archive
