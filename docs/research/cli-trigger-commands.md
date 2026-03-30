# CLI Trigger Commands — Research Findings

> **Owning task:** #22 — Build CLI trigger commands
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #22 requires CLI commands (`owlbear dispatch <id>`, `owlbear run [--all]`,
`owlbear status`) that trigger orchestrator dispatch. The CLI replaces v1's always-on
daemon with on-demand invocation.

Key questions: (1) Typer vs click? (2) Where does the CLI live in the package layout?
(3) How to handle async dispatch from sync CLI commands? (4) What's the testing strategy?
(5) How does the #20 dependency affect development order?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|:---------:|
| S1 | Typer docs (main + testing + subcommands) | <https://typer.tiangolo.com/> | .95 |
| S2 | Click docs (main + testing) | <https://click.palletsprojects.com/en/stable/> | .90 |
| S3 | Typer PyPI (v0.24.1, deps) | <https://pypi.org/project/typer/> | .85 |
| S4 | Click PyPI (v8.3.1) | <https://pypi.org/project/click/> | .80 |
| S5 | v1 CLI split research (docs/research/cli-split.md) | local | .90 |
| S6 | Existing orchestrator code (acp_client.py, process_supervisor.py) | local | .95 |
| S7 | Dispatch planner research (docs/research/build-dispatch-planner.md) | local | .90 |
| S8 | voice package entry point (owlbear_voice/main.py, pyproject.toml) | local | .85 |

## 3. Analysis

### 3.1 Framework Comparison

| Criterion | Typer (.85) | Click (.70) |
|-----------|-------------|-------------|
| Type hints | Native — params from type annotations [S1] | Decorator-based `@click.option` [S2] |
| Dependencies | 3 (click + rich + shellingham) [S3] | 0 additional [S4] |
| Testing | `typer.testing.CliRunner` (wraps Click's) [S1] | `click.testing.CliRunner` [S2] |
| Async support | None native — `asyncio.run()` wrapper [S1] | None native — same pattern [S2] |
| v1 precedent | v1 used Typer (bearclaw/cli.py) [S5] | Click is Typer's foundation [S3] |
| Rich output | Built-in — formatted errors, tables [S3] | Manual — needs separate rich dep |
| Shell completion | Auto via shellingham [S3] | Manual setup [S2] |
| Subcommands | `app.add_typer()` — proven in v1 [S5] | `@group.command()` [S2] |
| KISS alignment | High — less boilerplate per command | Medium — more explicit but verbose |
| Python 3.12+ fit | Excellent — type hints are the interface | Good — decorator-based |

### 3.2 Package Layout

The orchestrator package exports two namespace packages [S6]:
- `owlbear` — domain logic (errors, voice, future planner)
- `owlbear_orchestrator` — infrastructure (acp_client, process_supervisor)

CLI is a user-facing domain concern. It belongs in `owlbear`:

```
packages/orchestrator/src/owlbear/cli.py    # Typer app + commands (~150 LOC)
```

Entry point in `packages/orchestrator/pyproject.toml`:
```toml
[project.scripts]
owlbear = "owlbear.cli:app"
```

This follows the voice package pattern (`owlbear-voice = "owlbear_voice.main:main"`) [S8].
Single file — v1's multi-file split was for 1200 LOC across 10 concerns [S5]; v2 CLI
has 4 commands and should stay in one file per KISS.

### 3.3 Async Wrapping Pattern

AcpClient methods are async [S6]. Typer/Click commands are sync. Standard pattern:

```python
@app.command()
def dispatch(task_id: int) -> None:
    asyncio.run(_dispatch(task_id))

async def _dispatch(task_id: int) -> None:
    # planner + AcpClient logic here
```

This is the same pattern used in v1 for async commands (auth, voice, browser, chat,
daemon all used `asyncio.run()`) [S5]. No framework supports async commands natively —
both Typer and Click require this wrapper.

### 3.4 Command Architecture

| Command | Planner needed? | ACP needed? | Can build without #20? |
|---------|:-:|:-:|:-:|
| `owlbear status` | No — reads board via kanban-md | No | Yes |
| `owlbear dispatch <id>` | Yes — gate checks, agent selection | Yes | No |
| `owlbear run` | Yes — task selection | Yes | No |
| `owlbear run --all` | Yes — loop | Yes | No |

Finding: `owlbear status` has zero dependency on #20. It calls `kanban-md.exe list`
directly and formats output. The other 3 commands depend on: (a) planner module for
board reading/gate checking/task selection (#144, #145), (b) AcpClient + orchestrator
loop for dispatch (#146, #19).

### 3.5 Dependency Graph Update

Current: `#22 depends_on: [20]`. Task #20 is an umbrella for #144, #145, #146.
The CLI needs:
- Planner models + board reader (#144) — for `dispatch` and `run`
- Gate checker + task selector (#145) — for `run` to pick the right task
- Orchestrator loop (#146) — for `dispatch` and `run` to invoke ACP

All three subtasks must complete before `dispatch`/`run` are functional. The current
`depends_on: [20]` correctly captures this since #20 verifies all subtasks.

### 3.6 Testing Strategy

Typer's `CliRunner` enables clean unit testing [S1]:
- **Argument parsing:** invoke with various arg combos, check exit codes and output
- **Status command:** mock `subprocess.run` for kanban-md, test formatted output
- **Dispatch/run:** mock planner and AcpClient, verify correct calls
- **Error handling:** test no-Copilot, no-tasks, already-claimed scenarios

No real kanban-md.exe or Copilot CLI needed for unit tests.

### 3.7 Error Handling Design

| Error | Detection | User message |
|-------|-----------|-------------|
| No Copilot CLI | `shutil.which("copilot") is None` | "Copilot CLI not found. Install: gh extension install github/gh-copilot" |
| No actionable tasks | Planner returns empty plan | "No actionable tasks on the board." |
| Task already claimed | kanban-md returns claim info | "Task #{id} is already claimed by {agent}." |
| Task not found | kanban-md returns error | "Task #{id} not found." |
| ACP failure | AcpClientError with category | Category-appropriate message (retry/escalate) |

## 4. Recommendation (.85 confidence)

**Typer** — type-hint ergonomics, v1 precedent, rich output built-in, clean testing.
The extra deps (rich, shellingham) are acceptable for a CLI tool. Click would work but
adds boilerplate without benefit.

**Module placement:** Single `owlbear/cli.py` file with `[project.scripts]` entry point.
No multi-file split needed for 4 commands.

**Async pattern:** `asyncio.run()` wrappers — standard, proven in v1.

**Risk:** Typer pulls rich + shellingham (~5MB total). Mitigated: these are CLI-only
deps and provide genuine UX value (formatted tables, auto-completion).

## 5. Follow-up Tasks

Task #22 is validated as-is. No new decomposition needed — the AC is well-scoped.
One recommended refinement for the architect:

```
kanban\kanban-md.exe create "Add Typer dependency to orchestrator package" --priority needed --status ideation --tags "phase-2,scope:cli,type:config" --body "## Objective\nAdd typer>=0.24 to packages/orchestrator/pyproject.toml dependencies.\n\n## Acceptance Criteria\n- [ ] typer>=0.24 added to [project.dependencies] in packages/orchestrator/pyproject.toml\n- [ ] uv lock succeeds with the new dependency\n- [ ] uv run python -c 'import typer' works\n\n## Context\nPrerequisite for #22 (CLI trigger commands). Separated as config task so #22 can focus on implementation. See docs/research/cli-trigger-commands.md."
```
