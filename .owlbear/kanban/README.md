# kanban/

File-based task management for OwlBear, powered by the native kanban engine.

## Folder layout

| Path | Purpose |
| --- | --- |
| `config.yml` | `next_id` checkpoint (topology is product-defined) |
| `tasks/` | One Markdown file per task (YAML frontmatter + body) |
| `activity.jsonl` | Auto-generated activity log |

## Usage

Tasks are managed via the `owlbear-kanban` MCP server. See `share/skills/h-mcp-kanban/SKILL.md` for the full tool reference.
