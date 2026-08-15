---
name: h-pytest-and-linting
description: "Handbook: pytest, ruff, and coverage commands — flags, pitfalls, and recipes"
user-invocable: false
---

# pytest, ruff, and coverage Reference

Command reference and pitfalls for tests and linting. For Python conventions and test patterns, see `h-python-conventions`.

## Discover Project Configuration

Before constructing a command, inspect the nearest applicable configuration and workspace files:

1. `pyproject.toml`, `pytest.ini`, `tox.ini`, or `setup.cfg` for `testpaths`, `addopts`, markers,
   coverage sources, and Ruff settings.
2. Package or workspace manifests for source roots and package boundaries.
3. Lockfiles and project documentation for the configured runner: `uv run`, Poetry, Hatch, tox,
   nox, or the active virtual environment.
4. The changed path or failing test for the narrowest relevant package and test target.

Use these placeholders below:

| Placeholder | Meaning |
|-------------|---------|
| `{project-runner}` | Configured execution prefix, such as `uv run`, `poetry run`, or empty in an active environment |
| `{focused-test}` | One test file, node ID, or package-local test target |
| `{test-roots}` | Configured test directories; omit when pytest `testpaths` already provides complete discovery |
| `{source-roots}` | Maintained Python source directories from project configuration or package manifests |

Do not assume `serve/`, `src/`, `tests/`, or `packages/` exists. OwlBear itself uses `uv run`; that is
a verified local runner, not a requirement for consuming projects.

## Command Templates

### Scoped

```shell
{project-runner} pytest {focused-test} -q --tb=short
```

### Full suite

```shell
{project-runner} pytest {test-roots} -q --tb=short
```

Omit `{test-roots}` when configured discovery is authoritative. Add marker expressions only after
reading the project's marker definitions; do not copy another repository's exclusions.

### With coverage

```shell
{project-runner} pytest {focused-test} --cov --cov-report=term-missing -q --tb=short
```

Prefer the coverage source and threshold already configured by the project. Do not add a temporary
threshold that contradicts CI or claim package coverage from an unrelated focused test.

### ruff

```shell
{project-runner} ruff check {source-roots} {test-roots}
```

When Ruff's configured include/exclude rules cover the repository correctly, `ruff check .` is
acceptable. For focused validation, pass only the changed Python files or owning package.

### Default flags

| Tool | Flags |
|------|-------|
| pytest | `-q --tb=short` (add `-v` only for debugging) |
| ruff | none needed |

## No Piping

The terminal tool captures stdout and stderr. Run test and lint commands directly; do not pipe an
interactive or potentially prompting command through `tee`, `tail`, `grep`, or another filter.

## File-Capture Fallback

When direct output is actually truncated, use the discovered project runner and its Python
interpreter as the I/O layer. Write temporary output under OwlBear's supplied scratch directory.

```shell
{project-runner} python -c "import subprocess,sys,pathlib; r=subprocess.run([sys.executable,'-m','pytest','{focused-test}','-q','--tb=line'], capture_output=True, text=True); pathlib.Path('.owlbear/scratch/pytest-output.txt').write_text(r.stdout+'\n'+r.stderr); print('exit:', r.returncode)"
```

Read `.owlbear/scratch/pytest-output.txt` then delete it.

## General Gotchas

- **Stale cache in retry cycles.** `.pytest_cache` can return cached results from prior runs, causing incorrect totals. In retries, clear first: `rm -rf .pytest_cache` or add `-p no:cacheprovider`.

- **ruff `# noqa` placement.** On multiline signatures, `# noqa: C901` must go on the `def` line, not continuation lines.

- **Async tests.** Read the configured async plugin and mode. Under `pytest-asyncio` strict mode, bare
  `async def test_*` functions require `@pytest.mark.asyncio`.

## OwlBear Workspace Notes

Apply these only when the target is the OwlBear repository or matching configuration is verified:

