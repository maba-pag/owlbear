---
id: 921
title: Honor kanban age thresholds in bearclaw board Rich output
status: archived
priority: nice-to-have
created: 2026-03-21T16:42:56.2592789+01:00
updated: 2026-03-25T00:08:15.4770711+01:00
started: 2026-03-25T00:07:41.0080222+01:00
completed: 2026-03-25T00:07:41.0080222+01:00
tags:
    - cli
    - tooling
    - phase-14
    - type:build
    - scope:cli
depends_on:
    - 910
    - 925
class: standard
---

Research follow-up from docs/research/bearclaw-board-command-implementation-gate.md. Implement the age-threshold styling follow-on after #910 establishes the board command and #925 locks the RED contract.

AC:
(1) In src/bearclaw/commands/board.py, load tui.age_thresholds from kanban/config.yml with task-local helper logic only; do not add a shared config model or new dependency.
(2) Choose the matching threshold from the raw age duration already used for the Age column, not from the rendered age label, so sub-day thresholds such as 1h remain effective.
(3) Normalize all-digit configured colors such as 242 into a Rich-valid style string, validate the style, and apply it only to the Age cell; status order, task grouping, and the displayed age text/value remain unchanged from #910.
(4) If kanban/config.yml is missing, YAML is malformed, tui.age_thresholds is absent or not a list of {after,color} mappings, a duration cannot be parsed, or a Rich style is invalid, the command still renders the same plain unstyled Age text without raising.
(5) No new dependencies are added, implementation stays local to src/bearclaw/commands/board.py, and tests from #925 plus the existing tests/test_cli_board.py contract pass.

[[2026-03-21]] Sat 17:47

## Research

Doc: docs/research/bearclaw-board-age-threshold-styling.md

Summary: Preserve the age text introduced by #910, but decide Age-cell styling from the raw status duration so hourly tui.age_thresholds remain accurate. Current kanban/config.yml colors are numeric palette strings, so the future board renderer should normalize values like 242 to Rich color(242) styles and apply styling only to the Age cell, not the whole row. Missing or malformed threshold config, invalid durations, or invalid Rich styles should fall back to plain unstyled age text without breaking the command.

Follow-up created: #925 Test bearclaw board age-threshold styling contract (RED).

Command executed:

- kanban\kanban-md.exe create Test bearclaw board age-threshold styling contract (RED) -> #925

Attribution updated: docs/sources/overview.md

[[2026-03-21]] Sat 18:13

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | Correct direction, but it did not pin local parsing scope, raw-duration matching, or numeric color normalization. | Rewrote |
| 2 | Correct invariant, but it needed to state that only styling changes while grouping and displayed age stay the same. | Rewrote |
| 3 | Fallback path was too loose because invalid threshold shapes, duration parse failures, and invalid Rich styles were not explicit. | Rewrote |
| 4 | Mixed GREEN work with fresh test design; this task should consume the RED contract from #925 instead. | Rewrote |
| 5 | Scope was right, but task sequencing needed explicit dependencies on #910 and #925. | Rewrote |

### Architecture Notes

- Follow the #910 seam: keep helper logic local to src/bearclaw/commands/board.py and do not expand this into a shared config subsystem.
- Local YAML parsing is consistent with src/bearclaw/commands/decisions.py, while Rich table rendering should stay aligned with src/bearclaw/commands/usage.py and src/bearclaw/commands/daemon.py.
- Apply styling to the Age cell only. Row-level or column-level styling would exceed the task contract by recoloring unrelated cells.
- #921 remains a single-domain CLI display task. The explicit #910 and #925 dependencies preserve MVP -> RED -> GREEN sequencing.

### Changes Made

- Rewrote the task body as a stricter GREEN-phase contract.
- Added dependencies on #910 and #925.
- Appended this architecture review.

### Dependencies

- Added: #910, #925.
- Verified: docs/research/bearclaw-board-age-threshold-styling.md, kanban/config.yml, src/bearclaw/cli.py, src/bearclaw/commands/decisions.py, src/bearclaw/commands/usage.py, src/bearclaw/commands/daemon.py, tests/test_cli_board.py.

[[2026-03-24]] Tue 02:21

## Test-Writer Notes

- Test file: tests/test_cli_board.py

- Classes: TestFromAC_921_AgeThresholdCellScope, TestFromAC_921_FallbackMappingValidation

- Tests per category: happy 3 (cell-scope assertions), edge 3 (invariants: order/grouping/text), error 3 (malformed entries)

- Total: 9 tests, all FAIL (AssertionError on ANSI assertions) checked

- ruff: clean

- AC coverage:

