# Replace Hand-Rolled CLI Tables with rich.table.Table

> **Owning task:** #630 — Replace hand-rolled CLI tables with rich.table.Table
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

BearClaw CLI has 3 table-formatting sites that duplicate a ~15-line col-width pattern. Task #520 proposed extracting a `_print_table` helper; task #630 supersedes that by replacing the hand-rolled formatting with `rich.table.Table`. Is this the right approach, and what's the implementation plan?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|:---------:|------|
| Rich Tables docs | <https://rich.readthedocs.io/en/latest/tables.html> | .95 | `Table.add_column()`, `add_row()`, `add_section()`, `box` styles, `Column` options |
| Rich Console docs | <https://rich.readthedocs.io/en/latest/console.html> | .90 | Auto terminal detection, `is_terminal`, strips ANSI when piped, `NO_COLOR` env var |
| OwlBear parent research #583 | `docs/research/workflow-dashboards-devtools.md` §3.4 | .90 | Rich is transitive dep (0 new deps), ~30 LOC for table replacement |
| Rich GitHub repo | <https://github.com/Textualize/rich> | .85 | 55.7k stars, v14.3, mature stable API |
| OwlBear CLI source | `src/bearclaw/cli.py` L135–170, L439–475, L568–620 | .95 | 3 hand-rolled table sites |
| Typer testing docs | <https://typer.tiangolo.com/tutorial/testing/> | .80 | CliRunner captures stdout; Rich Console picks up patched stdout when created inside command |

## 3. Analysis

### 3.1 Call-Site Inventory

| # | Function | Lines | Headers | Has Footer | Complexity |
|---|----------|:-----:|:-------:|:----------:|:----------:|
| 1 | `project_list()` | L149–170 | Name, Workspace, Last Active, Status | No | Simple |
| 2 | `ks_list()` | L453–475 | Name, Type, Scope, Enabled, Last Refreshed | No | Simple |
| 3 | `_print_usage_table()` | L568–620 | Model, Requests, Input/Output/Total Tokens, Est. Cost, [Premium] | Yes (TOTAL row + separator) | Dynamic columns |

All 3 sites share the identical pattern: compute `col_widths` → build `fmt` string → `typer.echo(fmt.format(*row))`.

### 3.2 Approach Comparison

| Criterion | A. rich.table.Table (.90) | B. _print_table helper (.65) | C. tabulate lib (.40) |
|-----------|:------------------------:|:----------------------------:|:---------------------:|
| New dependencies | 0 (Rich is Typer transitive) | 0 | +1 (`tabulate`) |
| LOC removed | ~45 (3 sites × 15) | ~30 (DRY but same logic) | ~45 |
| LOC added | ~35 (3 call-sites + 0 helpers) | ~15 (helper) + ~9 (call-sites) | ~25 + dep |
| Auto column sizing | Built-in | Manual (kept) | Built-in |
| Color/styling support | Built-in | None | None |
| Pipe-safe auto-detection | Built-in (`is_terminal`) | Manual (N/A) | N/A |
| `NO_COLOR` respects | Built-in (env var standard) | N/A | N/A |
| Totals separator | `table.add_section()` | Custom footer param | N/A |
| KISS | High (replace pattern with API) | Medium (DRY but reinvents) | Low (new dep for solved problem) |

### 3.3 Testing Strategy

**Key concern:** CliRunner replaces `sys.stdout` during `invoke()`. Rich Console must be created *inside* the command function (not at module level) to pick up the patched stdout.

| Approach | Works with CliRunner? | Effort |
|----------|:---------------------:|:------:|
| `Console()` created inside command → `console.print(table)` | Yes — picks up replaced stdout | Lowest |
| Module-level `console = Console()` | **No** — grabs real stdout before runner patches it | — |
| `rich.print(table)` (uses default Console) | Risky — default Console may be cached | — |

**Recommended:** Create `Console()` inside each command function, or pass `file=sys.stdout` explicitly.

**Test assertion impact:** Existing tests check for content substrings (`"gpt-4o"`, `"Name"`, `"Premium"`, `"$"`, `"Listed"`, etc.). Rich renders these strings inside table cells — they remain present in output. No existing assertions need to change. Rich strips ANSI codes under non-terminal CliRunner, so `result.output` contains clean text with Unicode box-drawing characters.

### 3.4 Console Pattern: Shared vs Inline

| Pattern | Pros | Cons | Verdict |
|---------|------|------|:-------:|
| Inline `Console()` per call-site | Simple, CliRunner-safe | Repeated construction | **Use this** |
| Shared `_console()` factory function | DRY | Extra abstraction for 3 sites | Overkill (YAGNI) |
| Module-level `console` | DRY | **Breaks CliRunner test capture** | Reject |

### 3.5 Pipe Behavior

Rich Console auto-detects non-terminal output and strips ANSI escape sequences. Box-drawing characters (Unicode) remain but are harmless for `grep`/`awk`. The `NO_COLOR` env var is respected. No additional code needed for pipe safety — this is strictly better than the hand-rolled approach (which outputs plain ASCII but has no color support either).

## 4. Recommendation (.90 confidence)

Replace all 3 hand-rolled table sites with `rich.table.Table`. Create `Console()` inline in each command. Use `table.add_section()` for the usage totals separator. Close #520 as superseded.

**Risk:** Box-drawing Unicode characters in piped output could surprise users expecting pure ASCII. Mitigation: use `box=box.SIMPLE` for a lighter look, or accept Rich's default `box.HEAVY_HEAD` which is standard for modern CLIs. Low risk — Rich is used by thousands of CLIs.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement rich.table.Table in bearclaw CLI" --priority needed --status todo --tags "phase-cli,scope:cli,cli" --body "Replace hand-rolled table formatting in project_list(), ks_list(), and _print_usage_table() with rich.table.Table. Create Console() inline in each command (not module-level) for CliRunner compatibility. Use table.add_section() for usage totals. See docs/research/rich-table-cli.md.\n\nAC:\n- [ ] project_list() uses rich.table.Table\n- [ ] ks_list() uses rich.table.Table\n- [ ] _print_usage_table() uses rich.table.Table with add_section() for totals\n- [ ] Console() created inside command functions (not module-level)\n- [ ] Piped output auto-disables ANSI (Console auto-detection)\n- [ ] All existing test assertions pass unchanged\n- [ ] ruff clean"

kanban\kanban-md.exe edit 520 --status done --body "Superseded by #630 → rich.table.Table approach. See docs/research/rich-table-cli.md."

kanban\kanban-md.exe move 630 backlog
```
