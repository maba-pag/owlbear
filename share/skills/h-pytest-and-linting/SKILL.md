---
name: h-pytest-and-linting
description: "Handbook: pytest, ruff, and coverage commands — flags, pitfalls, and recipes"
user-invocable: false
---

# pytest, ruff, and coverage Reference

Command reference and pitfalls for tests and linting. For Python conventions and test patterns, see `h-python-conventions`.

## Commands

### Scoped

```shell
uv run pytest tests/test_{module}.py -q --tb=short
```

### Full suite

```shell
uv run pytest tests/ serve/ -m "not api" -q --tb=short
```

Use `mode=async` for full suite runs — output exceeds the 60 KB terminal capture limit:

```shell
run_in_terminal(command="uv run pytest tests/ serve/ -m 'not api' -q --tb=short", mode=async)
```

### With coverage

```shell
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
```

Only bare `--cov` works — `--cov=module.name` crashes pydantic, `--cov=path/` reports 0%. Coverage reads `source_pkgs` from `pyproject.toml`.

### ruff

```shell
uv run ruff check serve/ tests/
```

### Default flags

| Tool | Flags |
|------|-------|
| pytest | `-q --tb=short` (add `-v` only for debugging) |
| ruff | none needed |

## Markers

| Marker | Meaning |
|--------|---------|
| `api` | Requires live network — exclude with `-m "not api"` |
| `slow` | Long-running — exclude with `-m "not slow"` |
| `integration` | Requires `kanban-md` binary |
| `e2e` | Excluded by default via `addopts`; include explicitly with `-m e2e` |

## No Piping

The terminal tool captures stdout + stderr (60 KB limit). Never pipe output — no `| tee`, `2>&1 | cat`, `> file.log`, no redirect operators. **Run commands plain.**

## File-Capture Fallback

When terminal output is truncated, use `uv run python` as the I/O layer. **`uv run python` is load-bearing** — it resolves to `.venv` with all project dependencies. Bare `python3` or heredocs (`python3 << 'EOF'`) resolve to system Python which lacks project packages.

```shell
uv run python -c "import subprocess,sys,pathlib; r=subprocess.run([sys.executable,'-m','pytest','tests/','serve/','-m','not api','-q','--tb=line'], capture_output=True, text=True); pathlib.Path('.owlbear/scratch/pytest-output.txt').write_text(r.stdout+'\n'+r.stderr); print('exit:', r.returncode)"
```

Read `.owlbear/scratch/pytest-output.txt` then delete it.

## Gotchas

- **Stale cache in retry cycles.** `.pytest_cache` can return cached results from prior runs, causing incorrect totals. In retries, clear first: `rm -rf .pytest_cache` or add `-p no:cacheprovider`.

- **ruff `# noqa` placement.** On multiline signatures, `# noqa: C901` must go on the `def` line, not continuation lines.

- **`asyncio_mode = strict`.** Bare `async def test_*` won't be collected — always add `@pytest.mark.asyncio`.

- **Timeouts.** `pytest-timeout` kills individual tests after 30s and the entire session after 300s (configured in `pyproject.toml`).

- **Plugin auto-loading disabled.** Some VS Code terminal sessions export `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. This hides `pytest-xdist`, `pytest-cov`, `pytest-asyncio`, and `pytest-timeout`, breaking `addopts` flags like `-n auto --dist loadfile`. Fix: use `.venv/bin/pytest` and explicitly load plugins: `-p xdist.plugin -p pytest_cov -p pytest_asyncio.plugin -p pytest_timeout`.

## Windows-Only Pitfalls

These apply only when running on Windows with PowerShell.

- **Startup instability.** If scoped runs show plugin errors, set `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'` then add `-p pytest_asyncio.plugin -p xdist -n 0`. Or selectively disable logfire: `-p no:logfire -p no:pytest_logfire`.

- **WMI + logfire hang.** CPython 3.12+ `platform.uname()` calls WMI which can hang indefinitely. `conftest.py` has a workaround. If pytest still hangs: `Get-Process python*,pytest* | Stop-Process -Force`.

- **PowerShell piping.** PS 5.1 wraps stderr in ErrorRecord objects. All pipe combinations corrupt output.
