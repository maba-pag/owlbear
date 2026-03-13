# OwlBear

Always-on, laptop-resident AI development system.

## Overview

OwlBear receives user intent (via CLI, Slack, or voice), plans work, executes it
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
bearclaw slack auth                    # validate Slack tokens
bearclaw slack test                    # send test message to configured channel
bearclaw slack status                  # show Slack config and connection state
bearclaw project create -n NAME [-w PATH]  # create a project (default: CWD)
bearclaw project new NAME [--template T]   # scaffold a new project from template
bearclaw project list [--all]              # list projects (--all includes archived)
bearclaw project switch NAME               # switch active project
bearclaw project archive NAME              # archive a project
bearclaw status [--detail]                  # show daemon status (--detail for config info)
bearclaw chat [--project NAME]             # interactive REPL (--project scopes sessions)
bearclaw knowledge-source add --name N --type TYPE [opts]  # register a knowledge source
bearclaw knowledge-source list [--scope S]                 # list registered sources
bearclaw knowledge-source show NAME                        # show source details
bearclaw knowledge-source remove NAME                      # delete a source
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
uv run pytest tests/ -m "not api" --tb=short -q   # run tests
uv run ruff check src/ tests/  # lint
uv run ruff format --check     # format check
```

## License

MIT
