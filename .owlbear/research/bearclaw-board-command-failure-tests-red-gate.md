# BearClaw Board Failure-Test RED Gate

> **Owning task:** #924 — Test bearclaw board failure handling and JSON parse errors (RED)
> **Date:** 2026-03-21 **Status:** Complete

## 1. Context and Question

Task #924 fixes the RED seam for post-MVP `bearclaw board` failure handling.
The remaining design question is whether the new tests should stay at the root
CLI boundary with patched `subprocess.run`, drop to a private helper seam, or
exercise the real `kanban-md` binary [S1, S2, S3, S4].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/bearclaw-board-command-failure-handling.md` | .95 | Existing failure contract and RED/GREEN split for `#924` -> `#920` |
| S2 | `docs/research/bearclaw-board-command-red-gate.md` | .90 | Prior happy-path RED seam and board CLI test posture |
| S3 | `tests/test_cli.py`, `tests/test_cli_chat.py`, `tests/test_cli_error_helper.py` | .95 | Local `CliRunner`, subprocess patching, and `_cli_error` assertion style |
| S4 | `src/bearclaw/cli.py`, `src/bearclaw/commands/__init__.py` | .95 | Root Typer composition, Rich traceback install, and `_cli_error` behavior |
| S5 | `src/owlbear/core/board_context.py`, `tests/test_board_context.py` | .85 | Existing kanban subprocess spawn, `OSError`, and return-code handling precedent |
| S6 | Python `subprocess` docs | .90 | `run(..., check=False, capture_output=True, text=True)` and missing-executable `OSError` semantics |
| S7 | Python `json` docs | .90 | `JSONDecodeError` behavior for malformed payloads |
| S8 | Typer Testing docs | .90 | `CliRunner` invocation and stdout or stderr assertions |
| S9 | Click exception handling docs | .85 | User-facing stderr rendering and exit-code behavior |
| S10 | Typer exceptions docs | .80 | Uncaught exceptions surface as pretty tracebacks rather than the local CLI error contract |

## 3. Options

| Option | Confidence | Test seam | Pros | Risks | Verdict |
|--------|:----------:|-----------|------|-------|---------|
| A. Root CLI with patched `subprocess.run` only | .95 | `CliRunner` plus `patch("bearclaw.commands.board.subprocess.run")` | Matches AC, covers help or exit or stderr behavior, no real binary | Slightly more fixture setup | Recommend |
| B. Private helper or patched `_cli_error` | .45 | Unit tests below the CLI boundary | Smaller mocks | Misses command wiring and user-visible stderr or exit contract | Reject |
| C. Real `kanban-md` with temp board files | .20 | CLI plus live subprocess | Highest realism | Violates AC 2, brittle on Windows or PATH, duplicates integration concerns | Reject |

## 4. Findings

1. Keep the RED seam at the public CLI boundary. Typer testing guidance and the
   existing `tests/test_cli.py` or `tests/test_cli_chat.py` patterns use
   `CliRunner` to validate command exposure, exit codes, and rendered output. A
   helper-level seam would miss whether `bearclaw board` is actually wired into
   the root app and whether `_cli_error` reaches the user [S2, S3, S4, S8, S9].

2. Patch only `bearclaw.commands.board.subprocess.run`. The task AC is explicit,
   and the local CLI subprocess tests already patch the module-local
   `subprocess.run` call rather than the executable or global subprocess state.
   That keeps the tests deterministic and avoids PATH sensitivity on Windows
   [S3, S6, S8].

3. Model the five failure classes as two-stage subprocess sequences: missing
   executable on the first call, non-zero task-list exit, non-zero move-log exit
   after a successful list call, invalid task-list JSON, and invalid move-log
   JSON after a valid list payload. That matches the split between row loading
   and age loading already established in the parent failure-handling research
   [S1, S5, S6, S7].

4. Assert through the existing `_cli_error` contract, not raw exceptions.
   OwlBear's helper writes `Error: ...` to stderr and exits with code `1`, while
   uncaught Typer or Click exceptions surface differently and may leak Rich
   traceback behavior into a routine operator failure. The RED tests should
   therefore check exit code `1` and stage-specific `kanban-md` messages in CLI
   output instead of patching `_cli_error` away [S3, S4, S9, S10].

5. Keep happy-path assertions in the same `tests/test_cli_board.py` file once it
   exists. That matches the task AC, preserves one command-level contract file
   for board behavior, and leaves only optional cleanup to follow-up helpers
   such as paired JSON payload builders or repeated subprocess-result builders
   if duplication grows [S2, S3, S5].

6. Architecture fit is intentionally small: `#924` should add tests only. No
   production helper, config change, or shared subprocess wrapper is justified
   before `#920` lands; current CLI suites prefer small local helper functions
   only after repetition is proven [S3, S5].

## 5. Recommendation (.95 confidence)

Use option A.

Recommended RED contract for `#924`:

- `CliRunner` invokes the root app, not a private helper.
- Tests patch only `bearclaw.commands.board.subprocess.run`.
- Missing binary, non-zero list or log exits, and invalid list or log JSON each
  assert exit code `1` and a stage-specific message mentioning `kanban-md`.
- Happy-path board assertions stay in the same file and remain green after
  `#920` lands.
- No real `kanban-md` process or board files are involved.

## 6. Follow-up Tasks

1. Existing `#920` — Harden bearclaw board command failures and JSON parsing
   Priority rationale: GREEN half consumes the RED contract fixed here.
   Dependencies: should not move ahead of `#924` in practice; architect owns any
   dependency wiring while `#920` is actively claimed.
   One-line AC: implement the local stage-aware `_cli_error` handling in
   `src/bearclaw/commands/board.py` and satisfy the failure-path CLI tests.

2. Existing `#923` — Create reusable kanban JSON fixture helpers for BearClaw
   CLI board tests
   Priority rationale: optional cleanup for paired list or log JSON literals once
   both happy-path and failure-path board tests exist.
   Dependencies: after `#909` and alongside or after `#924` or `#920` as
   needed.
   One-line AC: extract paired list or log JSON builders for readable board CLI
   tests.

3. `#926` — Create reusable subprocess result helpers for BearClaw CLI tests
   Priority rationale: optional cleanup once `#924` introduces several
   `subprocess.run` failure fixtures and the existing chat CLI tests already show
   repeated `CompletedProcess` mocks.
   Dependencies: after `#924` and `#920`.
   One-line AC: add a test-only helper for success or non-zero or malformed
   output subprocess results and reuse it in board failure-path tests plus at
   least one existing CLI subprocess test.
   Created: `kanban\kanban-md.exe create "Create reusable subprocess result helpers for BearClaw CLI tests" ...` -> `#926`
