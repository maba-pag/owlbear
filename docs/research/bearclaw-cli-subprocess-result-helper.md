# BearClaw CLI Subprocess Result Helper

Task: #926
Question: Which reusable helper shape best reduces BearClaw CLI subprocess-test duplication without adding a production abstraction or a new test dependency?

## Sources Studied

| ID | Source | What it established |
|----|--------|---------------------|
| S1 | `tests/conftest.py`; `tests/test_conftest_helpers.py` | Shared test helpers already live in `conftest.py`, and duplicate local helpers are guarded explicitly. |
| S2 | `tests/test_cli_chat.py` | Current BearClaw CLI duplication is four hand-built `CompletedProcess`-like mocks around `_detect_github_remote()`. |
| S3 | `tests/test_cli_board.py` | Board tests already rely on a local command-router helper keyed on kanban subcommands. |
| S4 | `src/bearclaw/commands/chat.py`; `src/bearclaw/commands/board.py` | BearClaw call sites consume `subprocess.run(..., capture_output=True, text=True, check=False)` via `returncode`, `stdout`, and `stderr`. |
| S5 | Python `subprocess` docs | `subprocess.run()` returns `CompletedProcess`, and missing executables raise `OSError` before any result object exists. |
| S6 | pytest fixture docs | Reusable factory helpers in `conftest.py` are a normal pytest sharing pattern. |
| S7 | Python `unittest.mock` docs | `spec` and `side_effect` constrain mocks, but mocks remain synthetic and should still be patched at the lookup site. |
| S8 | Typer testing docs | BearClaw CLI behavior should stay validated at the `CliRunner` command boundary. |
| S9 | `pytest-subprocess` docs | The plugin can fake subprocesses comprehensively, but it introduces a broader seam and an extra dependency. |

## Current State

- `tests/test_cli_chat.py` repeats four `MagicMock(spec=subprocess.CompletedProcess)` setups for git-remote detection. [S2, S4]
- `tests/test_cli_board.py` already needs a board-specific router that chooses different fake outputs for kanban `list` versus `log` calls, so not every subprocess concern is cross-command. [S3, S4]
- Shared helper extraction in `tests/conftest.py` is already a repo convention, and `tests/test_conftest_helpers.py` exists to stop helpers from drifting back into per-file duplicates. [S1, S6]

## Option Comparison

| Option | Confidence | Pros | Costs | Verdict |
|--------|------------|------|-------|---------|
| A. Shared `CompletedProcess` factory in `tests/conftest.py`; keep per-command routers local | .94 | Matches repo precedent, uses the real subprocess contract, no new dependency, reusable across chat plus future board tests | Adds one more shared helper to `conftest.py` | Recommend |
| B. Keep module-local helpers or repeated `MagicMock` setup | .43 | Lowest coordination cost | Leaves current duplication in place and offers no reusable path for `#924` and `#920` follow-up coverage | Reject |
| C. Add `pytest-subprocess` | .58 | Powerful API for larger subprocess suites | New dependency, wider seam than this task needs, no existing repo usage | Reject for now |

## Recommendation (.94 confidence)

Use one small shared result helper and keep command-specific routing local:

- Add an importable `make_completed_process(args=None, *, returncode=0, stdout="", stderr="")` helper in `tests/conftest.py` that returns a real text-mode `subprocess.CompletedProcess`. [S1, S4, S5, S6]
- Keep the board command's `_subproc()`-style router local to `tests/test_cli_board.py`; it should compose the shared result helper rather than becoming a global subprocess abstraction. [S3, S4, S8]
- Model missing-binary coverage with a clearly named `OSError` fixture/helper at the test seam that needs it instead of inventing a production-layer abstraction. `subprocess.run()` raises before any `CompletedProcess` exists, so the exception path should stay explicit. [S4, S5, S7]
- Do not add `pytest-subprocess` for this cleanup. It solves a broader class of problems than BearClaw currently has, and the repo already prefers small shared helpers over new test dependencies for narrow cleanup work. [S1, S2, S9]

## Why This Fits OwlBear

- A real `CompletedProcess` mirrors the exact contract BearClaw code reads today (`returncode`, `stdout`, `stderr`) and removes the current `MagicMock` boilerplate in chat tests. [S2, S4, S5, S7]
- `conftest.py`-hosted helper extraction is already an established repo pattern, so this change is additive rather than novel. [S1, S6]
- Board tests still need their own local argument router because `list` versus `log` dispatch is specific to the board command, not to subprocesses in general. [S3, S4]
- The scope stays under `tests/` only and avoids production abstractions, which matches the parent task constraints. [S1, S4]

## Follow-up Tasks

1. Implement a shared `CompletedProcess` factory for BearClaw CLI tests.

Dependencies: `#920`, `#924`.

Scope: add contract coverage in `tests/test_conftest_helpers.py`, reuse the helper in `tests/test_cli_chat.py`, let future board failure tests compose it inside their local router, keep the missing-binary seam explicit, and add no new dependency or production abstraction.