| Command | Scope |
|---------|-------|
| `uv run test` or `uv run test --all` | Complete Python and Cockpit frontend unit-test suites |
| `uv run test [PATH ...]` | Tests owning the explicit paths; routes to pytest and/or Vitest |
| `uv run test-e2e [SPEC ...]` | Cockpit maintained fast Playwright gate |
| `uv run lint` | Normal local lint aggregate on the workspace; `--staged` selects staged files |
| `uv run lint-cockpit` | Cockpit frontend lint aggregate |
| `uv run megalint` | Standalone MegaLinter on the workspace; safe fixes by default, or check-only with `--no-fix` |
| `uv run lint-full` | `lint` plus MegaLinter |
| `uv run format-full` | Python, whitespace, and final-newline formatters |
| `uv run typecheck-cockpit` | Cockpit frontend TypeScript check |
| `uv run quality-full` | Format, lint-full, typecheck-cockpit, then advisory TODO scan |

Use these workspace entry points instead of invoking individual linters manually. `lint` and
`megalint` may auto-fix files through their configured safe fixers; inspect the diff afterward.
MegaLinter's repository policy is `APPLY_FIXES: all` by default, while `--no-fix` explicitly selects
a check-only run. Agents should
scope validation to their own work with `lint --staged`; workspace-wide `lint`, `megalint`, and
`lint-full` are broad user workflows rather than focused agent validation commands.

`lint`, `lint-cockpit`, `megalint`, `lint-full`, and `quality-full` accept one optional fix-policy
flag. `--no-fix` replaces mutating hooks with check-only equivalents. `--unsafe-fix` enables Ruff
unsafe fixes and Stylelint lax fixes in addition to the configured safe fixes. The two flags are
mutually exclusive; review the resulting diff whenever unsafe fixes are enabled. Full
aggregates are listed by `uv run help quality`.

| Marker | Local meaning |
|--------|---------------|
| `api` | Requires live network; routine local runs exclude it with `-m "not api"` |
| `slow` | Long-running |
| `integration` | Requires the `kanban-md` binary |
| `e2e` | Excluded by default through `addopts`; include explicitly with `-m e2e` |

- **Runner.** Use `uv run`; bare system Python does not resolve OwlBear workspace dependencies.
- **Direct runner debugging.** Raw `uv run pytest` and package-owned npm scripts remain valid when
  debugging runner-specific behavior or passing options not modeled by the maintained wrappers.
- **Coverage.** Bare `--cov` reads `source_pkgs` from `pyproject.toml`. Locally observed explicit
  module/path forms can conflict with Pydantic instrumentation or report misleading zero coverage.
- **Timeouts.** `pytest-timeout` uses the values configured in OwlBear's `pyproject.toml`; inspect the
  current file rather than copying numeric limits.
- **Plugin auto-loading disabled.** Some VS Code terminal sessions export
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. This hides `pytest-xdist`, `pytest-cov`, `pytest-asyncio`, and
  `pytest-timeout`, breaking configured plugin flags. Use the workspace interpreter and explicitly
  load only the configured plugins when this environment variable is present.

### MegaLinter reports

When analyzing `uv run megalint` or CI results, start with the structured report at
`megalinter-reports/mega-linter-report.json`. Use `megalinter-reports/linters_logs/` for raw
per-linter output and `megalinter-reports/megalinter-report.sarif` for code-scanning findings;
console output is primarily progress and diagnostic context.

### Windows-Only Notes

These are observed OwlBear workspace workarounds for Windows with PowerShell:

- **Startup instability.** If scoped runs show plugin errors, set `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'` then add `-p pytest_asyncio.plugin -p xdist -n 0`. Or selectively disable logfire: `-p no:logfire -p no:pytest_logfire`.

- **WMI + logfire hang.** CPython 3.12+ `platform.uname()` calls WMI which can hang indefinitely. `conftest.py` has a workaround. If pytest still hangs: `Get-Process python*,pytest* | Stop-Process -Force`.

- **PowerShell piping.** PS 5.1 wraps stderr in ErrorRecord objects. All pipe combinations corrupt output.
