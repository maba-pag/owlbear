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

```powershell
uv run pytest tests/test_{module}.py -q --tb=short
```

### Full suite (auditor)

```powershell
uv run pytest tests/ packages/ -m "not api" -q --tb=short
```

For full suite runs, use `isBackground=true` + `get_terminal_output` to avoid terminal corruption from long-lived VS Code sessions:

```powershell
run_in_terminal(command="uv run pytest tests/ -m 'not api' -q --tb=short", isBackground=true)
# Then: get_terminal_output(id=...)
```

`testpaths` in `pyproject.toml` is `["tests", "packages"]`, so bare `uv run pytest` also discovers `packages/`. Passing both paths explicitly is preferred for clarity.

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

```powershell
# Skip API tests (standard builder run)
uv run pytest tests/ packages/ -m "not api" -q --tb=short

# Skip API and slow
uv run pytest tests/ packages/ -m "not api and not slow" -q --tb=short

# Only integration tests
uv run pytest tests/ packages/ -m "integration" -q --tb=short

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

## Coverage

```powershell
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
```

`--cov-fail-under=0` overrides the global threshold for scoped runs. Target >= 90% on touched modules.

### Flags that DO NOT WORK

| Flag | Problem |
|------|---------|
| `--cov=dotted.module.name` | pydantic MRO crash |
| `--cov=packages/mcp-kanban/src/` | Reports 0% (src-layout issue) |
| `coverage run --source=...` | Incompatible with pytest-cov config |

Only bare `--cov` works. It reads `[tool.coverage.run] source_pkgs` from `pyproject.toml`, covering all 8 installed packages automatically.

## ruff

```powershell
uv run ruff check packages/ tests/
```

## NEVER Pipe `uv run` Output Through PowerShell Cmdlets

The terminal tool captures stdout + stderr automatically (60 KB limit). No piping needed.

PS 5.1 wraps stderr from `2>&1` in ErrorRecord objects. Every pipe combination corrupts, truncates, or drops output — `Out-File`, `Out-String`, `Select-String`, `Tee-Object`, `ForEach-Object`, redirect operators, and `[IO.File]` with pipeline subexpressions all break.

**Just run the command plain.**

## File-Capture Fallback (Truncated Output)

If the terminal truncates output, use Python as the I/O layer:

```powershell
uv run python -c "import subprocess,sys,pathlib; r=subprocess.run([sys.executable,'-m','pytest','tests/','packages/','-m','not api','-q','--tb=line'], capture_output=True, text=True); pathlib.Path('docs/scratch/pytest-output.txt').write_text(r.stdout+'\n'+r.stderr); print('exit:', r.returncode)"
```

Then `read_file` on `docs/scratch/pytest-output.txt`. Delete after use.

## pytest Startup Instability (Windows)

If scoped pytest runs show plugin-load errors or incorrect async behavior, disable auto-loading:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
uv run pytest tests/test_{module}.py -q --tb=short -p pytest_asyncio.plugin
# With coverage:
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q -p pytest_asyncio.plugin -p pytest_cov
```

Restore before returning the terminal: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=''`

## Known Gotchas

- **WMI + logfire pydantic plugin hang on Windows.** CPython 3.12+ calls `_wmi.exec_query()` inside `platform.uname()`. WMI has no timeout and blocks indefinitely when degraded. logfire triggers this via `platform.system()` at pydantic import. **Mitigation:** `tests/conftest.py` pre-populates the `platform.uname()` cache in a daemon thread with a 3-second timeout. If pytest hangs despite the fix, the WMI cache only works within a single process — check for zombie processes: `Get-Process python*,pytest* -ErrorAction SilentlyContinue | Stop-Process -Force`.
- **Rich Console flags for CLI ANSI tests.** When testing CLI commands with Rich styling via `CliRunner`, the console must be created inside the command function with `Console(force_terminal=True, color-system="256")`. Module-level `Console()` ignores `FORCE_COLOR` from `CliRunner.invoke(env=...)`.
- **`asyncio_mode = strict` means bare `async def test_*` won't be collected.** Always add `@pytest.mark.asyncio`.
