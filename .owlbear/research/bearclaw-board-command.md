# BearClaw Board Command Research

> **Owning task:** #905 — bearclaw board: Rich table view of kanban tasks by status and assignee
> **Date:** 2026-03-21 **Status:** Complete

## 1. Context and Question

Task #905 asks for a `bearclaw board` command that shows task rows grouped by
status with columns for ID, title, assignee, age in status, and tags. Prior
research already concluded OwlBear should keep `kanban-md` and add richer board
visibility around it, with this command named as the concrete follow-up [S1,
S2]. The remaining design question is the seam: wrap the existing
`kanban-md board` summary, consume structured `kanban-md` JSON, or read board
files directly [S1, S2].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/kanban-replacement-options.md` | .95 | Prior keep-plus-augment decision and the original `bearclaw board` recommendation |
| S2 | kanban-md README / command docs | .95 | `board`, `list`, `log`, `assignee`, `claimed_by`, JSON output, and auto-discovery behavior |
| S3 | Live `kanban-md` inspection on OwlBear board | .95 | `board --group-by assignee` is summary-only; `list --json` and `log --action move --json` are structured and sufficient |
| S4 | `src/bearclaw/cli.py`, `src/bearclaw/commands/{daemon,usage}.py`, `tests/test_cli*.py` | .90 | Existing Typer/Rich command-module pattern and CLI test style |
| S5 | `src/owlbear/core/retrospective_hook.py`, `tests/test_retrospective_hook.py` | .85 | Existing move-log parsing prior art and `from -> to` detail format |
| S6 | Rich Table docs | .80 | Table sections, column options, and empty-table behavior |
| S7 | Typer commands docs | .75 | Dedicated command registration conventions |
| S8 | Typer testing docs | .75 | `CliRunner` invocation and text assertions |

## 3. Options

| Option | Confidence | Data path | Pros | Risks | Verdict |
|--------|:----------:|-----------|------|-------|---------|
| A. Wrap `kanban-md board --group-by assignee` | .30 | Human table output | Lowest code | Summary counts only; no task rows or tags; parsing terminal text is brittle | Reject |
| B. `kanban-md list --json` + `kanban-md log --action move --json` | .90 | Structured CLI JSON | Single supported seam; matches requested columns; no schema duplication | Two subprocess calls; local age calculation still required | Recommend |
| C. Parse `kanban/tasks/*.md` + `activity.jsonl` directly | .55 | Raw files | Full local control | Duplicates `kanban-md` schema and discovery rules; more maintenance than needed | Reject |

## 4. Findings

1. `kanban-md board --group-by assignee` does not solve the task by itself. On
   the live OwlBear board it prints assignee buckets with status counts, not
   task rows, so it cannot supply title, tag, or per-task age columns without
   scraping formatted output [S2, S3].

2. Structured `kanban-md` JSON is the right implementation seam.
   `list --json` already surfaces the row data needed for ID, title, status,
   tags, and assignment fields, and `log --action move --json` exposes move
   history without adding a second parser for `activity.jsonl` [S2, S3].

3. Age should mean `days in the current status`, not `days since last edit`.
   `updated` changes on any task edit, while move-log entries encode the actual
   status transition. The correct rule is: latest move into the current status;
   if none exists, fall back to `created` for tasks born in that column [S2,
   S3, S5].

4. Assignee should display `assignee` first, then `claimed_by`, then `--`.
   `assignee` is explicit task metadata supported by `kanban-md`, while
   `claimed_by` reflects the active OwlBear pipeline worker that currently has
   the task locked [S2, S3].

5. The command should live in its own CLI module, not in core OwlBear toolsets.
   A new `src/bearclaw/commands/board.py` wired from `src/bearclaw/cli.py`
   matches the current one-file-per-command layout and keeps the feature scoped
   to the human CLI surface [S4, S7].

6. Tests should use `CliRunner` plus mocked `subprocess.run` JSON responses.
   That matches existing BearClaw command tests and avoids brittle terminal
   snapshot fixtures while still covering registration, grouping, assignee
   fallback, age fallback, and empty-state behavior [S4, S6, S8].

## 5. Recommendation (.90 confidence)

Implement option B: one `kanban-md list --json` call for visible tasks and one
`kanban-md log --action move --json` call for move history, then render a Rich
table with one section per status in board order [S2, S3, S6].

Why this fits OwlBear:

- It stays on the existing `kanban-md` CLI seam instead of re-implementing
  board-file parsing [S1, S2].
- It adds no new dependency and stays within the `~120 LOC in src/bearclaw`
  target direction from the earlier research [S1, S4].
- It avoids the much larger TUI and event-stream work that earlier dashboard
  research explicitly deferred [S1, S4].

## 6. Testing Strategy

- Add a dedicated `tests/test_cli_board.py` file using `CliRunner` [S4, S8].
- Mock the `kanban-md list --json` result with tasks covering: explicit
  `assignee`, `claimed_by` only, unassigned, empty tags, and multiple statuses
  [S2, S3].
- Mock the `kanban-md log --action move --json` result with both matching and
  missing move entries to pin the age fallback behavior [S2, S3, S5].
- Assert rendered output contains status headers, column headers, expected task
  rows, and a friendly no-tasks message [S4, S6].

## 7. Follow-up Tasks

1. #909 — Test bearclaw board command rendering and status age (RED)
   Priority rationale: nice-to-have visibility improvement; test-first split
   keeps the status-age rules explicit before implementation.
   Dependencies: intended to run before the build task if the architect keeps
   the split.
   One-line AC: failing tests pin command registration, status grouping,
   assignee fallback, age-in-status calculation, and empty-state output.
   Created: `kanban\kanban-md.exe create "Test bearclaw board command rendering and status age (RED)" ...`

2. #910 — Implement bearclaw board Rich table command
   Priority rationale: same user-visible feature, scoped to CLI only and no new
   dependencies.
   Dependencies: intended follower to #909 if the split is kept.
   One-line AC: add a top-level `bearclaw board` command in
   `src/bearclaw/commands/board.py` that uses `kanban-md` JSON outputs and
   renders the Rich table.
   Created: `kanban\kanban-md.exe create "Implement bearclaw board Rich table command" ...`
