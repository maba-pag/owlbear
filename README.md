# OwlBear

On-demand AI development through semantic authority, reviewed delivery, and GitHub Copilot.

## Overview

OwlBear runs inside VS Code. A designer turns user intent into durable target authority, validates
the exact revision, and admits it only after explicit approval. The delivery engine then selects
independently reviewed plan, build, and conditional assembly transformations, with finite correction
routing when review does not accept a claim. MCP servers expose the control plane, Knowledge,
Memory, and browser automation; Cockpit provides the human operating surface.

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
| `.owlbear/target/` | Receipt-authorized semantic authority, runtime evidence, and immutable receipts |
| `.owlbear/target-cutover-request.json` | Exact activation request required by the target runtime |
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

Run Python checks with `uv`:

```shell
uv run pytest tests/ serve/ -m "not api" -q --tb=short
uv run ruff check serve/ tests/
```

For consumer installation, configuration, Cockpit launch, and troubleshooting, use
[README-consumer.md](README-consumer.md) and [setup/setup-guide.md](setup/setup-guide.md). The setup
guide is the canonical command reference; this README intentionally does not duplicate it.

## License

MIT
