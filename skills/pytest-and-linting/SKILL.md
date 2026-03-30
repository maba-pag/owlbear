---
name: pytest-and-linting
description: "How to run pytest, ruff, and coverage in this project. Covers PS 5.1 piping pitfalls, correct flags, and file-capture fallback. Use when running tests or linting."
---

# Running Tests and Linters

This skill covers the **how** of running pytest, ruff, and coverage in OwlBear.
Each agent's primary skill covers **what** to test (scoping, AC verification).

## pytest — run plain, never pipe

For full test suite runs (auditor), use `isBackground=true` + `get_terminal_output` to avoid terminal corruption from long-lived VS Code sessions (stale output, truncation, KeyboardInterrupt from prior runs):

```powershell
# Background terminal — avoids corruption
run_in_terminal(command="uv run pytest tests/ -m 'not api' -q --tb=short", isBackground=true)
# Then: get_terminal_output(id=...)
```

For scoped runs (builder, reviewer, test-writer), foreground is fine:

`--import-mode=importlib` is set in `addopts` in `pyproject.toml` — no manual flag needed.

```powershell
# Scoped (builder, reviewer, test-writer)
uv run pytest tests/test_{module}.py -q --tb=short

# Full suite (auditor only)
uv run pytest tests/ packages/ -m "not api" -q --tb=short
```

`testpaths` in `pyproject.toml` is `["tests", "packages"]`, so bare `uv run pytest` also discovers `packages/`. Passing both paths explicitly is preferred for clarity and to avoid relying on implicit config when running from a subdir.

### asyncio_mode = strict

`asyncio_mode = "strict"` is set in `pyproject.toml`. Every async test **must** carry an explicit `@pytest.mark.asyncio` decorator — bare `async def test_*` functions will not be collected:

```python
import pytest

@pytest.mark.asyncio
async def test_something():
    ...
```

### norecursedirs = ["v1"]

`norecursedirs = ["v1"]` in `pyproject.toml` excludes the `v1/` directory from test discovery. Tests under `v1/` are never collected or run — this is intentional to keep the legacy codebase isolated.

The terminal tool captures stdout + stderr automatically (60 KB limit).
No piping needed.

## NEVER pipe `uv run` output through PowerShell cmdlets

PS 5.1 wraps stderr from `2>&1` in ErrorRecord objects. Every pipe combination
corrupts, truncates, or drops output. **All of these break — no exceptions:**

```powershell
# BAD — Out-File uses UTF-16LE, mangles output
uv run pytest ... 2>&1 | Out-File file.txt

# BAD — Out-String corrupts ErrorRecord objects
uv run pytest ... 2>&1 | Out-String

# BAD — Select-String drops non-matching lines
uv run pytest ... 2>&1 | Select-String "passed"

# BAD — Tee-Object has the same pipeline issues
uv run pytest ... 2>&1 | Tee-Object -Variable out

# BAD — ForEach-Object pipeline corruption
uv run pytest ... 2>&1 | ForEach-Object { $_ }

# BAD — redirect operator (UTF-16LE)
uv run pytest ... 2>&1 > file.txt

# BAD — [IO.File] with pipeline subexpression
[IO.File]::WriteAllText($p, (uv run pytest ... 2>&1 | Out-String), ...)
```

**Just run the command plain.** The terminal tool captures everything.

## File-capture fallback (truncated output)

If the terminal truncates output, use Python as the I/O layer:

```powershell
uv run python -c "import subprocess,sys,pathlib; r=subprocess.run([sys.executable,'-m','pytest','tests/','packages/','-m','not api','-q','--tb=line'], capture_output=True, text=True); pathlib.Path('docs/scratch/pytest-output.txt').write_text(r.stdout+'\n'+r.stderr); print('exit:', r.returncode)"
```

Then `read_file` on `docs/scratch/pytest-output.txt`. Delete after use.

## ruff — also run plain

```powershell
uv run ruff check packages/ tests/
```

## Coverage — bare `--cov` only

```powershell
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
```

`--cov-fail-under=0` overrides the global threshold for scoped runs.
Target >= 90% on touched modules.

