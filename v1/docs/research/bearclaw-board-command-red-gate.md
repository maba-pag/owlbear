# BearClaw Board RED Test Gate

> **Owning task:** #909 — Test bearclaw board command rendering and status age (RED)
> **Date:** 2026-03-21 **Status:** Complete

## 1. Context and Question

Task #909 is the research gate for the RED half of the `bearclaw board`
feature. The command seam was already chosen in #905 and refined for the GREEN
task in #910; the remaining question is the test seam: should the RED file use
live kanban board files, mock only `kanban-md` JSON subprocess output, or drop
to formatter-only unit tests [S1, S3, S5].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/bearclaw-board-command.md` | .95 | Prior board seam, assignee fallback, and age-in-status rule |
| S2 | `src/bearclaw/cli.py` | .90 | Root Typer composition and top-level command exposure pattern |
| S3 | `tests/test_cli.py`, `tests/test_cli_chat.py`, `tests/test_cli_knowledge_source.py`, `tests/test_cli_status_rich.py` | .95 | Local `CliRunner`, subprocess patching, and Rich assertion style |
| S4 | `src/owlbear/core/retrospective_hook.py`, `tests/test_retrospective_hook.py` | .80 | Existing move-log parsing and fixture-builder precedent |
| S5 | `kanban/README.md` plus live `kanban-md list --help` and `log --help` inspection | .90 | Structured `list --json` and `log --action move --json` seam |
| S6 | Typer Testing docs | .85 | `CliRunner` invocation and output assertions |
| S7 | Typer Add Typer docs | .70 | Typer app composition through `add_typer()` |
| S8 | Rich Tables docs | .80 | Stable table semantics, sections, and empty-table fallback guidance |

## 3. Options

| Option | Confidence | Test seam | Pros | Risks | Verdict |
|--------|:----------:|-----------|------|-------|---------|
| A. Live `kanban-md` subprocess with temp board files | .35 | End-to-end CLI plus filesystem | Highest realism | Violates AC #6, adds brittle timestamp setup, slower | Reject |
| B. `CliRunner` plus mocked `subprocess.run` JSON payloads | .93 | BearClaw CLI boundary only | Matches AC, isolates command contract, follows local test style | Needs paired list/log fixtures | Recommend |
| C. Formatter-only unit tests | .55 | Internal helper functions | Smallest fixtures | Misses help exposure and command wiring | Reject |

## 4. Findings

1. The RED file should test the public CLI contract, not only a formatter.
   `CliRunner` is already the BearClaw pattern for root help and command
   invocation, and AC #1 explicitly requires the top-level help surface to
   expose `board` [S2, S3, S6].

2. Mocked JSON subprocess output is the only external seam the RED file needs.
   The live `kanban-md` CLI exposes `list --json` and `log --action move
   --json`, and existing BearClaw tests already patch `subprocess.run` instead
   of spawning real tooling [S1, S3, S5, S6].

3. Rich assertions should be substring-based, not snapshot-based. Current CLI
   tests check for headers, representative values, and box-drawing characters,
   while Rich tables adapt layout to content and console width [S3, S8].

4. Age-in-status fixtures should encode "latest move into current status, else
   created timestamp." That rule is already established in the parent board
   research, and OwlBear's move-log parsing precedent confirms the `detail`
   payload shape is `from -> to` [S1, S4, S5].

5. Assignee fixtures should explicitly cover `assignee`, `claimed_by`, and no
   assignment. That ordering came from the parent board research and is easy to
   express with paired list/log JSON payloads in one RED file [S1, S3, S5].

6. Architecture fit is simple: add `tests/test_cli_board.py` and keep setup in
   tests. No source-code helper or reusable fixture module is required for #909
   itself; the current CLI layout already makes the public surface testable
   from the root app [S2, S3, S7].

7. A small follow-up task is justified after #909 and #910: if paired list/log
   JSON literals become noisy, extract a test-only helper rather than adding
   production abstractions. The local suite already uses small fixture builders,
   and the board seam needs two synchronized payloads instead of one [S3, S4,
   S5].

## 5. Recommendation (.93 confidence)

Use option B for #909: create `tests/test_cli_board.py`, invoke the root Typer
app with `CliRunner`, patch the board command's `subprocess.run`, and feed it
only `kanban-md list --json` plus `kanban-md log --action move --json`
payloads [S1, S3, S5, S6].

This keeps the RED task pinned to the user-facing contract:

- AC #1 and #5 stay at the CLI layer.
- AC #2 through #4 stay data-driven and deterministic.
- AC #6 is satisfied without temp board files or the real binary.
- #910 can implement against the exact seam already fixed here.

## 6. Follow-up Tasks

1. Existing #910 — Implement bearclaw board Rich table command
   Priority rationale: main GREEN task that consumes the RED contract from
   #909.
   Dependencies: follows #909 in the intended split.
   One-line AC: add a top-level `bearclaw board` command that consumes
   `kanban-md` JSON and renders the grouped Rich table.
   Existing task: #910.

2. #923 — Create reusable kanban JSON fixture helpers for BearClaw CLI board
   tests
   Priority rationale: optional cleanup once #909 and #910 land; reduces
   duplicated paired list/log payload literals without blocking delivery.
   Dependencies: depends on #909.
   One-line AC: add a test-only helper that builds paired `kanban-md list
   --json` and `kanban-md log --json` payloads for board-style CLI tests,
   including assignee fallback and latest-move age cases.
   Created: `kanban\kanban-md.exe create "Create reusable kanban JSON fixture
   helpers for BearClaw CLI board tests" ...`
