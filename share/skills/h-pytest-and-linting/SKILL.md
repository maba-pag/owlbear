---
name: h-pytest-and-linting
description: "Handbook: pytest, ruff, and coverage commands — flags, pitfalls, and recipes"
user-invocable: false
---

# pytest, ruff, and coverage Reference

Command reference, configuration, and troubleshooting for running tests and linters in the OwlBear workspace.

For Python coding conventions and test patterns, see `h-python-conventions`.

## pytest Commands

### Scoped runs (builder, reviewer, test-writer)

```shell
uv run pytest tests/test_{module}.py -q --tb=short
```

### Full suite (auditor)

Run against your test directory and your source package directory.
> Example (OwlBear-dev): `tests/` and `serve/`

```shell
uv run pytest tests/ path/to/source-packages/ -m "not api" -q --tb=short
```

For full suite runs, use `mode=async` to avoid output truncation in long-lived terminal sessions. The agent is automatically notified when the command finishes — no manual polling needed:

```shell
run_in_terminal(command="uv run pytest tests/ -m 'not api' -q --tb=short", mode=async)
# Agent receives automatic notification on completion
# Then: get_terminal_output(id=...) to retrieve the output
# If the terminal needs input: send_to_terminal(id=..., data="...")
```

`testpaths` in `pyproject.toml` should include both your tests and source packages. Bare `uv run pytest` may already discover both, but passing explicit paths is preferred for clarity.

### Default flags

| Tool | Default flags |
|------|---------------|
| pytest | `-q --tb=short` (add `-v` only for specific debugging) |
| ruff | no extra flags needed |

## Test Markers

| Marker | Meaning |
|--------|---------|
| `api` | Requires live API / network — skip in offline runs |
| `slow` | Long-running — skip in fast-feedback loops |
| `integration` | Requires `kanban-md` binary — deselect when not installed |
| `e2e` | Requires `gh` CLI on PATH; spawns real Copilot agent — expensive |

`e2e` tests are excluded from the default run via `addopts = "-m 'not e2e'"` in `pyproject.toml`.

### Common `-m` filter recipes

```shell
# Skip API tests (standard builder run)
uv run pytest tests/ path/to/source-packages/ -m "not api" -q --tb=short

# Skip API and slow
uv run pytest tests/ path/to/source-packages/ -m "not api and not slow" -q --tb=short

# Only integration tests
uv run pytest tests/ path/to/source-packages/ -m "integration" -q --tb=short

# Run e2e explicitly
uv run pytest -m e2e -q --tb=short
```

## pytest Configuration (pyproject.toml)

| Setting | Value | Effect |
|---------|-------|--------|
| `import-mode` | `importlib` | Set in `addopts` — no manual flag needed |
| `asyncio_mode` | `strict` | Every async test **must** carry `@pytest.mark.asyncio` |
| `norecursedirs` | `["v1"]` | Excludes `v1/` from test discovery |
| `testpaths` | `["tests", "packages"]` | Discovers tests in both locations |
| `timeout` | `30` | Per-test timeout via `pytest-timeout` — kills any single test exceeding 30s |
| `session_timeout` | `300` | Whole-session timeout — kills the entire pytest run after 5 minutes |

## Coverage

```shell
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
```

`--cov-fail-under=0` overrides the global threshold for scoped runs. Target >= 90% on touched modules.

### Flags that DO NOT WORK

| Flag | Problem |
|------|---------|
| `--cov=dotted.module.name` | pydantic MRO crash |
| `--cov=path/to/package/src/` | Reports 0% in src-layout setups |
| `coverage run --source=...` | Incompatible with pytest-cov config |

Only bare `--cov` works. It reads `[tool.coverage.run] source_pkgs` from `pyproject.toml`, covering all 8 installed packages automatically.

## ruff

```shell
uv run ruff check path/to/source-packages/ tests/
```

