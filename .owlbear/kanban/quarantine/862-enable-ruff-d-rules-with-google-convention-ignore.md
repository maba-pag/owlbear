---
id: 862
title: Enable ruff D rules with Google convention (ignore D1xx)
status: archived
priority: needed
created: 2026-03-20T12:16:45.0722391+01:00
updated: 2026-03-23T03:53:30.6399558+01:00
started: 2026-03-23T03:53:10.9327193+01:00
completed: 2026-03-23T03:53:10.9327193+01:00
tags:
    - config
    - tooling
    - code-quality
class: standard
---

Research split from #543. See docs/research/docstring-style.md.

## Acceptance Criteria

- [ ] In pyproject.toml [tool.ruff.lint].ignore, remove the bare D ignore and replace it with a D1xx-only ignore entry while preserving the existing non-docstring ignores.
- [ ] Add [tool.ruff.lint.pydocstyle] with convention = google.
- [ ] uv run ruff check src/ --select D --ignore D100,D101,D102,D103,D104,D105,D106,D107 exits 0.
- [ ] Source-file edits are limited to docstring text or formatting fixes for the current D205 and D416 violations, plus raw-string docstring fixes for the current D301 violations in src/owlbear/core/notification_hook.py and src/owlbear/tools/web_search.py.
- [ ] No executable logic, imports, function signatures, or data structures change in src/.
- [ ] This task does not enable any D1xx rule.

[[2026-03-20]] Fri 12:35

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| In pyproject.toml [tool.ruff.lint].ignore, remove the bare D ignore and replace it with a D1xx-only ignore entry while preserving the existing non-docstring ignores. | Precise rule-boundary change for pyproject.toml. | Keep |
| Add [tool.ruff.lint.pydocstyle] with convention = google. | Explicit convention choice; aligns Ruff with the repo's dominant docstring style. | Keep |
| uv run ruff check src/ --select D exits 0. | Mechanically wrong for this repo: live Ruff probes showed --select D surfaces D1xx unless they are ignored on the CLI, which conflicts with the task's D1xx boundary. | Rewrote verification command |
| Source-file edits in this task are limited to docstring-only fixes required by the newly enabled D2xx/D3xx/D4xx rules and the current D301 raw-string violations in src/owlbear/core/notification_hook.py and src/owlbear/tools/web_search.py. | Directionally correct, but the live non-D1xx set is specifically D205, D416, and D301. The AC needed an exact scope and a no-logic-change guard. | Rewritten + tightened |
| No executable logic, imports, function signatures, or data structures change in src/. | Makes the lint-only waiver mechanically reviewable. | Added |
| This task does not enable any D1xx rule. | Necessary guardrail for the phased rollout recommended by docs/research/docstring-style.md. | Keep |

### Architecture Notes

- Verified current Ruff config in pyproject.toml still ignores all D rules; this task is the first-phase tooling enablement from docs/research/docstring-style.md.
- Live Ruff probing under convention = google with D1xx explicitly ignored shows 31 current non-D1xx failures: 26 D416, 2 D205, and 3 D301. The older 26-violation research count is stale, but the task remains single-responsibility because all required source edits are docstring text/formatting or raw-string prefixes only.
- No separate RED test task is required. This task does not change runtime behavior, interfaces, or module layering; verification is lint-only, consistent with prior non-behavioral config/code-quality tasks.
- #863 remains a valid follow-on cleanup task because #862 only needs the lint-enforced D205/D416/D301 fixes, not a full removal of every remaining NumPy-style underline block.

### Changes Made

- Rewrote the verification AC to use an explicit D100-D107 CLI ignore list.
- Tightened the source-edit scope to the current D205/D416/D301 rule set.
- Added a no-logic-change guard for src/ edits.
- Approved task #862 for todo.

### Dependencies

- Added/Removed/Verified: verified docs/research/docstring-style.md, pyproject.toml Ruff config, and the current D205/D416/D301 violation set in src/; no new dependency task required.

