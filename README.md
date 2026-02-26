# OwlBear

Always-on, laptop-resident AI development system.

## Overview

OwlBear receives user intent (via CLI, Teams, or voice), plans work, executes it
autonomously, and delivers results — with human approval gates for destructive or
publishing actions. It owns the full build pipeline from ideation through delivery
and operates as a standalone daemon process.

## Quick Start

```bash
uv sync                        # install dependencies
uv run bearclaw --help         # show CLI help
uv run bearclaw auth login     # start Copilot OAuth device flow
```

## CLI — BearClaw

BearClaw is the command-line interface for OwlBear. All user interaction starts
here: authentication, task management, and daemon control.

```bash
bearclaw --version       # print version
bearclaw auth login      # authenticate with GitHub Copilot
bearclaw auth status     # check token status
bearclaw browser start [--port 9222]   # launch Edge with CDP debug port
bearclaw browser stop                  # stop tracked browser
bearclaw browser status [--port 9222]  # check CDP connection
```

## Architecture

- **Runtime:** Standalone daemon, started via BearClaw CLI
- **Agents:** PydanticAI with structured output and dependency injection
- **LLM:** GitHub Copilot API (device-flow OAuth)
- **Config:** pydantic-settings with env var overrides (`OWLBEAR_` prefix)
- **Knowledge:** Knowledge graph + vector DB (planned)

VS Code remains the IDE for interactive work; OwlBear and VS Code share the
filesystem (code, kanban board, sessions) as the integration point.

See [docs/architecture.md](docs/architecture.md) for the full system design.

## Inspiration

- [HKUDS/nanobot](https://github.com/HKUDS/nanobot) — MessageBus, Tool ABC, progressive skills
- [openclaw/openclaw](https://github.com/openclaw/openclaw) — agent loop, ChannelPlugin, hooks
- [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) — hook patterns, safety guards

See [docs/sources.md](docs/sources.md) for full attribution.

## Development

```bash
uv sync --all-extras           # install with dev dependencies
uv run pytest tests/ -m "not api" --tb=short -q   # run tests
uv run ruff check src/ tests/  # lint
uv run ruff format --check     # format check
```

## License

MIT