**Flags that DO NOT WORK in this project:**

- `--cov=dotted.module.name` — pydantic MRO crash
- `--cov=packages/mcp-kanban/src/` — reports 0% (src-layout; use bare `--cov` instead)
- `coverage run --source=...` — incompatible with pytest-cov config

Only bare `--cov` works. It picks up `[tool.coverage.run] source_pkgs` from `pyproject.toml`, which lists all 7 installed package names: `owlbear`, `owlbear_orchestrator`, `owlbear_knowledge`, `owlbear_mcp_kanban`, `owlbear_mcp_knowledge`, `owlbear_mcp_project`, `owlbear_voice`. Coverage is measured across all of them automatically.

## Known hang: WMI + logfire pydantic plugin on Windows

CPython 3.12+ calls `_wmi.exec_query()` inside `platform.uname()` on Windows.
WMI queries have **no timeout** and can block indefinitely when the WMI service
is degraded (common under heavy parallel load — e.g., orchestration sessions).

logfire registers a pydantic plugin (`logfire.integrations.pydantic`) that calls
`platform.system()` at import time. Pydantic auto-loads plugins when constructing
any model, including `pydantic_settings.BaseSettings`. This makes every
`import pydantic_settings` hang when WMI is slow.

**Mitigation:** `tests/conftest.py` pre-populates the `platform.uname()` cache
in a daemon thread with a 3-second timeout, falling back to synthetic values from
`sys.platform` / `os.environ`. This runs before any pydantic imports.

**If pytest hangs despite the fix:** The WMI cache only works within a single
process. If `uv run pytest` spawns a subprocess or the conftest doesn't load
(e.g., wrong `testpaths`), the hang can recur. Also check for zombie processes
from prior runs:

```powershell
Get-Process python*,pytest* -ErrorAction SilentlyContinue | Stop-Process -Force
```

## Rich Console: required flags for CLI ANSI tests

When testing CLI commands that apply Rich styling (color, bold, etc.) with
`CliRunner`, the console must be created **inside** the command function (not at
module level) with both flags set explicitly:

```python
from rich.console import Console
console = Console(force_terminal=True, color_system="256")
```

- `force_terminal=True` — required so CliRunner output isn't treated as a pipe
- `color_system="256"` — required for 256-color sequences (`38;5;N`); without it
  Rich may auto-detect truecolor (`38;2;R;G;B`) or emit no color codes at all

A module-level `Console()` won't respect `FORCE_COLOR` injected by
`CliRunner.invoke(env=...)` because module constants are evaluated at import.

Tests asserting concrete ANSI sequences will fail if either flag is missing, even
when the styling logic is correct.

## pytest startup instability (Windows, scoped TDD runs)

If scoped pytest runs show plugin-load errors or incorrect async behavior, disable
auto-loading and explicitly list only the plugins you need:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
uv run pytest tests/test_{module}.py -q --tb=short -p pytest_asyncio.plugin
# With coverage:
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q -p pytest_asyncio.plugin -p pytest_cov
```

Restore before returning the terminal to foreground use: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=''`

## Test markers

OwlBear defines three project-level markers in `pyproject.toml`:

| Marker        | Meaning                                                                    |
| ------------- | -------------------------------------------------------------------------- |
| `api`         | Requires live API integrations or network services — skip in offline runs  |
| `slow`        | Long-running test — skip in fast-feedback loops                            |
| `integration` | Requires the `kanban-md` binary — deselect when it is not installed        |

**Common `-m` filter flags:**

```powershell
# Skip API tests (standard CI / builder run)
uv run pytest tests/ packages/ -m "not api" -q --tb=short

# Skip API and slow tests
uv run pytest tests/ packages/ -m "not api and not slow" -q --tb=short

# Run only integration tests
uv run pytest tests/ packages/ -m "integration" -q --tb=short
```

## Default flags

| Tool      | Default flags                                               |
| --------- | ----------------------------------------------------------- |
| pytest    | `-q --tb=short` (add `-v` only for specific test debugging) |
| ruff      | no extra flags needed                                       |
