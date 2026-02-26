# kanban/

File-based task management for OwlBear, powered by [kanban-md](https://github.com/antopolskiy/kanban-md) v0.32.1.

## Setup

```powershell
.\kanban\setup.ps1
```

This downloads `kanban-md.exe` into this directory. The binary is gitignored.

## Folder layout

| Path | Purpose |
| --- | --- |
| `kanban-md.exe` | CLI/TUI binary (gitignored, fetch via `setup.ps1`) |
| `config.yml` | Board configuration — statuses, task directory |
| `tasks/` | One Markdown file per task (YAML frontmatter + body) |
| `setup.ps1` | Download script for `kanban-md.exe` |
| `activity.jsonl` | Auto-generated activity log |

## Quick reference

```powershell
kanban\kanban-md.exe board            # Open TUI board
kanban\kanban-md.exe list --compact   # List all tasks
kanban\kanban-md.exe show <id>        # Show task details
kanban\kanban-md.exe move <id> <status>  # Move task to status
```

For the full CLI reference, see [.github/skills/kanban-md/SKILL.md](../.github/skills/kanban-md/SKILL.md).
