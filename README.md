# OwlBear

On-demand AI development through semantic authority, reviewed delivery, and GitHub Copilot.

## Overview

OwlBear runs inside VS Code. A designer turns user intent into durable target authority, validates
the exact Specification revision, and admits it only after explicit approval. The Delivery engine
then acquires dependency-ready Planning and Build work under explicit capacity, gives each worker
bounded typed context, and applies only worker-owned transitions. Reviewers provide advisory
evidence; the runtime owns state, recovery, Integration, and completed history. MCP servers expose
that control plane plus Knowledge, Memory, and browser automation; Cockpit provides the human
operating and recovery surface.

The `dev` branch is the development workspace. The `main` branch is a generated consumer subset and
must not be edited directly. Immutable records from the retired workflow may remain under
`.owlbear/legacy/` as hash-verified history, but they are never runtime authority.

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `serve/` | Python runtime and MCP packages; Cockpit also contains its React source and consumer bundle |
| `share/agents/` | Copilot role definitions |
| `share/skills/` | Reusable workflows, rules, and handbooks |
| `share/instructions/` | Contextual instruction stubs and universal authority |
| `share/prompts/` | User-facing workflow entry points |
| `seed/` | Project-local templates copied by `setup/init.py` |
| `setup/` | Workspace initializer and installer documentation |
| `.owlbear/delivery/packages/` | Tracked authored Design packages and admitted contract authority |
| `.owlbear/delivery/runtime/` | Ignored host-local Delivery state, claims, transactions, and publications |
| `.owlbear/delivery/worktrees/` | Ignored Git worktrees owned per nonterminal Change |
| `.owlbear/legacy/` | Optional immutable legacy inventory, never executable state |
| `store/` | Knowledge and Memory data |
| `tests/` | Workspace regression and integration tests |

## Getting Started

Development requires Python 3.14+, [uv](https://docs.astral.sh/uv/), VS Code with GitHub Copilot,
and Git. The Cockpit frontend additionally requires the Node version pinned in
`serve/cockpit/web/.nvmrc`.

```shell
git clone -b dev https://github.com/OWNER/owlbear.git
cd owlbear
uv sync --all-extras
code .
```

Run the maintained development checks with `uv`:

```shell
uv run test --all
uv run lint --all --no-fix
```

Use `uv run help`, `uv run help tests`, or the shorthand `uv run help t` for focused command
guidance. Direct pytest and npm commands remain available for runner-specific debugging.

For consumer installation, configuration, Cockpit launch, and troubleshooting, use
[README-consumer.md](README-consumer.md) and [setup/setup-guide.md](setup/setup-guide.md). The setup
guide is the canonical command reference; this README intentionally does not duplicate it.

## License

MIT
