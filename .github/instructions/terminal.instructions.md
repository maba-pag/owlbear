---
applyTo: "**"
description: "Terminal output handling — prevent wasted tool calls from re-running commands"
---

# Terminal Output Handling

## First-call discipline

Get the invocation right the first time. Never re-run a command just to see different output or try a different piping strategy.

## Concise flags by default

| Tool       | Default flags                                               |
| ---------- | ----------------------------------------------------------- |
| pytest     | `-q --tb=short` (add `-v` only for specific test debugging) |
| ruff       | no extra flags needed                                       |
| kanban-md  | `--compact` for `list`, `board`, `metrics`, `log`           |
| git status | `--short`                                                   |
| git log    | `--oneline -N` (where N is the number of entries you need)  |
| git diff   | `--stat` first, then full diff on specific files if needed  |

## Prefer dedicated tools over terminal

- **Testing:** Always use `uv run pytest` in the terminal. Do NOT use the `runTests` tool —
  it funnels through a single VS Code execution queue and deadlocks when multiple agents
  run tests in parallel. Always scope to specific files:
  ```powershell
  uv run pytest tests/test_{module}.py -q --tb=short
  ```
- **Linting:** No dedicated tool exists — terminal `uv run ruff check` is correct.
- **Errors:** Use `get_errors` to read the VS Code Problems panel.

## Do not fence output with Write-Host

Do NOT wrap commands in `Write-Host` markers:

```powershell
# BAD — wastes tokens, the terminal tool already reports exit codes
Write-Host "=== RUFF ==="; uv run ruff check src/; Write-Host "=== EXIT: $LASTEXITCODE ==="

# GOOD — just run the command
uv run ruff check src/ tests/
```

The terminal tool reports exit codes automatically. Extra `Write-Host` fencing adds noise.

## Long output strategy

When a command might produce more than a screenful of output:

1. **Redirect to scratch file**, then read the file:

```powershell
uv run pytest tests/ -m "not api" -q --tb=short 2>&1 | Out-File docs/scratch/pytest-output.txt
# Then use read_file on docs/scratch/pytest-output.txt
```

2. **Never use `Select-Object`** to truncate terminal output — if output is too long, redirect to a file instead.

3. **Delete scratch files after use** — they are ephemeral.

## PowerShell specifics

- Chain commands with `;` — never `&&`.
- Use `Out-String` when piping to avoid object-rendering issues.
- Prefer PowerShell cmdlets (`Get-ChildItem`, `Test-Path`) over aliases in scripts.
