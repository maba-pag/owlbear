---
id: 466
title: 'Test: CLI entrypoint for analysis pipeline'
status: review
priority: important
created: 2026-03-31T04:56:48.2314847+02:00
updated: 2026-03-31T07:10:42.6090691+02:00
started: 2026-03-31T04:57:02.2910553+02:00
tags:
    - phase-2
    - ' scope:orchestrator'
    - ' type:test'
    - ' cli'
    - ' test'
depends_on:
    - 179
class: standard
---

RED phase tests for #180 (CLI entrypoint for analysis pipeline).

Test the _cli.py main(argv=None) -> int function and __main__.py entrypoint.

AC:
- [ ] test_main_returns_int: main() returns 0 on success
- [ ] test_default_format_json: main([]) with no args prints JSON to stdout (default format=json, window=all)
- [ ] test_format_json_flag: main(["--format", "json"]) prints JSON array to stdout
- [ ] test_format_markdown_flag: main(["--format", "markdown"]) prints markdown table to stdout
- [ ] test_window_hours: main(["--window", "24"]) passes timedelta(hours=24) to analyze()
- [ ] test_window_default_all: main([]) without --window passes large timedelta to analyze() (scans all history)
- [ ] test_audit_dir_flag: main(["--audit-dir", "custom/"]) passes Path("custom/") to analyze()
- [ ] test_audit_dir_default: main([]) without --audit-dir passes Path("data/audit/") to analyze()
- [ ] test_exit_code_0_success: main() returns 0 when analyze succeeds
- [ ] test_exit_code_1_on_error: main() returns 1 when analyze raises an exception
- [ ] test_error_message_stderr: on error, message goes to stderr (not stdout)
- [ ] test_no_proposals_json: when analyze returns [], JSON output is "[]"
- [ ] test_no_proposals_markdown: when analyze returns [], markdown output is "No analysis proposals."
- [ ] test_main_argv_injection: main(argv) uses argv, not sys.argv (testability contract)

Approach: mock analyze() and formatters; test main(argv) directly. No subprocess needed.

[[2026-03-31]] Tue 06:14
## Test-Writer Notes
- Test file: tests/test_analysis_cli.py
- Classes: TestFromAC_AnalysisCLI
- Tests per category: happy 6, edge 3, error 2, boundary 2
- Total: 14 tests, all FAIL (ImportError â€” _cli.py not yet built)
- ruff: clean
- AC coverage:
  - test_main_returns_int -> test_main_returns_int (happy)
  - test_exit_code_0_success -> test_exit_code_0_success (happy)
  - test_default_format_json -> test_default_format_json (happy)
  - test_format_json_flag -> test_format_json_flag (happy)
  - test_format_markdown_flag -> test_format_markdown_flag (happy)
  - test_window_hours -> test_window_hours (boundary)
  - test_window_default_all -> test_window_default_all (boundary)
  - test_audit_dir_flag -> test_audit_dir_flag (happy)
  - test_audit_dir_default -> test_audit_dir_default (happy)
  - test_exit_code_1_on_error -> test_exit_code_1_on_error (error)
  - test_error_message_stderr -> test_error_message_stderr (error)
  - test_no_proposals_json -> test_no_proposals_json (edge)
  - test_no_proposals_markdown -> test_no_proposals_markdown (edge)
  - test_main_argv_injection -> test_main_argv_injection (edge)
- Patch namespace: owlbear_orchestrator.analysis._cli

[[2026-03-31]] Tue 07:10
## Builder Notes
- Files changed: packages/orchestrator/src/owlbear_orchestrator/analysis/_cli.py (new)
- Tests: 14 passed, 100% coverage on _cli.py
- Lint: ruff clean
- Evidence: 14/14 TestFromAC_AnalysisCLI passed; coverage 26/26 stmts
- Fixes applied: Used sys.stdout.write/sys.stderr.write instead of print() to satisfy T201; moved return to else block for TRY300
