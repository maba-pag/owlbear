---
id: 180
title: Add CLI entrypoint for analysis pipeline
status: archived
priority: medium
created: 2026-03-29 19:51:28.617595+02:00
updated: 2026-03-31 22:47:54.344375+02:00
started: 2026-03-31 22:47:53.764946+02:00
completed: 2026-03-31 22:47:53.764946+02:00
tags:
- phase-2
- scope:orchestrator
- type:build
- cli
depends_on:
- 179
- 466
class: standard
archival_reason: completed
archival_refs: []
---

Add `python -m owlbear_orchestrator.analyze` entrypoint via two new files in `packages/orchestrator/src/owlbear_orchestrator/analysis/`:

**Files:**
- `_cli.py`: CLI logic with `main(argv=None) -> int` function
- `__main__.py`: 3-line entrypoint importing `main` from `_cli`

**Implementation contract:**

`_cli.py`:
- `main(argv: list[str] | None = None) -> int` is the only public function
- Uses `argparse.ArgumentParser` (stdlib, no Typer)
- `--window HOURS` (float): converts to `timedelta(hours=HOURS)`, passes to `analyze(window=...)`. When omitted, passes `timedelta(days=36500)` to scan all history (avoids changing `analyze()` default)
- `--format {json,markdown}` (str, default `json`): selects `format_json()` or `format_markdown()` from `formatters.py`
- `--audit-dir PATH` (str, default `data/audit/`): passes `Path(value)` to `analyze(audit_dir=...)`
- On success: prints formatted output to stdout, returns 0
- On error (any exception from `analyze()`): prints message to stderr, returns 1
- No side effects beyond stdout/stderr

`__main__.py`:
- Imports `main` from `owlbear_orchestrator.analysis._cli`
- Calls `sys.exit(main())`
- No other logic

AC:
- [ ] `python -m owlbear_orchestrator.analyze` executes `__main__.py` which calls `_cli.main()`
- [ ] `_cli.main(argv=None) -> int` accepts optional argv list for testability
- [ ] `--window 24` passes `timedelta(hours=24)` to `analyze()`
- [ ] No `--window` flag passes `timedelta(days=36500)` to `analyze()` (scan all history)
- [ ] `--format json` (default) prints `format_json()` output to stdout
- [ ] `--format markdown` prints `format_markdown()` output to stdout
- [ ] `--audit-dir custom/path` passes `Path(custom/path)` to `analyze()`
- [ ] Default `--audit-dir` is `data/audit/`
- [ ] Exit code 0 on success
- [ ] Exit code 1 on error; error message to stderr (not stdout)
- [ ] No proposals with json format prints `[]`; with markdown prints `No analysis proposals.`
- [ ] No changes to existing `analyze()`, `formatters.py`, or `cli.py`

Depends on #179 (analysis module, archived), #466 (tests RED phase)
See docs/research/cli-entrypoint-analysis-pipeline.md for full analysis.

[[2026-03-31]] Tue 04:59
## Architecture Review
See docs/scratch/180-architect.md for full review.

[[2026-03-31]] Tue 16:17
## Test-Writer Notes
- Test file: tests/test_analysis_main_180.py
- Classes: TestFromAC_MainEntrypoint
- Tests per category: happy 3, edge 0, error 1, boundary 0, integration 2
- Total: 6 tests, all FAIL (AssertionError) confirmed against current HEAD
- ruff: clean
- AC coverage:
  - python -m owlbear_orchestrator.analysis executes __main__.py: test_main_module_exists, test_module_run_exit_0_on_success
  - No proposals json prints []: test_module_run_no_proposals_json
  - No proposals markdown prints 'No analysis proposals.': test_module_run_no_proposals_markdown
  - Exit code 1 on error + stderr message: test_module_run_exit_1_on_error_with_stderr_message
  - stdout is valid JSON array: test_module_run_stdout_is_valid_json
- Note: remaining AC items (window, audit-dir, format flags) are covered by pre-existing TestFromAC_AnalysisCLI in tests/test_analysis_cli.py (written for task #466, _cli.py already implemented)

[[2026-03-31]] Tue 17:35
## Builder Notes
- Files changed: packages/orchestrator/src/owlbear_orchestrator/analysis/__main__.py (created, 7 lines)
- Tests: 6 passed (TestFromAC_MainEntrypoint), ruff clean
- Evidence: all 6 TestFromAC_ tests RED to GREEN
- Coverage: 0% on __main__.py (expected, subprocess-only execution)
- Fixes applied: None

[[2026-03-31]] Tue 21:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Orchestrator already describes 'audit analysis (pattern detectors)'; no new behavior or convention |
| 2 | Docstrings | Yes | Pass | _cli.py has module docstring + main() docstring; __main__.py is 7-line runner with no public functions |
| 3 | sources/overview.md | No | N/A | Uses stdlib argparse/__main__ pattern and internal OwlBear references only; no novel external borrowing |
| 4 | README.md | No | N/A | README has no section for individual python -m module commands |
| 5 | Research doc linked | Yes | Pass | docs/research/cli-entrypoint-analysis-pipeline.md exists and linked from task body |

### Files Updated
- None

### Scratch Files Cleaned
- Deleted docs/scratch/180-architect.md

[[2026-03-31]] Tue 22:47
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| __main__.py executes _cli.main() | __main__.py L5-7: imports main from _cli, calls sys.exit(main()) | PASS |
| _cli.main(argv=None) -> int testable | _cli.py L17: def main(argv: list[str] None = None) -> int | PASS |
| --window 24 passes timedelta(hours=24) | Pre-existing _cli.py L46, covered by test_analysis_cli.py | PASS |
| No --window passes timedelta(days=36500) | _cli.py L14+L46: _DEFAULT_WINDOW fallback | PASS |
| --format json default prints format_json | _cli.py L50-51, test_module_run_no_proposals_json green | PASS |
| --format markdown prints format_markdown | _cli.py L53, test_module_run_no_proposals_markdown green | PASS |
| --audit-dir custom/path | _cli.py L38-42, covered by test_analysis_cli.py | PASS |
| Default --audit-dir data/audit/ | _cli.py L13: _DEFAULT_AUDIT_DIR = Path(data/audit/) | PASS |
| Exit code 0 on success | test_module_run_exit_0_on_success green | PASS |
| Exit code 1 on error, stderr msg | test_module_run_exit_1_on_error_with_stderr_message green | PASS |
| No proposals json=[], markdown=No analysis proposals. | test_module_run_no_proposals_json + markdown green | PASS |
| No changes to existing analyze/formatters/cli | Builder notes: only __main__.py created | PASS |

### Test Results
- pytest full suite: 1959 passed, 186 failed (all unrelated), 1 error (unrelated fixture)
- task-scope tests: 6/6 passed (TestFromAC_MainEntrypoint)
- ruff: clean for task scope (2 violations in unrelated test_necessity_check_196.py)

### AC Quality Score: 5/5
AC was specific, complete, and led to a clean 7-line implementation. All items measurable.

### Upstream Commits
- 7b72ab5 test: add failing tests (#180, test-writer)
- a9e846c feat: add __main__.py entrypoint (#180, builder)

### Deduction breakdown
- Missing Review Evidence section in task body: -.02

### Confidence: .98
### Action: archive