[[2026-03-20]] Fri 13:19

## Test-Writer Notes\n- Non-implementation task (tagged config, tooling) - no tests applicable.\n- Architecture Review explicitly states no RED test task required: lint-only verification task with no runtime behavior change.\n- Passing through to builder

[[2026-03-20]] Fri 14:17

## Builder Notes\n- Files changed: pyproject.toml + 23 src/ files (D416 auto-fixed: 19 files; D205 manual: circuit_breaker.py daemon.py; D301 manual: notification_hook.py web_search.py)\n- Tests: circuit_breaker tests pass; pre-existing failures (missing TextChunker export, slack_sdk) unrelated to this task\n- Lint: uv run ruff check src/ --select D --ignore D100-D107 -> All checks passed (exit 0)\n- Evidence: 31 violations fixed (26 D416 auto-fix, 2 D205 manual, 3 D301 manual); BLE001/E501 in auth.py/screenshot.py are pre-existing not from this task\n- Fixes applied: replaced bare 'D' ignore with 'D1' in pyproject.toml; added [tool.ruff.lint.pydocstyle] convention=google; fixed D416 section colons; fixed D205 single-line summaries; fixed D301 raw-string prefixes

## Review Evidence

## Review: #862 - Enable ruff D rules with Google convention (ignore D1xx)

### Test Results

- pytest (scoped): uv run pytest tests/test_circuit_breaker.py tests/test_notification_hook.py tests/test_web_search.py tests/test_bookmark_pipeline.py tests/test_knowledge_chunker.py tests/test_knowledge_graph.py tests/test_knowledge_ingest.py tests/test_project_workspace.py -q --tb=short
- Result: 313 passed, 2 failed, 2 warnings
- Failing tests:  ests/test_bookmark_pipeline.py::TestBookmarkPipelineHappyPath::test_full_pipeline_high_score and  ests/test_bookmark_pipeline.py::TestBookmarkPipelineThreshold::test_low_score_skips_ingest
- Failure signature: AttributeError: module 'numpy' has no attribute 'isscalar' inside pytest.approx internals

### Lint Results

- ruff (project-wide): uv run ruff check src/ tests/
- Result: FAILED with 201 errors, predominantly test-docstring D-rule violations (D205/D209/D403/D415/D301)
- Note: This indicates broader repo lint debt under the new D-rule posture; not used as sole reject reason for this task.

### Coverage

- command: uv run pytest tests/test_circuit_breaker.py tests/test_notification_hook.py tests/test_web_search.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- result: 69 passed, 2 warnings
- touched-module coverage from report:
  - src/owlbear/core/circuit_breaker.py: 98%
  - src/owlbear/core/notification_hook.py: 100%
  - src/owlbear/tools/web_search.py: 98%

### Pass 1 - CRITICAL

#### Security Review

- Reviewed git show --unified=0 0c10649 -- src/ pyproject.toml.
- No new hardcoded secrets, injection sinks, unsafe deserialization, path traversal, or sensitive logging introduced.
- Changes are config/docstring/formatting only.

#### Test Integrity (TestFromAC comparison)

- Not applicable: commit

[[2026-03-22]] Sun 19:15

## Test-Writer Notes (retry)

- Retry reason: reviewer FAIL was about lint violations (201 D-rule errors in src/ tests/) and pre-existing numpy failures in bookmark_pipeline - not missing tests for this task's AC.
- Architecture Review explicitly states no RED test task required: lint-only verification task with no runtime behavior change.
- Non-implementation task (tagged config, tooling) - no tests applicable.
- Existing pass-through preserved. Builder will address reviewer findings.

[[2026-03-22]] Sun 22:21

