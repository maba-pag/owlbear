# Workflow, Dashboards & Developer Tools

> **Owning task:** #583 — Research: Workflow, Dashboards & Developer Tools
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear's CLI (`bearclaw`) uses plain `typer.echo()` with hand-rolled ASCII table formatting. Daemon status is a single line (`running`/`not running`). Usage stats are a plain-text table. There is no live dashboard, no progress visualization, and no consolidated developer overview. What tooling would most improve the OwlBear developer experience, and what's the simplest useful integration?

**Prior OwlBear research consulted:** mission-control.md (cost tracking, §3.2), agent-observability.md (OTel/Logfire, §3–4), progress-reporting.md (ProgressReporter, §3–4), pinchtab.md (web dashboard rejected, §4), symphony.md (HTTP dashboard rejected).

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Textualize/rich (v14.3, 55.7k stars) | <https://github.com/Textualize/rich> | .90 | Tables, progress bars, panels, live display, tree, logging handler — zero-config terminal formatting |
| Textualize/textual (v8.0, 34.7k stars) | <https://github.com/Textualize/textual> | .75 | Full TUI framework (widgets, CSS, async, web-servable), built on Rich |
| otel-tui (826 stars) | <https://github.com/ymtdzzz/otel-tui> | .65 | Terminal OTel viewer — traces, metrics, logs in a Go TUI |
| darrenburns/posting (11.5k stars) | <https://github.com/darrenburns/posting> | .60 | Textual-based HTTP client TUI — reference for Textual app complexity |
| Rich progress docs | <https://rich.readthedocs.io/en/latest/progress.html> | .85 | Multi-task progress, indeterminate bars, transient display, nesting |
| OwlBear bearclaw CLI | `src/bearclaw/cli.py` | .95 | Current state: Typer + typer.echo, manual column formatting |
| OwlBear progress-reporting-research | `docs/research/progress-reporting.md` | .90 | Planned ProgressReporter via hooks + channel |
| Mission Control research | `docs/research/mission-control.md` | .85 | Cost/usage tracking, loop detection, compact board-state context |

## 3. Analysis

### 3.1 What's Missing Today

| Gap | Impact | Severity |
|-----|--------|----------|
| `bearclaw status` shows 1 line — no session info, no active task, no uptime | Can't tell what daemon is doing | High |
| `bearclaw usage` is a plain-text table — hard to scan, no color, no sparklines | Poor developer feedback loop | Medium |
| No live progress during daemon turns | Blind waiting during long operations | High |
| No consolidated "dashboard" view (tasks + status + usage) | Context switching between tools | Medium |
| CLI table output is hand-rolled (col-width math) | Maintenance burden, inconsistent formatting | Low |

### 3.2 Approach Options

