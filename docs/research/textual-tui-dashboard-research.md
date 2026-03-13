# Textual TUI Dashboard Evaluation

> **Owning task:** #633 — Evaluate Textual TUI dashboard for Phase 11+
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Task #633 (spawned from workflow-dashboards-devtools-research.md §3.5) asks: should OwlBear build a `bearclaw dashboard` TUI command using Textual? The prior research scored Textual at .55 confidence and deferred it. This deeper evaluation completes the ideation research checklist: theoretical validity, prior art, technical feasibility, architecture fit, LOC cost, and adopt/reject decision.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|:---------:|------|
| Textualize/textual v8.0 (34.7k stars) | <https://github.com/Textualize/textual> | .85 | Full TUI framework: reactive attrs, CSS layout, 40+ widgets, async-native, testing API |
| Textual reactivity guide | <https://textual.textualize.io/guide/reactivity/> | .80 | `reactive()`, watch methods, data binding, compute methods — the live-update mechanism |
| Textual layout guide | <https://textual.textualize.io/how-to/design-a-layout/> | .75 | Dock, FR units, containers, outside-in design — relevant to dashboard panel layout |
| darrenburns/posting (11.5k stars) | <https://github.com/darrenburns/posting> | .70 | Textual HTTP client TUI — real-world complexity reference (~6k LOC Python+SCSS) |
| tconbeer/harlequin (5.8k stars) | <https://github.com/tconbeer/harlequin> | .65 | Textual SQL IDE — large-scale Textual app, adapter plugins, DataTable usage |
| OwlBear workflow-dashboards research | `docs/workflow-dashboards-devtools-research.md` | .95 | Prior evaluation: Textual scored .55, Rich CLI scored .90, decision: defer TUI |
| OwlBear daemon.py | `src/owlbear/daemon.py` | .95 | Current daemon: in-memory OrchestratorState, HookRegistry, PidFile, no IPC |
| OwlBear cli.py | `src/bearclaw/cli.py` | .95 | Current status: rich.Panel display, file-based PID/config reads, no live data |

## 3. Analysis

### 3.1 Theoretical Validity

A TUI dashboard is a valid pattern for monitoring daemon systems (k9s for Kubernetes, lazygit for git, htop for processes). However, validity requires a **live data source**. OwlBear's daemon currently exposes zero runtime state externally — `OrchestratorState` and `HookRegistry` live in the daemon process memory only. The CLI reads static files (PID, config, active_project).

### 3.2 Infrastructure Gap: Event Stream

| Requirement | Current state | What's needed | LOC estimate |
|-------------|---------------|---------------|:---:|
| Daemon runtime state | In-memory `OrchestratorState` dataclass | IPC export (socket or file) | ~150 |
| Live hook events | `HookRegistry.emit()` in-process only | Event stream sink (socket or JSONL file) | ~100 |
| Usage stats | `UsageTracker` writes JSONL files | Already file-based — pollable | 0 |
| Kanban board | `kanban-md.exe` file-based | Already file-based — pollable | 0 |
| **Total IPC infra** | | | **~250** |

**Key finding:** The Textual app itself is straightforward. The real cost is the daemon-side event stream that doesn't exist yet.

### 3.3 LOC Cost Estimate

| Component | Description | LOC |
|-----------|-------------|:---:|
| Dashboard app class | `App` subclass, compose, CSS, keybindings | ~80 |
| Status panel widget | PID, uptime, project, model — poll PID file | ~60 |
| Task panel widget | DataTable of kanban tasks — poll kanban files | ~80 |
| Usage panel widget | Sparkline + table of recent usage — poll JSONL | ~70 |
| Agent activity log | RichLog widget — requires event stream | ~50 |
| Event stream client | Read from daemon IPC socket/file | ~60 |
| Daemon event stream server | Emit events from HookRegistry to IPC | ~150 |
| CLI entry point | `bearclaw dashboard` Typer command | ~20 |
| CSS file | Layout, colors, borders | ~40 |
| Tests (Textual pilot API) | App mount, widget content, key bindings | ~120 |
| **Total** | | **~730** |

### 3.4 Comparison: What You Get vs What It Costs