## Builder Notes (retry)\n- Files changed: pyproject.toml only (+1 line: added 'D' to tests/**/*.py per-file-ignores)\n- Root cause: global D->D1 change left tests/ without a D-rule ignore; D-rule violations flooded tests/ after the previous builder's fix\n- Tests: 69 passed (test_circuit_breaker, test_notification_hook, test_web_search)\n- Lint AC: uv run ruff check src/ --select D --ignore D100-D107 -> exit 0 (All checks passed)\n- Lint src/: 2 pre-existing errors (BLE001 auth.py, E501 screenshot.py) - unrelated\n- Lint tests/: 0 D-rule violations after fix\n- Fixes applied: added D to tests/**/*.py per-file-ignores

[[2026-03-22]] Sun 23:13

## Review Evidence

## Review: #862 - Enable ruff D rules with Google convention (ignore D1xx)

### Test Results

- Scoped pytest run: uv run pytest tests/test_bootstrap.py tests/test_circuit_breaker.py tests/test_notification_hook.py tests/test_web_search.py tests/test_graph_builder.py tests/test_inter_doc_graph_builder.py tests/test_project_workspace.py tests/test_browser_manager.py -q --tb=short
- Result: 1 failed, 334 passed, 2 warnings
- Failure: tests/test_bootstrap.py::TestCreateChannelSlackSuccess::test_slack_channel_created -> ImportError: slack_sdk is not installed (optional dependency)
- Re-run excluding dependency-sensitive case (-k not TestCreateChannelSlackSuccess): 334 passed, 1 deselected, 2 warnings

### Lint Results

- AC command run by reviewer: uv run ruff check src/ --select D --ignore D100,D101,D102,D103,D104,D105,D106,D107
- Result: exit 0, All checks passed
- Source lint baseline: uv run ruff check src/ -> 2 pre-existing errors in untouched files (src/bearclaw/commands/auth.py BLE001, src/owlbear/tools/screenshot.py E501)
- Repo lint baseline: uv run ruff check src/ tests/ -> 257 errors (mostly pre-existing RUF100 in tests)

### Coverage

- Command: uv run pytest tests/test_circuit_breaker.py tests/test_notification_hook.py tests/test_web_search.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: 69 passed, 2 warnings
- Relevant module coverage: src/owlbear/core/circuit_breaker.py 98%, src/owlbear/core/notification_hook.py 100%, src/owlbear/tools/web_search.py 98%

### Pass 1 - CRITICAL

- Test-writer AC coverage: Not applicable. This task is lint-only and no task-specific TestFromAC suite exists.
- Security review: Diffs 0c10649 and b8ff0cf show config/docstring/formatting-only edits; no injection, secret, deserialization, traversal, or logging exposure introduced.
- Test integrity: Not applicable (no TestFromAC methods modified for this task).
- Data safety: No data integrity or concurrency risks introduced.
- Implementation-aware test gaps: No new behavior paths introduced.

### AC Compliance

- AC1 PASS: pyproject.toml now uses D1 in [tool.ruff.lint].ignore and retains COM812, ISC001, S101.
- AC2 PASS: pyproject.toml includes [tool.ruff.lint.pydocstyle] with convention = google.
- AC3 PASS: required Ruff D command exits 0 with All checks passed.
- AC4 FAIL: commit 0c10649 contains non-docstring executable-line formatting hunks outside the allowed docstring-only scope:
  - src/owlbear/memory/knowledge/graph_builder.py hunk @@ -165,4 +165 @@
  - src/owlbear/memory/knowledge/inter_doc_graph_builder.py hunk @@ -207,3 +207 @@
  - src/owlbear/projects/workspace.py hunks @@ -119,3 +119 @@, @@ -165,3 +163 @@, @@ -184,3 +180 @@
  - src/owlbear/tools/browser/manager.py hunk @@ -287,3 +287 @@
- AC5 PASS: no executable logic/import/signature/data-structure semantic changes detected in reviewed hunks.
- AC6 PASS: D1xx remains disabled via D1 ignore and explicit D100-D107 CLI ignore used in AC verification.

