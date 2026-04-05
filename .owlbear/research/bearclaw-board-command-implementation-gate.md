# BearClaw Board Command Implementation Gate

> **Owning task:** #910 — Implement bearclaw board Rich table command
> **Date:** 2026-03-21 **Status:** Complete

## 1. Question

Task #905 already chose the `kanban-md` JSON seam and created the paired RED and
GREEN tasks. This pass validates #910 against the current OwlBear codebase: live
`kanban-md` schemas, BearClaw command-module conventions, status-order inputs,
timestamp parsing, and post-MVP boundaries [S1, S2, S3].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/bearclaw-board-command.md` | .95 | Prior seam decision and the already-approved MVP scope for `bearclaw board` |
| S2 | kanban-md README / command docs | .95 | `list --json`, `log --action move --json`, auto-discovery, status ordering, and config semantics |
| S3 | Live `kanban-md` inspection on OwlBear board | .95 | Actual `list` and `log` JSON fields, including `assignee`, `claimed_by`, `created`, `detail`, and `timestamp` |
| S4 | `src/bearclaw/cli.py`, `src/bearclaw/commands/{daemon,usage}.py` | .90 | Root command wiring and task-local Rich helper patterns |
| S5 | `src/bearclaw/commands/__init__.py`, `src/bearclaw/commands/decisions.py`, `tests/test_cli_error_helper.py` | .90 | BearClaw CLI error contract via `_cli_error` |
| S6 | `src/bearclaw/commands/chat.py` | .80 | Existing `subprocess.run(..., capture_output=True, text=True, check=False, cwd=...)` command pattern |
| S7 | `src/owlbear/core/retrospective_hook.py` | .80 | Existing `detail.split(" -> ", maxsplit=1)` move-log parsing prior art |
| S8 | `kanban/config.yml` | .90 | Canonical status order plus optional `tui.age_thresholds` follow-up input |
| S9 | Rich Table docs | .80 | Table sections, column styling, and empty-table handling |
| S10 | Typer Add Typer docs | .75 | `app.add_typer()` composition for dedicated command modules |
| S11 | Python `datetime` docs | .75 | `datetime.fromisoformat()` parsing of ISO 8601 timestamps with UTC offsets |

## 3. Findings

1. The live `kanban-md` JSON seam still matches #910 exactly. `list --json`
   returns the row fields needed for ID, title, status, tags, assignee, and
   created time, while `log --action move --json` returns `detail` and
   `timestamp` entries that are sufficient to derive age in status without
   parsing board files directly [S1, S2, S3, S7].

2. The command should be implemented as a dedicated
   `src/bearclaw/commands/board.py` module promoted to the root CLI with
   `app.add_typer(board_app)`. That matches the current BearClaw one-file-per-
   command layout and keeps the helpers local instead of inventing a shared
   abstraction for a single command [S4, S10].

3. Status grouping must follow `kanban/config.yml`, not task sort order, and age
   should be computed from the latest move into the current status with a
   `created` fallback. The current board config is the canonical status-order
   source, and Python's `datetime.fromisoformat()` already handles the ISO 8601
   timestamps with offsets returned by the live board and activity log [S3, S8,
   S11].

4. BearClaw already has a clear CLI failure contract: `_cli_error` writes
   `Error: ...` to stderr and exits with code 1, and command modules such as
   `decisions.py` use that helper for user-facing failures. Board subprocesses
   should follow the existing `subprocess.run(..., capture_output=True,
   text=True, check=False, cwd=...)` pattern, with `_cli_error` preferred over
   raw tracebacks whenever the board command surfaces a user-facing failure [S5,
   S6].

5. Rich `Table.add_section()` is the right primitive for per-status grouping,
   and empty-board output should stay explicit rather than printing a blank table.
   That matches current BearClaw Rich usage and Rich's documented empty-table
   behavior [S4, S9].

6. Two post-MVP follow-ups are justified but should stay outside #910. First,
   broader failure hardening for missing `kanban-md`, non-zero exits, and invalid
   JSON. Second, optional age styling that honors the existing
   `tui.age_thresholds` config. Both are valuable, but neither is required to
   satisfy the already-approved #910 AC [S5, S8, S9].

## 4. Recommendation (.93 confidence)

Implement #910 now as a narrow happy-path command:

- add `src/bearclaw/commands/board.py`
- wire it into `src/bearclaw/cli.py` as a top-level command
- run exactly one `kanban-md list --json` call and one
  `kanban-md log --action move --json` call
- keep helpers local to `board.py`
- group rows by configured status order
- display assignee as `assignee -> claimed_by -> --`
- compute age from the latest move into the current status, with `created`
  fallback

Do not expand #910 into direct board-file parsing, a shared kanban helper layer,
TUI-threshold styling, or a larger failure-handling matrix. Those are valid but
separate follow-ups [S1, S4, S5, S8, S9].

## 5. Follow-up Tasks

1. #920 — Harden bearclaw board command failures and JSON parsing
   Why: the BearClaw `_cli_error` contract is already established, but the MVP
   task does not need the full missing-binary, non-zero-exit, and invalid-JSON
   matrix [S5, S6].

2. #921 — Honor kanban age thresholds in bearclaw board Rich output
   Why: `kanban/config.yml` already defines `tui.age_thresholds`, and Rich
   supports styled table cells, but this is display polish beyond the MVP AC
   [S8, S9].