## NEVER Pipe `uv run` Output Through PowerShell Cmdlets

The terminal tool captures stdout + stderr automatically (60 KB limit). No piping needed.

PS 5.1 wraps stderr from `2>&1` in ErrorRecord objects. Every pipe combination corrupts, truncates, or drops output — `Out-File`, `Out-String`, `Select-String`, `Tee-Object`, `ForEach-Object`, redirect operators, and `[IO.File]` with pipeline subexpressions all break.

**Just run the command plain.**

## File-Capture Fallback (Truncated Output)

If the terminal truncates output, use Python as the I/O layer:

```shell
uv run python -c "import subprocess,sys,pathlib; r=subprocess.run([sys.executable,'-m','pytest','tests/','path/to/source-packages/','-m','not api','-q','--tb=line'], capture_output=True, text=True); pathlib.Path('.owlbear/scratch/pytest-output.txt').write_text(r.stdout+'\n'+r.stderr); print('exit:', r.returncode)"
```

Then `read_file` on `.owlbear/scratch/pytest-output.txt`. Delete after use.

## pytest Startup Instability (Windows)

If scoped pytest runs show plugin-load errors or incorrect async behavior, disable auto-loading:

```shell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
uv run pytest tests/test_{module}.py -q --tb=short -p pytest_asyncio.plugin -p xdist -n 0
# With coverage:
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q -p pytest_asyncio.plugin -p pytest_cov -p xdist -n 0
```

`-p xdist` is required because `addopts` contains `-n auto --dist loadfile` — without the plugin loaded those flags cause `unrecognized arguments`. `-n 0` overrides xdist parallelism for scoped runs.

Restore before returning the terminal: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=''`

> **Preferred alternative:** Instead of disabling all plugins, selectively disable the known-bad logfire plugins:
>
> ```shell
> uv run pytest tests/test_{module}.py -p no:logfire -p no:pytest_logfire -q --tb=short
> ```
>
> This keeps all other plugins (xdist, cov, asyncio) working from autoload.

## Known Gotchas

- **ruff `# noqa` on multiline function signatures must go on the `def` line.** For complexity-rule suppression (e.g., `# noqa: C901`), the comment must appear on the line containing `def`, not on a continuation line. Placing it on a parameter or return-type line is silently ignored by ruff. (Evidence: task 1064 builder)

- **Stale pytest cache in retry cycles.** When running tests in a 2nd or 3rd builder/reviewer attempt, `.pytest_cache` can return cached results from prior runs, causing agents to report incorrect totals — e.g., "0 failed" when a test is actually failing. Two independent occurrences observed in the same sprint (#857 reviewer pass 2, #871 builder cycles 2–3). **Mitigation:** In any retry cycle, clear the cache before running: `Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue; uv run pytest ...` — or add `-p no:cacheprovider` to the pytest command. Never trust a self-reported "N passed, 0 failed" in a retry cycle without cross-checking against terminal output.

- **WMI + logfire pydantic plugin hang on Windows.** CPython 3.12+ calls `_wmi.exec_query()` inside `platform.uname()`. WMI has no timeout and blocks indefinitely when degraded. logfire triggers this via `platform.system()` at pydantic import. **Mitigation:** `tests/conftest.py` pre-populates the `platform.uname()` cache in a daemon thread with a 3-second timeout. If pytest hangs despite the fix, the WMI cache only works within a single process — check for zombie processes: `Get-Process python*,pytest* -ErrorAction SilentlyContinue | Stop-Process -Force`.
- **Rich Console flags for CLI ANSI tests.** When testing CLI commands with Rich styling via `CliRunner`, the console must be created inside the command function with `Console(force_terminal=True, color-system="256")`. Module-level `Console()` ignores `FORCE_COLOR` from `CliRunner.invoke(env=...)`.
- **`asyncio_mode = strict` means bare `async def test_*` won't be collected.** Always add `@pytest.mark.asyncio`.