| Option | Description | New dep | KISS | Complexity | Daemon compat |
|--------|-------------|---------|:----:|:----------:|:-----------:|
| **A. Rich-enhanced CLI** | Replace `typer.echo` tables with `rich.table`, add `rich.progress`, `rich.panel` for status | `rich` (0 transitive — already Typer's dep) | Highest | ~200 LOC | Full |
| **B. Textual TUI dashboard** | Full-screen terminal app with live widgets, layout panels, keybindings | `textual` (~5MB) | Medium | ~800+ LOC | Needs separate process |
| **C. Web dashboard (Streamlit/FastAPI)** | Browser-based real-time dashboard | `streamlit`/`fastapi` + frontend | Low | ~1500+ LOC | HTTP server in daemon |
| **D. Rich Live + Layout** | Rich's `Live` display with `Layout` for split-pane terminal dashboard | `rich` | High | ~400 LOC | Needs dedicated terminal |

### 3.3 Detailed Comparison

| Criterion | A. Rich CLI (.90) | B. Textual TUI (.55) | C. Web Dashboard (.20) | D. Rich Live (.70) |
|-----------|:-:|:-:|:-:|:-:|
| New dependencies | 0 (Rich is Typer transitive dep) | textual ~5MB | streamlit 100MB+ or fastapi+templates | 0 |
| Learning curve | Minimal (drop-in replacement) | CSS-like layout system, widget lifecycle | Frontend framework | Moderate (Layout API) |
| Works over SSH | Yes | Yes | No (needs browser) | Yes |
| Slack channel compatible | N/A (CLI only) | No | No | No |
| Integration effort | Replace `typer.echo` → `rich.print` | New entry point, new process | New server, new codebase | New `bearclaw dashboard` command |
| Maintenance burden | Very low | Medium (widget state management) | High (two codebases) | Low-medium |
| KISS alignment | Highest | Medium | Violates YAGNI | High |
| YAGNI risk | None — improves existing CLI | Medium — full TUI for single-user daemon | High — web UI for laptop daemon | Low |

**Key insight:** Rich is already a transitive dependency of Typer. OwlBear gets tables, progress bars, panels, trees, syntax highlighting, and logging handlers at zero additional dependency cost.

### 3.4 Rich-Enhanced CLI: Specific Improvements

| Feature | Rich API | OwlBear integration point | LOC estimate |
|---------|----------|---------------------------|:---:|
| Formatted tables | `rich.table.Table` | Replace `_print_usage_table()`, `project_list` | ~30 |
| Enhanced status | `rich.panel.Panel` + `rich.table` | New `bearclaw status --detail` | ~60 |
| Progress bars | `rich.progress.Progress` | ProgressReporter via CLIChannel | ~40 |
| Colored output | `rich.console.Console` | Replace `typer.echo` in key commands | ~20 |
| Tree view | `rich.tree.Tree` | `bearclaw knowledge-source list` hierarchy | ~20 |
| Logging handler | `rich.logging.RichHandler` | `setup_logging()` in daemon | ~10 |
| Error tracebacks | `rich.traceback.install()` | Global in CLI entry point | ~5 |

**Total: ~185 LOC of changes across existing code — no new modules needed.**

### 3.5 Textual TUI: When It Makes Sense

Textual becomes justified when OwlBear needs a persistent interactive terminal view — e.g., a `bearclaw dashboard` command that shows live task progress, agent status, and usage metrics simultaneously. This is a "Phase 11+" feature per the architecture roadmap. For now, Rich-enhanced CLI output covers 90% of the developer experience gap at 10% of the cost.

### 3.6 Rejected Approaches (with rationale)

| Approach | Rejection reason | Prior research |
|----------|-----------------|----------------|
| Web dashboard (Streamlit/FastAPI) | Violates YAGNI for single-laptop daemon; adds HTTP server complexity | pinchtab §4, symphony §3, mission-control §3.3 |
| Textual TUI now | Over-engineered for current CLI-and-Slack interaction model; revisit when daemon needs persistent monitoring | — |
| Custom OTel dashboard | otel-tui exists but requires separate Go binary + OTLP exporter config | observability §4 (Layer 2: opt-in) |

## 4. Recommendation (.90 confidence)

**Phase 1 (now): Rich-enhanced CLI output.** Replace hand-rolled ASCII tables with `rich.table.Table`, add `rich.panel.Panel` for `bearclaw status --detail`, wire `rich.progress.Progress` into the planned ProgressReporter, and install `rich.traceback` for better error display. Zero new deps (Rich is already available via Typer). ~185 LOC.

**Phase 2 (future): Textual TUI dashboard.** When the daemon needs persistent live monitoring (concurrent tasks, multi-agent orchestration), build a `bearclaw dashboard` command using Textual. This is a Phase 11+ concern per architecture.md.

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary approach | Rich-enhanced CLI | Zero deps, highest KISS, covers 90% of gaps |
| Table formatting | `rich.table.Table` | Drop-in replacement for hand-rolled columns |
| Status display | `rich.panel.Panel` + structured data | Shows daemon PID, uptime, active task, session info |
| Progress display | `rich.progress.Progress` | Integrates with planned ProgressReporter (#298) |
| Logging | `rich.logging.RichHandler` | Better daemon log readability |
| Tracebacks | `rich.traceback.install()` | Global, 1-line setup |
| TUI | Deferred to Phase 11+ | YAGNI for current single-user CLI model |
| Web dashboard | Rejected | YAGNI, violates architecture principles |

**Risks:**

| Risk | Severity | Mitigation |
|------|----------|------------|
| Rich output breaks piping (`bearclaw usage \| grep`) | Medium | Use `Console(force_terminal=...)` or `--no-color` flag |
| Rich markup in non-terminal contexts (Slack) | Low | Rich formatting only in CLIChannel, not ChannelPlugin base |
| Over-formatting simple output | Low | Use Rich only for tables/progress/status — leave simple echo for confirmations |

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Replace hand-rolled CLI tables with rich.table.Table" --priority needed --tags "phase-cli,scope:cli,cli" --body "Replace _print_usage_table() and project_list hand-rolled column formatting with rich.table.Table. Rich is already a transitive dep of Typer (zero new deps). Add --no-color flag support via Console(force_terminal=...). See docs/research/workflow-dashboards-devtools.md S4.\n\nAC:\n- [ ] bearclaw usage output uses rich.table.Table\n- [ ] bearclaw project list uses rich.table.Table\n- [ ] --no-color flag disables Rich formatting\n- [ ] Piped output auto-disables color (Console auto-detection)\n- [ ] Tests verify table output content"

kanban\kanban-md.exe create "Enhanced bearclaw status with rich.panel" --priority important --tags "phase-cli,scope:cli,cli" --body "Extend bearclaw status to show: daemon PID, uptime, active project, active channel, last session timestamp, session count. Use rich.panel.Panel for display. Add --detail flag for verbose output. See docs/research/workflow-dashboards-devtools.md S3.4 and S4.\n\nAC:\n- [ ] bearclaw status shows PID, uptime, active project\n- [ ] bearclaw status --detail adds session info, channel, last activity\n- [ ] Output uses rich.panel.Panel with colored status indicators\n- [ ] Falls back to plain text when --no-color is set\n- [ ] Tests verify status output fields"

kanban\kanban-md.exe create "Add rich.traceback and RichHandler to daemon logging" --priority nice-to-have --tags "phase-cli,scope:core,cli" --body "Install rich.traceback.install() in bearclaw CLI entry point for better error display. Replace daemon setup_logging() handler with rich.logging.RichHandler for structured log output. See docs/research/workflow-dashboards-devtools.md S3.4.\n\nAC:\n- [ ] rich.traceback.install() called in CLI app callback\n- [ ] Daemon logs use RichHandler with timestamp and level coloring\n- [ ] Log file output remains plain text (no ANSI codes in log files)\n- [ ] Tests verify logging setup"

kanban\kanban-md.exe create "Evaluate Textual TUI dashboard for Phase 11+" --priority someday --tags "research,scope:cli,phase-11" --body "When OwlBear reaches concurrent multi-agent orchestration, evaluate building a bearclaw dashboard command using Textual. Track: live task progress, agent states, usage metrics, knowledge source status in split-pane TUI. Deferred per YAGNI analysis in docs/research/workflow-dashboards-devtools.md S3.5.\n\nAC:\n- [ ] Prototype bearclaw dashboard with Textual\n- [ ] Layout: task panel + status panel + usage panel\n- [ ] Live updates via daemon event stream\n- [ ] Evaluate LOC cost vs value"
```

## 6. Attribution Updates

| Source | URL | License | What | Where Used | Date |
|--------|-----|---------|------|------------|------|
| Textualize/rich | <https://github.com/Textualize/rich> | MIT | Terminal formatting library: tables, progress, panels, tracebacks | `docs/research/workflow-dashboards-devtools.md` | 2026-03-07 |
| Textualize/textual | <https://github.com/Textualize/textual> | MIT | TUI framework evaluation for future dashboard | `docs/research/workflow-dashboards-devtools.md` | 2026-03-07 |
| otel-tui | <https://github.com/ymtdzzz/otel-tui> | Apache-2.0 | Terminal OTel viewer — evaluated for observability display | `docs/research/workflow-dashboards-devtools.md` | 2026-03-07 |
| Rich progress docs | <https://rich.readthedocs.io/en/latest/progress.html> | MIT | Multi-task progress bar patterns | `docs/research/workflow-dashboards-devtools.md` | 2026-03-07 |
