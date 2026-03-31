---
id: 180
title: Add CLI entrypoint for analysis pipeline
status: todo
priority: important
created: 2026-03-29T19:51:28.617595+02:00
updated: 2026-03-31T04:59:53.3329939+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
    - cli
depends_on:
    - 179
    - 466
class: standard
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