| Criterion | Textual TUI (.40) | Rich CLI status (.90) | Rich Live layout (.60) |
|-----------|:---:|:---:|:---:|
| New dependency | textual ~5MB | 0 (already transitive) | 0 |
| New infra needed | Daemon event stream IPC | None | Daemon event stream IPC |
| LOC cost | ~730 | ~185 (already mostly done) | ~400 |
| Live updates | Yes — reactive widgets | No — point-in-time snapshot | Yes — but dedicated terminal |
| User audience | 1 developer (laptop daemon) | 1 developer | 1 developer |
| Maintenance surface | Widget state, CSS, IPC protocol | Minimal | Moderate |
| KISS alignment | Low | Highest | Medium |
| YAGNI risk | High — no concurrent multi-agent yet | None | Medium |
| Testing complexity | Textual Pilot API (good but new) | Standard CLI assertions | Rich Console capture |

### 3.5 When a TUI Dashboard Becomes Justified

The value proposition flips when OwlBear has:

1. **Concurrent multi-agent orchestration** — multiple agents running simultaneously, need live progress for each
2. **Autonomous mode active** — poll-dispatch-reconcile loop running tasks without user input, need observability
3. **Long-running sessions** — daemon runs for hours, user wants glanceable status without typing commands

Currently: OwlBear runs single-agent, mostly interactive (CLI/Slack channel), with `autonomous_mode` defaulting to `False`. The `bearclaw status` rich Panel already covers the "what is the daemon doing?" question.

## 4. Recommendation (.35 confidence — defer/reject for now)

**Reject for Phase 11.** The Textual TUI is a solution looking for a problem that doesn't exist yet.

| Factor | Assessment |
|--------|-----------|
| Framework maturity | Excellent — Textual v8.0 is production-ready (posting, harlequin prove it) |
| Widget fit | Good — DataTable, Sparkline, RichLog, ProgressBar cover all panels |
| Reactive model | Excellent — `reactive()` + `watch_*` + `data_bind` handles live updates cleanly |
| Testing | Good — Textual's `Pilot` API enables programmatic UI testing |
| **Blocker: no event stream** | The daemon has no IPC mechanism. Building one solely for a TUI is unjustified |
| **Blocker: single user** | OwlBear is a laptop-resident single-user daemon. A TUI dashboard has 1 viewer |
| **YAGNI** | `bearclaw status --detail` + `kanban-md list --compact` already provide the information |

**Re-evaluate when:** (a) `autonomous_mode` is default-on and running concurrent tasks, or (b) a daemon event stream is built for other reasons (e.g., Slack live progress, error monitoring). At that point, the TUI becomes ~480 LOC on top of existing IPC — much cheaper.

**Risks if we built it now:**

| Risk | Severity | Why |
|------|----------|-----|
| IPC protocol churn | High | No other consumer — protocol would be designed speculatively |
| Maintenance burden | Medium | ~730 LOC + CSS + tests for 1 viewer |
| Textual version churn | Low | v8.0 is stable, but major versions have breaking changes |

## 5. Follow-up Tasks

No implementation tasks recommended at this time — defer is the recommendation. One housekeeping task to keep the option tracked:

```powershell
kanban\kanban-md.exe edit 633 --priority someday --body "## Research Complete\n\nSee docs/textual-tui-dashboard-research.md for full evaluation.\n\n**Decision: Defer (reject for Phase 11)** — .35 confidence.\n\nTextual v8.0 is production-ready and excellent for TUI dashboards (posting, harlequin prove it). However, OwlBear lacks the daemon event stream IPC needed for live updates, and single-user laptop operation makes a persistent TUI unjustified.\n\n**Re-evaluate when:**\n- autonomous_mode is default-on with concurrent tasks\n- A daemon event stream exists for other reasons (Slack progress, error monitoring)\n\n## Original AC\n- [x] Prototype feasibility: Textual can build this (LOC ~730 total)\n- [x] Layout: task panel + status panel + usage panel (DataTable + Sparkline + RichLog)\n- [x] Live updates: requires daemon event stream IPC (~250 LOC, doesn't exist)\n- [x] LOC cost vs value: ~730 LOC for 1 viewer with no concurrent agents — poor ROI\n- [x] Decision: defer with rationale"
```