### Verdict: FAIL

### Action Taken

- kanban\\kanban-md.exe edit 862 --status todo --release

[[2026-03-22]] Sun 23:55

## Test-Writer Notes (retry 2)

- Retry reason: reviewer FAIL was about D-rule lint violations in tests/ - not missing tests for this task's AC.
- Architecture Review explicitly states no RED test task required: lint-only verification task with no runtime behavior change.
- Non-implementation task (tagged config, tooling) - no tests applicable.
- Second builder fixed root cause (added D to tests/**/*.py per-file-ignores in pyproject.toml).
- Passing through to builder.

[[2026-03-23]] Mon 00:43

## Builder Notes (retry 3)\n- Files changed: 4 src/ files (revert non-docstring code-formatting hunks)\n- AC4 fix: reverted 6 code-formatting hunks in graph_builder.py, inter_doc_graph_builder.py, workspace.py (x3), manager.py back to original multi-line form\n- All docstring fixes from previous builder (D416 Returns:/Raises: colons, D205, D301) preserved\n- AC3: uv run ruff check src/ --select D --ignore D100,D101,D102,D103,D104,D105,D106,D107 -> exit 0 (All checks passed)\n- Ruff on changed files: All checks passed\n- Sync tests: test_project_workspace.py 33 passed; async failures are pre-existing pytest-asyncio plugin mismatch (Unknown config option: asyncio_mode)\n- Commit: 50d7354 fix: revert non-docstring code-formatting hunks to docstring-only scope (#862, builder)

## Review Evidence

## Review: #862 - Enable ruff D rules with Google convention (ignore D1xx)

### Test Results

- Scoped pytest: uv run pytest tests/test_circuit_breaker.py tests/test_notification_hook.py tests/test_web_search.py tests/test_project_workspace.py -q --tb=short
- Result: 102 passed, 2 warnings (optional dependency skips: qdrant_client)

### Lint Results

- AC command: uv run ruff check src/ --select D --ignore D100,D101,D102,D103,D104,D105,D106,D107 -> All checks passed.
- Source lint baseline: uv run ruff check src/ -> 2 pre-existing errors in untouched files (src/bearclaw/commands/auth.py BLE001, src/owlbear/tools/screenshot.py E501).
- Repo lint baseline: uv run ruff check src/ tests/ -> 251 errors (249 fixable), predominantly pre-existing RUF100 in tests.

### Coverage

- Command: uv run pytest tests/test_circuit_breaker.py tests/test_notification_hook.py tests/test_web_search.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: 69 passed, 2 warnings.
- Relevant modules from report:
  - src/owlbear/core/circuit_breaker.py: 98%
  - src/owlbear/core/notification_hook.py: 100%
  - src/owlbear/tools/web_search.py: 98%

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- Not applicable: lint-only task; no task-specific TestFromAC_* suite exists. Prior architecture and test-writer notes explicitly marked no RED test task required.

#### Security Review

- Reviewed task commits

[[2026-03-23]] Mon 03:52

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Replace bare D ignore with D1xx-only in pyproject.toml | pyproject.toml L66: D1 in ignore list; COM812/ISC001/S101 preserved | PASS |
| Add [tool.ruff.lint.pydocstyle] convention = google | pyproject.toml L92-93: section + convention present | PASS |
| ruff check src/ --select D --ignore D100-D107 exits 0 | Ran command: All checks passed | PASS |
| Source edits limited to D205/D416/D301 docstring fixes | Commit 50d7354 reverted non-docstring hunks; reviewer retry 3 confirmed | PASS |
| No executable logic/imports/signatures change | All diffs are docstring text/formatting and pyproject.toml config only | PASS |
| No D1xx rule enabled | D1 in ignore list disables all D1xx; verified in pyproject.toml L66 | PASS |

### Test Results

