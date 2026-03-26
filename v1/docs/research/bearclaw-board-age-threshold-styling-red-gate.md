# BearClaw Board Age-Threshold Styling RED Gate

> **Owning task:** #925 — Test bearclaw board age-threshold styling contract (RED)
> **Date:** 2026-03-21 **Status:** Complete

## 1. Context and Question

Task #925 is the RED partner for the post-MVP age-threshold styling follow-on.
The open questions are sequencing and test visibility: should the styling tests
wait for `#910`, and how can they stay at the root CLI boundary while still
observing Rich style changes without patching private render helpers [S1, S2,
S3, S4].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/bearclaw-board-age-threshold-styling.md` | .95 | Parent styling contract, raw-duration threshold rule, numeric color normalization, and fallback behavior |
| S2 | `tests/test_cli_board.py` | .95 | Existing board RED seam: `CliRunner`, module-local `subprocess.run` patching, and one-command contract file |
| S3 | `src/bearclaw/cli.py`, `src/bearclaw/commands/{usage,decisions}.py` | .90 | Root Typer composition, local Rich `Console()` usage, and tmp-path or module-constant config patching precedent |
| S4 | Task `#910` plus current `src/bearclaw/commands/` tree | .95 | `board.py` and root `board` registration do not exist yet, so `#910` is the prerequisite command seam |
| S5 | Rich Console docs | .95 | Non-terminal output strips ANSI by default; `FORCE_COLOR`, `TTY_COMPATIBLE`, and `TTY_INTERACTIVE` can force terminal-compatible capture |
| S6 | Rich Style docs | .90 | `color(<number>)` numeric palette syntax and style parsing expectations |
| S7 | Typer Testing docs | .90 | `CliRunner.invoke()` boundary testing, `result.output`, and stdout or stderr assertion patterns |
| S8 | Local Rich or `CliRunner` probe | .95 | Verified `Console(file=StringIO())` and default `CliRunner` drop ANSI, while forced-terminal env preserves `\x1b[38;5;34m...\x1b[0m` |
| S9 | `kanban/config.yml` | .90 | Live thresholds include `1h` and numeric colors like `"34"`, which makes raw-duration matching and numeric-style normalization observable |

## 3. Options

| Option | Confidence | Test seam | Pros | Risks | Verdict |
|--------|:----------:|-----------|------|-------|---------|
| A. Root `CliRunner` + patched subprocess or config + terminal-compatible Rich env | .94 | Public CLI only | Preserves AC, keeps tests user-visible, no private helper patching | Needs explicit env in the test harness | Recommend |
| B. Root `CliRunner` without forced terminal behavior | .25 | Public CLI only | Lowest ceremony | Rich strips ANSI, so style differences are invisible | Reject |
| C. Patch private Rich helpers or use `record=True` exports below the CLI boundary | .40 | Helper-level | Easy style introspection | Breaks the task's CLI-boundary posture and couples tests to implementation details | Reject |
| D. Real `kanban-md` board files and live subprocesses | .15 | Integration | Highest realism | Violates AC scope, brittle on Windows and PATH, duplicates later integration coverage | Reject |

## 4. Findings

1. `#925` should depend on `#910`. The current tree still lacks
   `src/bearclaw/commands/board.py`, and `src/bearclaw/cli.py` does not expose a
   root `board` command yet. Without `#910`, the RED failures are dominated by a
   missing command seam instead of styling behavior [S2, S3, S4].

2. Keep the tests in `tests/test_cli_board.py` at the root CLI boundary. The
   existing board RED file already uses `CliRunner` plus a module-local
   `subprocess.run` patch, and BearClaw's other CLI suites use the same public
   seam rather than private render-helper tests [S2, S3, S7].

3. Default `CliRunner` capture is not enough for style assertions. Rich strips
   ANSI when it decides output is non-terminal, and the local probe confirmed
   that both `Console(file=StringIO())` and a default `CliRunner` return plain
   text only. Setting `FORCE_COLOR=1`, `TTY_COMPATIBLE=1`, and
   `TTY_INTERACTIVE=0` makes the same CLI invocation emit ANSI sequences that
   tests can assert without patching `Console()` itself [S5, S7, S8].

4. The threshold-boundary test should preserve the displayed Age text while the
   style changes. OwlBear's live config includes a `1h` threshold, so the RED
   contract should use two raw ages that still render the same Age label from
   `#910` but land on different sides of that threshold [S1, S8, S9].

5. Numeric palette colors should be asserted through their normalized style
   effect, not the raw config string. Rich expects `color(<number>)`, and the
   local probe shows `color(34)` emits the `38;5;34` ANSI sequence. The RED
   contract should therefore look for the normalized color effect rather than a
   literal `"34"` token in output [S1, S6, S8, S9].

6. Fallback cases should remain exit-0 and visually plain. Missing config,
   malformed threshold structures, invalid durations, and invalid style values
   should still print the same Age text and avoid the threshold color sequence,
   matching the non-breaking fallback rule already fixed in the parent research
   [S1, S2, S5, S7].

## 5. Recommendation (.94 confidence)

Use option A.

Recommended RED contract for `#925`:

- add `#910` as an explicit dependency before the task leaves ideation
- keep the new cases in `tests/test_cli_board.py`
- patch only `bearclaw.commands.board.subprocess.run` plus the config seam
  (`kanban/config.yml` via temp cwd or a local config-path helper)
- invoke the CLI with `FORCE_COLOR=1`, `TTY_COMPATIBLE=1`, and
  `TTY_INTERACTIVE=0` so Rich styles stay observable in `CliRunner` output
- assert the same Age text across a threshold boundary while the ANSI style
  sequence changes
- assert malformed or missing threshold inputs keep exit code `0` and plain Age
  text with no threshold color sequence

## 6. Follow-up Tasks

1. Existing `#910` — Implement bearclaw board Rich table command
   Priority rationale: prerequisite command seam; without it `#925` mostly fails
   for missing command wiring rather than styling behavior.
   Dependencies: must precede `#925` and `#921`.
   One-line AC: land the root `board` command and the base contract from `#909`.

2. Existing `#921` — Honor kanban age thresholds in bearclaw board Rich output
   Priority rationale: GREEN half consumes the RED contract fixed here.
   Dependencies: after `#910` and `#925`.
   One-line AC: implement local threshold parsing, numeric color normalization,
   Age-cell-only styling, and graceful fallback behavior.

3. No new task required
   Rationale: this pass tightened sequencing and the test harness only; the
   actionable implementation work already exists in `#910` and `#921`.
