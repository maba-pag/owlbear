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