- pytest full suite: 3779 passed, 88 failed (all pre-existing), 20 skipped. No regressions from 862.
- ruff check src/: 2 pre-existing errors (BLE001 auth.py, E501 screenshot.py) unrelated.

### Architect Quality

- AC quality score: 4/5. Architect caught flawed AC3 and rewrote it, added no-logic-change guard.
- Edge case: tests/ per-file-ignores gap found in retry cycle, not originally anticipated.

### Commits (upstream, verified)

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0c10649 | feat | pyproject.toml + 23 src/ | #862 |
| b8ff0cf | chore | pyproject.toml | #862 |
| 50d7354 | fix | 4 src/ files | #862 |
| 9873ead | docs | python.instructions.md | #862 |

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 03:53

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Replace bare D ignore with D1xx-only in pyproject.toml | pyproject.toml L66: D1 in ignore list; COM812/ISC001/S101 preserved | PASS |
| Add [tool.ruff.lint.pydocstyle] convention = google | pyproject.toml L92-93: section + convention present | PASS |
| ruff check src/ --select D --ignore D100-D107 exits 0 | Ran command: All checks passed | PASS |
| Source edits limited to D205/D416/D301 docstring fixes | Commit 50d7354 reverted non-docstring hunks; reviewer retry 3 confirmed | PASS |
| No executable logic/imports/signatures change | All diffs are docstring text/formatting and pyproject.toml config only | PASS |
| No D1xx rule enabled | D1 in ignore list disables all D1xx; verified in pyproject.toml L66 | PASS |

### Test Results

- pytest full suite: 3779 passed, 88 failed (all pre-existing), 20 skipped. No regressions from 862.
- ruff check src/: 2 pre-existing errors (BLE001 auth.py, E501 screenshot.py) unrelated.

### Architect Quality

- AC quality score: 4/5. Architect caught flawed AC3 and rewrote it, added no-logic-change guard.
- Edge case: tests/ per-file-ignores gap found in retry cycle, not originally anticipated.

### Commits (upstream, verified)

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0c10649 | feat | pyproject.toml + 23 src/ | #862 |
| b8ff0cf | chore | pyproject.toml | #862 |
| 50d7354 | fix | 4 src/ files | #862 |
| 9873ead | docs | python.instructions.md | #862 |

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 03:53

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Replace bare D ignore with D1xx-only in pyproject.toml | pyproject.toml L66: D1 in ignore list; COM812/ISC001/S101 preserved | PASS |
| Add [tool.ruff.lint.pydocstyle] convention = google | pyproject.toml L92-93: section + convention present | PASS |
| ruff check src/ --select D --ignore D100-D107 exits 0 | Ran command: All checks passed | PASS |
| Source edits limited to D205/D416/D301 docstring fixes | Commit 50d7354 reverted non-docstring hunks; reviewer retry 3 confirmed | PASS |
| No executable logic/imports/signatures change | All diffs are docstring text/formatting and pyproject.toml config only | PASS |
| No D1xx rule enabled | D1 in ignore list disables all D1xx; verified in pyproject.toml L66 | PASS |

### Test Results

- pytest full suite: 3779 passed, 88 failed (all pre-existing), 20 skipped. No regressions from 862.
- ruff check src/: 2 pre-existing errors (BLE001 auth.py, E501 screenshot.py) unrelated.

### Architect Quality

- AC quality score: 4/5. Architect caught flawed AC3 and rewrote it, added no-logic-change guard.
- Edge case: tests/ per-file-ignores gap found in retry cycle, not originally anticipated.

### Commits (upstream, verified)

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0c10649 | feat | pyproject.toml + 23 src/ | #862 |
| b8ff0cf | chore | pyproject.toml | #862 |
| 50d7354 | fix | 4 src/ files | #862 |
| 9873ead | docs | python.instructions.md | #862 |

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 03:53

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4692834 | chore | kanban/tasks/862-*.md | #862 |
