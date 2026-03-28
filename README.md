# OwlBear

Always-on, laptop-resident AI development system.

## Overview

OwlBear receives user intent (via CLI, Slack, or voice), plans work, executes it
autonomously, and delivers results — with human approval gates for destructive or
publishing actions. It owns the full build pipeline from ideation through delivery
and operates as a standalone daemon process.

## Prerequisites

- **Python ≥ 3.12**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Windows** is the primary development OS; Linux and macOS are expected to work but untested

> **Browser automation** is designed for corporate Windows laptops. It attaches to an
> existing Edge session over CDP rather than launching a new browser, so it requires no
> admin rights, no browser extensions, and no separate unmanaged browser install.
> See [docs/research/browser-automation.md](docs/research/browser-automation.md) for details.

## Quick Start

```bash
uv sync                        # install dependencies
uv run bearclaw --help         # show CLI help
uv run bearclaw auth login     # start Copilot OAuth device flow
```

## Bootstrap a New Project

`scripts/setup.py` wires an existing project directory to OwlBear. Run it once
from inside the target project — it auto-detects the owlbear installation from
the script's own location:

```bash
# From the target project directory (owlbear cloned at ../owlbear):
cd my-project
python ../owlbear/scripts/setup.py
```

What it creates:

| Artifact | Behaviour |
|---|---|
| `.vscode/settings.json` | Adds agent, skill, and instruction discovery paths pointing to owlbear. Merges with any existing keys. |
| `.vscode/mcp.json` | Registers the three owlbear MCP servers (kanban, knowledge, project). Skipped if already exists. |
| `kanban/config.yml` + `kanban/tasks/` | Copies config from owlbear with `next_id` reset to 1. Skipped if config already exists. |
| `kanban/setup.ps1` | Copied from owlbear so you can download `kanban-md.exe` in the new project. |
| `data/knowledge/` | Creates the knowledge directory. |
| `.github/copilot-instructions.md` | Stub instructions file pre-filled with the project name. Skipped if already exists. |

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
bearclaw slack auth                    # validate Slack tokens
bearclaw slack test                    # send test message to configured channel
bearclaw slack status                  # show Slack config and connection state
bearclaw project create -n NAME [-w PATH]  # create a project (default: CWD)
bearclaw project new NAME [--template T]   # scaffold a new project from template
bearclaw project list [--all]              # list projects (--all includes archived)
bearclaw project switch NAME               # switch active project
bearclaw project archive NAME              # archive a project
bearclaw board                             # display kanban board grouped by status
bearclaw status [--detail]                  # show daemon status (--detail for config info)
bearclaw chat [--project NAME]             # interactive REPL (--project scopes sessions)
bearclaw knowledge-source add --name N --type TYPE [opts]  # register a knowledge source
bearclaw knowledge-source list [--scope S]                 # list registered sources
bearclaw knowledge-source show NAME                        # show source details
bearclaw knowledge-source remove NAME                      # delete a source
bearclaw decisions list                    # list pending decision requests
bearclaw decisions show TASK_ID            # display a pending decision by task ID
bearclaw decisions resolve TASK_ID         # interactively resolve a decision
```

## Slack Integration

OwlBear uses Slack as its messaging channel. Socket Mode provides real-time
messaging over an outbound WebSocket — no public endpoint or tunnel required.

### Quick Setup

1. **Create a free Slack workspace** at [slack.com/create](https://slack.com/create)
2. **Create a Slack app** at [api.slack.com/apps](https://api.slack.com/apps) — use the manifest below for quick setup
3. **Enable Socket Mode** — App Settings → Socket Mode → toggle on
4. **Generate an app-level token** — Basic Information → App-Level Tokens → create with `connections:write` scope (prefix: `xapp-`)
5. **Add bot scopes** — OAuth & Permissions → add `chat:write`, `im:history`, and `files:write`
6. **Install to workspace** — OAuth & Permissions → Install to Workspace → copy Bot User OAuth Token (prefix: `xoxb-`)
7. **Subscribe to events** — Event Subscriptions → Subscribe to bot events → add `message.im`

### App Manifest

Use this manifest when creating your app for quick setup:

```yaml
display_information:
  name: OwlBear
  description: AI development assistant
features:
  bot_user:
    display_name: OwlBear
    always_online: true
oauth_config:
  scopes:
    bot:
      - chat:write
      - im:history
      - files:write
settings:
  event_subscriptions:
    bot_events:
      - message.im
  socket_mode_enabled: true
```

### Configuration

Set these environment variables (or add to `.env`):

```bash
OWLBEAR_SLACK_APP_TOKEN=xapp-...   # app-level token for Socket Mode
OWLBEAR_SLACK_BOT_TOKEN=xoxb-...   # bot token for Web API
OWLBEAR_SLACK_CHANNEL_ID=C...      # channel ID for outgoing messages
```

### CLI Commands

```bash
bearclaw slack auth      # validate tokens via auth.test API
bearclaw slack test      # send a test message to the configured channel
bearclaw slack status    # show token configuration and connection state
```

For architecture details and implementation rationale, see
[docs/research/slack-integration.md](docs/research/slack-integration.md).

## Architecture

- **Runtime:** Standalone daemon, started via BearClaw CLI
- **Agents:** PydanticAI with structured output and dependency injection
- **LLM:** GitHub Copilot API (device-flow OAuth)
- **Config:** pydantic-settings with env var overrides (`OWLBEAR_` prefix)
- **Knowledge:** SQLite knowledge graph + Qdrant hybrid vector search (BGE-M3)

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
```

### Testing

```bash
# Run all tests (root tests/ and all packages/*/tests/)
uv run pytest tests/ packages/ -m "not api" --tb=short -q

# Run with coverage
uv run pytest tests/ packages/ --cov --cov-report=term-missing -q

# Run a specific package
uv run pytest packages/orchestrator/tests/ -q
```

### Linting

```bash
uv run ruff check packages/ tests/   # lint all packages and tests
uv run ruff format --check           # format check
```

## License

MIT
