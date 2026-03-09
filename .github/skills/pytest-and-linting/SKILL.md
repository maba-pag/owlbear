---
name: pytest-and-linting
description: "How to run pytest, ruff, and coverage in this project. Covers PS 5.1 piping pitfalls, correct flags, and file-capture fallback. Use when running tests or linting."
---

# Running Tests and Linters

This skill covers the **how** of running pytest, ruff, and coverage in OwlBear.
Each agent's primary skill covers **what** to test (scoping, AC verification).

## pytest — run plain, never pipe

```powershell
# Scoped (builder, reviewer, test-writer)
uv run pytest tests/test_{module}.py -q --tb=short

# Full suite (auditor only)
uv run pytest tests/ -m "not api" -q --tb=short
```

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
uv run python -c "import subprocess,sys,pathlib; r=subprocess.run([sys.executable,'-m','pytest','tests/','-m','not api','-q','--tb=line'], capture_output=True, text=True); pathlib.Path('docs/scratch/pytest-output.txt').write_text(r.stdout+'\n'+r.stderr); print('exit:', r.returncode)"
```

Then `read_file` on `docs/scratch/pytest-output.txt`. Delete after use.

## ruff — also run plain

```powershell
uv run ruff check src/ tests/
```

## Coverage — bare `--cov` only

```powershell
uv run pytest tests/test_{module}.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
```

`--cov-fail-under=0` overrides the global threshold for scoped runs.
Target >= 90% on touched modules.

**Flags that DO NOT WORK in this project:**

- `--cov=dotted.module.name` — pydantic MRO crash
- `--cov=src/owlbear/{dir}/` — reports 0% (src-layout)
- `coverage run --source=...` — incompatible with pytest-cov config

Only bare `--cov` works. It picks up `[tool.coverage.run] source` from `pyproject.toml`.

## Default flags

| Tool      | Default flags                                               |
| --------- | ----------------------------------------------------------- |
| pytest    | `-q --tb=short` (add `-v` only for specific test debugging) |
| ruff      | no extra flags needed                                       |
