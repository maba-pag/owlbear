# OwlBear

On-demand AI development system built on GitHub Copilot.

## Overview

OwlBear receives user intent, plans work, and executes it through Copilot agent
workflows. VS Code is the IDE; OwlBear and VS Code share the filesystem as the
integration point.

## Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **[VS Code](https://code.visualstudio.com/)** with the GitHub Copilot extension

## Quick Start

```bash
git clone -b dev https://github.com/OWNER/owlbear.git
cd owlbear
uv sync
```

> **Branches:** `dev` is the working branch (full workspace). `main` is the consumer-facing branch — auto-synced product subset, never committed to directly.

Open VS Code with `code .`.

## Directory Layout

| Directory                 | Purpose                                                |
|---------------------------|--------------------------------------------------------|
| `serve/browser/`          | Web content extraction library (authenticated via Edge CDP) |
| `serve/cockpit/`          | Steering Cockpit — browser UI for kanban board management |
| `serve/knowledge/`        | Knowledge engine (graph + vector)                      |
| `serve/kanban/`           | Kanban engine (transport-free; used by mcp-kanban)     |
| `serve/memory/`           | Memory primitives — models, errors, and storage (used by mcp-memory and cockpit) |
| `serve/mcp-browser/`      | MCP server for authenticated web content fetching      |
| `serve/mcp-kanban/`       | MCP server wrapping kanban operations                  |
| `serve/mcp-knowledge/`    | MCP server exposing knowledge operations               |
| `serve/mcp-memory/`       | MCP server for persistent agent memory (file-based) |
| `serve/tools/`            | Workspace utility scripts — `doc-index` CLI            |
| `share/agents/`           | Agent definitions (`.agent.md`)                        |
| `share/skills/`           | Agent skills (`SKILL.md`, agentskills.io style)        |
| `share/instructions/`     | Shared instruction files (`*.instructions.md`)         |
| `share/prompts/`          | User-facing one-shot prompt files (`*.prompt.md`)      |
| `.owlbear/`               | Project ops data: kanban board, decisions, research, sources, scratch, scripts, hooks |
| `tests/`                  | Integration and unit test suite                        |
| `store/`                  | Knowledge and memory data                              |
| `seed/`                   | Template files copied to new projects by `setup/init.py` |
| `setup/`                  | Workspace initialiser (`init.py`), setup guide, sharing guide |

## How It Works

**Agents** in `share/agents/` appear in VS Code's agent picker, each owning a pipeline
stage (research → architect → test-writer → builder → reviewer → writer → auditor).

**Skills** in `share/skills/` auto-load by relevance, carrying domain knowledge and
reusable workflows for each agent role.

**MCP servers** (`mcp-kanban`, `mcp-knowledge`, `mcp-memory`) expose the kanban
board, knowledge base, and persistent agent memory as tools inside VS Code.

## Cockpit

The Steering Cockpit is a browser-based UI for managing the kanban board.

Developer workflow (source build in `dev`):

```bash
cd serve/cockpit/web && npm run build && cd -
uv run cockpit
```

Requires Node `>=24.15.0` (see `serve/cockpit/web/package.json`) and npm for the
frontend package in `serve/cockpit/web/`. All non-frontend packages in this repository
still use `uv`.

Cockpit frontend quality commands (run from `serve/cockpit/web/`):

```bash
npm test
npm run test:e2e
npm run lint:css
npm run lint:html
npm run build
```

`uv run cockpit` starts the server on `http://127.0.0.1:8420` and opens it in the
default browser. The kanban directory defaults to `.owlbear/kanban/` relative to CWD.

Release packaging boundary:

- `dev` keeps frontend source at `serve/cockpit/web/` for development and quality checks.
- `main` ships prebuilt `serve/cockpit/dist/` for consumers; consumers launch with
  `uv run cockpit` and do not need Node/npm.

| Variable | Default | Purpose |
|----------|---------|--------|
| `COCKPIT_PORT` | `8420` | Override listen port (1–65535) |
| `COCKPIT_NO_OPEN` | — | Set to `1` to suppress browser auto-open |
| `KANBAN_DIR` | `.owlbear/kanban/` | Override kanban directory path |

## Knowledge Base

Knowledge base sources are registered and refreshed via the MCP server tools (`knowledge_sources_register`, `knowledge_sources_refresh`). See `serve/mcp-knowledge/README.md` for the full tool reference.

Set `OWLBEAR_LOCAL_KB_PATH` to override the default `.owlbear/knowledge/local.db` location (`OWLBEAR_KB_PATH` is still accepted as a fallback).

## Doc Index

Generate or update the workspace documentation index at `.owlbear/doc-index.md`:

```bash
uv run doc-index
```

Skips regeneration when the index is newer than all collected docs. Override output path with `--output <path>` (must stay inside workspace root).

## Development

```bash
uv sync --all-extras
uv run pytest tests/ serve/ -m "not api" -q --tb=short
uv run pytest tests/ serve/ -m "not api" -q --tb=short --cov --cov-report=term-missing
uv run ruff check serve/ tests/
```

## Pre-commit Hooks

Two local hooks guard agent and skill file quality:

- **`validate-skills`** — runs on every commit, validates all `share/skills/*/SKILL.md` frontmatter.
- **`validate-agents`** — runs when any `share/agents/*.agent.md` file is staged, checking for:
  - Bare `todo` (instead of `todos`) in the `tools:` list
  - Stale `resolveMemoryFileUri` tool references anywhere in the file

### VS Code auto-staging trap

VS Code silently re-serializes and re-stages `.agent.md` files when it detects new
tool capabilities (e.g. `execute/runTask`, `execute/testFailure`). This can revert
manual edits before commit. Always run `git diff --cached share/agents/` before committing
and unstage any auto-generated reverts with `git reset HEAD <file>`.

## License

MIT