| AC Line | Test(s) | Category |

|---------|---------|----------|

| AC1: load tui.age_thresholds task-local only | covered by_with_config context manager for all 9 tests | happy |

| AC2: raw ago duration drives threshold (not rendered label) | test_threshold_boundary_same_displayed_age_text_different_ansi (#925, already failing) | boundary |

| AC3: normalize numeric colors, apply only to Age cell | test_threshold_color_not_directly_preceding_title_text, test_threshold_color_not_directly_preceding_id_text, test_tags_column_data_intact_when_threshold_fires | happy |

| AC3: status order unchanged | test_status_order_preserved_while_threshold_styling_applied | edge |

| AC3: task grouping unchanged | test_task_grouping_preserved_while_threshold_styling_applied | edge |

| AC3: displayed age text unchanged | test_age_text_value_unchanged_after_stripping_ansi_sequences | edge |

| AC4: malformed mapping entries fallback | test_threshold_entry_missing_after_key_falls_back_to_plain_age, test_threshold_entry_missing_color_key_falls_back_to_plain_age, test_threshold_list_of_scalars_falls_back_to_plain_age | error |

| AC5: tests from #925 still pass | TestFromAC_AgeThresholdStyling + TestFromAC_AgeThresholdFallback already in file (11 RED tests from #925) | boundary |

[[2026-03-24]] Tue 05:31

## Builder Notes

- Files changed: src/bearclaw/commands/board.py

- RED verification: 20/20 task TestFromAC tests failed before implementation.

- Tests: 20 passed (age-threshold TestFromAC scope) and 50 passed (full tests/test_cli_board.py module).

- Coverage: src/bearclaw/commands/board.py 95% (bare --cov scoped run).

- Lint: uv run ruff check src/bearclaw/commands/board.py tests/test_cli_board.py -> All checks passed.

- Evidence: uv run pytest tests/test_cli_board.py::TestFromAC_AgeThresholdStyling tests/test_cli_board.py::TestFromAC_AgeThresholdFallback tests/test_cli_board.py::TestFromAC_921_AgeThresholdCellScope tests/test_cli_board.py::TestFromAC_921_FallbackMappingValidation -q --tb=short -> 20 passed; uv run pytest tests/test_cli_board.py -q --tb=short -> 50 passed.

- Fixes applied: Added task-local config loading + tui.age_threshold parsing, duration parsing from raw age reference timestamps, numeric color normalization to Rich style with validation, and Age-cell-only styling with safe fallback to plain text for missing/invalid config.

[[2026-03-24]] Tue 09:36

## Review Evidence

## Review: #921 — Honor kanban age thresholds in bearclaw board Rich output

### Test Results

- pytest: 50 passed, 0 failed (`uv run pytest tests/test_cli_board.py -q --tb=short`)
- warnings: 4 optional-dependency warnings from `tests/conftest.py` about missing `qdrant_client`; unrelated to board behavior

### Lint Results

- ruff: All checks passed (`uv run ruff check src/bearclaw/commands/board.py tests/test_cli_board.py`)

### Coverage

- `src/bearclaw/commands/board.py`: 95% (`uv run pytest tests/test_cli_board.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`)

### Test-Writer Coverage

| AC Line | Evidence | Would fail if AC violated? | Verdict |
| --- | --- | --- | --- |
| AC1: load `tui.age_thresholds` from config with local board helpers | `src/bearclaw/commands/board.py`: `_load_board_config` (line 30), `_read_age_thresholds` (line 103); exercised by fallback/style tests including `test_missing_config_file_exits_zero_with_plain_age_text` (line 725) | Yes for config-loading behavior; locality/no-new-dependency needs code review | COVERED |
| AC2: choose threshold from raw age duration, not rendered label | `test_threshold_boundary_same_displayed_age_text_different_ansi` (line 686); code path `_age_display_and_seconds` (line 201) -> `_age_style_for_seconds` (line 214) | Yes | COVERED |
| AC3: normalize numeric colors and apply styling only to Age cell | `_normalize_age_style` (line 82); `test_base_zero_second_tier_color_242_applied_for_fresh_task` (line 663); cell-scope tests at lines 874, 934, 989 | No for full cell exclusivity; assignee cell is not asserted anywhere | LAX |
| AC4: invalid/missing threshold config falls back to plain Age text without raising | `_read_age_thresholds` (line 103); fallback tests at lines 725, 791, 811, 1038, 1056, 1074 | Yes | COVERED |
| AC5: existing board contract still passes | `uv run pytest tests/test_cli_board.py -q --tb=short` -> 50 passed | Yes | COVERED |

### TestFromAC Comparison

- `git diff --unified=3 -- tests/test_cli_board.py` shows only formatting-only changes in the current worktree around the #921 tests (line wrapping and string-literal formatting).
- No weakened assertions, broadened exceptions, removed tests, skips, or xfails found in the task-specific `TestFromAC_AgeThresholdStyling`, `TestFromAC_AgeThresholdFallback`, `TestFromAC_921_AgeThresholdCellScope`, or `TestFromAC_921_FallbackMappingValidation` methods.
- Assessment: PRESERVED.

### Test Quality

- Assertion specificity: ADEQUATE
- Negative / error-path coverage: STRONG
- Manual mutation reasoning: WEAK
  - `TestFromAC_921_AgeThresholdCellScope` says `Title, ID, Assignee, and Tags cells must not receive the threshold color` in its docstring (line 863), but the class only negative-checks Title, ID, and Tags. No threshold test asserts that the Assignee cell remains unstyled.
  - Source renders `_assignee_display(t)` and `age_cell` as separate cells in `table.add_row` (`src/bearclaw/commands/board.py` lines 277-278). A broken implementation that styles both Assignee and Age would still satisfy the current suite.
- Test independence: STRONG
- Descriptive names: STRONG

### Security / Data Safety

- No security or data-safety findings in the local YAML parsing and Rich style-normalization path.

### AC Compliance

| AC Line | Evidence | Status |
| --- | --- | --- |
| AC1 | Local config helpers remain in `src/bearclaw/commands/board.py` at lines 30 and 103; `pyproject.toml` has no current diff, and YAML parsing is already an established project pattern (`src/bearclaw/commands/decisions.py` line 12, `src/owlbear/core/agent_def.py` line 18, `src/owlbear/skills/registry.py` line 20) | PASS |
| AC2 | `_age_display_and_seconds` (line 201) computes display + raw seconds separately; threshold boundary test at line 686 passed | PASS |
| AC3 | Current code reads thresholds at line 245 and applies style only to `age_cell` at lines 271-272, but regression coverage is insufficient because assignee-cell styling is untested | FAIL |
| AC4 | Fallback tests at lines 725, 791, 811, 1038, 1056, and 1074 passed | PASS |
| AC5 | Full board module run passed (50/50), ruff clean, board.py coverage 95% | PASS |

### Verdict

- FAIL
- Confidence: .84
- Reason: the current implementation appears correct, but the test suite does not fully enforce the core `Age cell only` contract. Missing assignee-cell negative coverage leaves a realistic regression path unguarded.

[[2026-03-24]] Tue 22:55

## Builder Notes

- Files changed: none
- RED verification: task-specific TestFromAC slices were already green on current HEAD (21 passed)
- Tests: full tests/test_cli_board.py module passed (51 passed)
- Coverage: src/bearclaw/commands/board.py measured at 95 percent in scoped coverage run
- Lint: task-scoped ruff check passed
- Evidence: task-specific slice 21 passed, module run 51 passed, board command coverage 95 percent, ruff clean
- Fixes applied: none; existing implementation already satisfied the updated assignee-cell-only guard

[[2026-03-24]] Tue 23:11

## Review Evidence

## Review: #921 — Honor kanban age thresholds in bearclaw board Rich output

### Test Results

- pytest: 51 passed, 0 failed on tests/test_cli_board.py
- Warnings: 2 optional-dependency warnings from tests/conftest.py about missing qdrant_client and 1 pytest config warning about asyncio_mode during scoped runs; unrelated to board behavior

### Lint Results

- ruff: All checks passed on src/bearclaw/commands/board.py and tests/test_cli_board.py

### Coverage

- src/bearclaw/commands/board.py: 95 percent in scoped coverage
- Tooling note: coverage in this terminal required PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 plus explicit pytest_cov; the plain coverage invocation did not load the plugin

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: load tui.age_thresholds with task-local helper logic only and no new dependency | TestFromAC_AgeThresholdFallback::test_missing_config_file_exits_zero_with_plain_age_text plus the threshold-style tests exercising config reads | Yes for config loading and fallback behavior; locality and dependency scope verified in code review at board.py lines 30 and 103 and by the builder commit touching only board.py | COVERED |
| AC2: choose threshold from raw age duration, not rendered age label | TestFromAC_AgeThresholdStyling::test_threshold_boundary_same_displayed_age_text_different_ansi | Yes; both tasks render 0d but only the older task gets the 1h tier color | COVERED |
| AC3: normalize numeric colors and style only the Age cell without changing order, grouping, or age text | TestFromAC_AgeThresholdStyling::test_base_zero_second_tier_color_242_applied_for_fresh_task, TestFromAC_AgeThresholdStyling::test_numeric_color_string_becomes_38_5_n_ansi_not_raw_config_string, TestFromAC_921_AgeThresholdCellScope::test_threshold_color_not_applied_to_assignee_cell, TestFromAC_921_AgeThresholdCellScope::test_status_order_preserved_while_threshold_styling_applied, TestFromAC_921_AgeThresholdCellScope::test_task_grouping_preserved_while_threshold_styling_applied, TestFromAC_921_AgeThresholdCellScope::test_age_text_value_unchanged_after_stripping_ansi_sequences | Yes; exact ANSI tier values are asserted and the cell-scope checks now cover title, ID, assignee, and tags | COVERED |
| AC4: missing or malformed config and invalid threshold entries fall back to plain Age text without raising | TestFromAC_AgeThresholdFallback::test_missing_config_file_exits_zero_with_plain_age_text, TestFromAC_AgeThresholdFallback::test_malformed_yaml_config_exits_zero_with_plain_age_text, TestFromAC_AgeThresholdFallback::test_tui_section_absent_plain_age_contrast_valid_config_has_ansi, TestFromAC_AgeThresholdFallback::test_age_thresholds_not_a_list_plain_age_contrast_valid_config_has_ansi, TestFromAC_AgeThresholdFallback::test_threshold_invalid_duration_plain_age_contrast_valid_config_has_ansi, TestFromAC_AgeThresholdFallback::test_threshold_invalid_color_value_plain_age_contrast_valid_config_has_ansi, TestFromAC_921_FallbackMappingValidation::test_threshold_entry_missing_after_key_falls_back_to_plain_age, TestFromAC_921_FallbackMappingValidation::test_threshold_entry_missing_color_key_falls_back_to_plain_age, TestFromAC_921_FallbackMappingValidation::test_threshold_list_of_scalars_falls_back_to_plain_age | Yes; each malformed case asserts exit 0 and absence of threshold ANSI | COVERED |
| AC5: no new dependencies, implementation stays local to board.py, and task plus existing board tests pass | Full tests/test_cli_board.py module run, task-scoped ruff, and scoped coverage; code review confirms imports remain existing yaml and Rich modules at board.py lines 13, 15, and 16 | Yes | COVERED |

#### Security Review

- No security issues found. The config path is fixed by _KANBAN_CONFIG, YAML uses yaml.safe_load, and Rich styles are validated with Style.parse before rendering.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Existing TestFromAC_921_AgeThresholdCellScope methods from the RED commit | Current working tree has only formatting compaction for the original title, ID, tags, order, grouping, and age-text checks; builder commit 7333650 touched only board.py | PRESERVED |
| TestFromAC_921_AgeThresholdCellScope::test_threshold_color_not_applied_to_assignee_cell | Added in the current working tree after the original RED commit bd60cca; the RED docstring promised Assignee coverage but did not include a concrete test method | STRENGTHENED |
| Existing TestFromAC_921_FallbackMappingValidation methods from the RED commit | Current working tree compacts a few multiline literals but keeps the assertions intact | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact ANSI tiers 242, 34, and 226 are asserted; cell-scope tests assert the styled tier is present while title, ID, assignee, and tags remain unstyled; fallback tests assert exit 0 plus plain Age output |
| Negative or error paths | STRONG | Missing file, malformed YAML, missing tui section, non-list threshold config, invalid duration, invalid Rich color, missing after, missing color, and scalar-list cases are all exercised |
| Mutation reasoning | STRONG | Manual reproduction of the rendered row showed Rich starts the threshold ANSI at the Age cell content, so the direct-precedence sentinel checks are meaningful; if styling leaks to ID, title, assignee, or tags the current tests would fail |
| Test independence | STRONG | Each test patches subprocess.run and the temporary config locally; no shared mutable state is required across tests |
| Descriptive names | STRONG | The task-specific test names describe the exact threshold or fallback scenario being verified |

#### Data Safety

- No data safety issues found. Invalid threshold config collapses to an empty threshold list instead of partial state, and the logic performs only local parsing and render-time formatting.

#### Implementation-Aware Test Gaps

- No significant untested paths. The new behavior in _read_age_thresholds,_age_display_and_seconds,_age_style_for_seconds, and the Age-cell render path is exercised across success, boundary, and fallback scenarios. The few uncovered board.py lines are defensive branches and the older_age_in_status wrapper, not gaps in the task behavior.

### Pass 2 — INFORMATIONAL

- The current workspace includes an uncommitted strengthening in tests/test_cli_board.py that adds the explicit assignee-cell guard. The committed #921 builder change itself touched only board.py, so this review applies to the current workspace state rather than commit 7333650 alone.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | _load_board_config at board.py line 30 and_read_age_thresholds at line 103 keep the config handling local to board.py; the builder commit touched only board.py and imports remain existing yaml and Rich modules | Missing-config and malformed-config fallback tests plus the positive threshold-style tests | PASS |
| AC2 | _age_display_and_seconds at line 201 separates display text from raw seconds, and _age_style_for_seconds at line 214 uses the raw seconds for threshold matching | TestFromAC_AgeThresholdStyling::test_threshold_boundary_same_displayed_age_text_different_ansi | PASS |
| AC3 | _normalize_age_style at line 82 normalizes numeric colors,_read_age_thresholds at line 103 validates them, line 272 styles only age_cell, and line 274 adds the row with_assignee_display(t) still passed separately at line 277 | Base-tier color test, numeric-color normalization test, assignee scope test, status-order test, grouping test, and age-text preservation test | PASS |
| AC4 | _parse_duration_seconds at line 60 and_normalize_age_style at line 82 reject invalid values, and _read_age_thresholds at line 103 returns no thresholds when the config shape is malformed | Missing-config, malformed-YAML, absent-tui, non-list, invalid-duration, invalid-color, missing-after, missing-color, and scalar-list fallback tests | PASS |
| AC5 | Full board module pytest passed, task-scoped ruff passed, scoped coverage reports board.py at 95 percent, and no new imports or dependency-manifest changes are involved in the task implementation | Full tests/test_cli_board.py module run | PASS |

### Verdict

- PASS
- Confidence: .91

### Action Taken

- Moving task 921 to docs and releasing the reviewer claim.

[[2026-03-25]] Wed 00:08

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: local config helpers | _load_board_config L30,_read_age_thresholds L103, no new imports | PASS |
| AC2: raw age seconds for threshold | _age_display_and_seconds L201 separates display from raw seconds | PASS |
| AC3: normalize numeric colors, Age cell only | _normalize_age_style L82 wraps digits in color(N), Style.parse validates, styling at L272 only on age_cell | PASS |
| AC4: fallback on invalid config | OSError/YAMLError caught in _load_board_config, shape/key/duration/color validation in_read_age_thresholds returns [] | PASS |
| AC5: no new deps, tests pass | pyproject.toml unchanged, 51 passed in test_cli_board.py, ruff clean | PASS |

### Test Results

- pytest (task-scoped): 51 passed, 0 failed
- pytest (full suite): 4227 passed, 91 failed (all pre-existing RED-phase/unrelated), 0 regressions from #921
- ruff: All checks passed

### Architect Quality

- AC specificity: 5/5 - explicit failure modes, clear scope, measurable criteria
- Edge case coverage: complete - all fallback paths specified in AC4
- Design direction: clean - local helpers pattern consistent with decisions.py

### Confidence: .96

### Action: archive

### Quality Gap Note

- Uncommitted test strengthening (assignee-cell negative guard) was left by the second review cycle - committed by auditor as 16bf25b.

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 16bf25b | test | tests/test_cli_board.py | #921 |

[[2026-03-25]] Wed 00:08

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: local config helpers | _load_board_config L30,_read_age_thresholds L103, no new imports | PASS |
| AC2: raw age seconds for threshold | _age_display_and_seconds L201 separates display from raw seconds | PASS |
| AC3: normalize numeric colors, Age cell only | _normalize_age_style L82 wraps digits in color(N), Style.parse validates, styling at L272 only on age_cell | PASS |
| AC4: fallback on invalid config | OSError/YAMLError caught in _load_board_config, shape/key/duration/color validation in_read_age_thresholds returns [] | PASS |
| AC5: no new deps, tests pass | pyproject.toml unchanged, 51 passed in test_cli_board.py, ruff clean | PASS |

### Test Results

- pytest (task-scoped): 51 passed, 0 failed
- pytest (full suite): 4227 passed, 91 failed (all pre-existing RED-phase/unrelated), 0 regressions from #921
- ruff: All checks passed

### Architect Quality

- AC specificity: 5/5 - explicit failure modes, clear scope, measurable criteria
- Edge case coverage: complete - all fallback paths specified in AC4
- Design direction: clean - local helpers pattern consistent with decisions.py

### Confidence: .96

### Action: archive

### Quality Gap Note

- Uncommitted test strengthening (assignee-cell negative guard) was left by the second review cycle - committed by auditor as 16bf25b.

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 16bf25b | test | tests/test_cli_board.py | #921 |
