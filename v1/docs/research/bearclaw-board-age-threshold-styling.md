# BearClaw Board Age-Threshold Styling Gate

> **Owning task:** #921 — Honor kanban age thresholds in bearclaw board Rich output
> **Date:** 2026-03-21 **Status:** Complete

## 1. Context and Question

Task #921 asks how `bearclaw board` should honor the existing
`tui.age_thresholds` config without changing status grouping or the displayed age
value. The open questions are the config seam, the Rich styling seam, and the
fallback contract when thresholds are missing or malformed [S1, S2, S3, S4].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/bearclaw-board-command.md` | .95 | Existing board seam and the current meaning of age as time in current status |
| S2 | `docs/research/bearclaw-board-command-implementation-gate.md` | .95 | Board.py scope, local-helper boundary, and the explicit deferral of threshold styling to #921 |
| S3 | `kanban/config.yml` | .95 | Actual OwlBear threshold list: ordered `after` values (`0s`, `1h`, `24h`, `72h`, `168h`) plus numeric palette colors |
| S4 | kanban-md README / config docs | .90 | `tui.age_thresholds` is the supported config key for TUI age color thresholds |
| S5 | `src/bearclaw/cli.py`, `src/bearclaw/commands/{usage,decisions}.py` | .90 | BearClaw command-module pattern, Rich table usage, and existing YAML parsing in CLI code |
| S6 | `tests/test_cli_decisions.py`, `tests/test_cli_error_helper.py` | .85 | `CliRunner` patterns, tmp-path config seams, and CLI-boundary verification style |
| S7 | Rich table docs / reference | .90 | `Table.add_row()` accepts renderables; row styles and column styles have broader scope than a single cell |
| S8 | Rich style docs / reference | .90 | `Style.parse()` validation and `color(<number>)` syntax for 256-color palette entries |
| S9 | PyYAML docs | .85 | `yaml.safe_load()` and `yaml.YAMLError` behavior for defensive config parsing |

## 3. Options

| Option | Confidence | Approach | Pros | Risks | Verdict |
|--------|:----------:|----------|------|-------|---------|
| A. Hardcode board colors | .20 | Ignore `kanban/config.yml` and pick Rich colors in code | Lowest code | Drifts from TUI config; breaks AC immediately | Reject |
| B. Read thresholds, style rows or whole column | .45 | Use config but color full rows or a static Age column | Uses Rich built-ins | Row styling changes unrelated cells; static column style cannot vary by age | Reject |
| C. Read thresholds defensively, style only the Age cell | .95 | Parse config locally, compare raw age duration, and render a styled Age cell or plain fallback | Matches AC, preserves existing display text, minimal diff | Needs one RED task to pin boundary behavior first | Recommend |

## 4. Findings

1. `tui.age_thresholds` is an ordered list, and OwlBear's live config uses
   hour-based `after` values while the board research still frames age as
   “days in status.” The styling logic therefore must compare the raw age
   duration, not the rendered age label, otherwise the `1h` threshold would be
   lost once age is rounded for display [S1, S3, S4].

2. The current config stores colors as quoted numeric palette entries such as
   `"242"` and `"34"`. Rich does not use bare numeric strings as styles; its
   supported numeric syntax is `color(<number>)`. The board command should
   normalize all-digit config colors to that syntax, and only then validate them
   with `Style.parse()` [S3, S8].

3. The correct styling seam is the Age cell only. Rich row styles and row-level
   `style=` would color the title, assignee, and tags columns as well, which is
   outside the task contract. `Table.add_row()` accepts renderables, so the
   smallest correct implementation is a local helper in `src/bearclaw/commands/board.py`
   that returns a styled Age renderable when thresholds are valid and the plain
   age text when they are not [S2, S5, S7, S8].

4. Fallback should be purely non-breaking: parse `kanban/config.yml` with
   `yaml.safe_load()`, accept only a list of mappings containing `after` and
   `color`, and treat missing config, malformed YAML, unsupported threshold
   shapes, invalid durations, or invalid Rich styles as “no styling.” That
   preserves the existing board output while satisfying the AC that malformed or
   missing thresholds must not break the command [S2, S5, S8, S9].

5. Verification belongs at the CLI boundary in `tests/test_cli_board.py`. The
   RED coverage should pin one threshold transition using unchanged age text but
   different raw durations, plus a malformed-config case that still prints the
   same age value without style. Because #921 is a GREEN task with fresh tests
   in its AC, it should gain a paired RED predecessor instead of mixing both
   phases in one card [S1, S2, S5, S6, S7].

## 5. Recommendation (.95 confidence)

Implement option C.

Recommended shape:

- keep all logic local to `src/bearclaw/commands/board.py`
- load `kanban/config.yml` with `yaml.safe_load()`
- extract `tui.age_thresholds` only if it is a list of `{after, color}` entries
- normalize numeric colors like `"242"` to `color(242)`
- validate styles with `Style.parse()`
- compare thresholds against the raw age duration already used to derive the
  Age column
- keep the rendered Age text unchanged from the #910 contract
- if anything about the threshold config is missing or invalid, render the same
  plain Age text with no style

Do not introduce a shared config model, a board-wide theme layer, or row-level
coloring. This is display polish on top of the existing board seam, not a new
configuration subsystem [S2, S5, S7, S8, S9].

## 6. Follow-up Tasks

1. #925 — Test bearclaw board age-threshold styling contract (RED)
   Priority rationale: #921 is a GREEN task but still carries new CLI-boundary
   tests, so the styling contract should be pinned first.
   Dependencies: intended predecessor to #921; the architect should add the
   dependency before approving #921 to `todo`.
   One-line AC: failing CLI tests pin config-driven Age styling, numeric color
   normalization, raw-duration threshold matching with unchanged age text, and
   malformed-config fallback.
   Created: `kanban\kanban-md.exe create "Test bearclaw board age-threshold styling contract (RED)" ...` -> #925

2. Existing #921 — Honor kanban age thresholds in bearclaw board Rich output
   Priority rationale: GREEN half of the styling split.
   Dependencies: should follow #910 and #925 once the architect keeps the
   sequence explicit.
   One-line AC: implement local threshold parsing and Age-cell styling in
   `src/bearclaw/commands/board.py` with coverage in `tests/test_cli_board.py`.
