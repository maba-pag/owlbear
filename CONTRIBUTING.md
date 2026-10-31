# Contributing to OwlBear

This page is for developing OwlBear itself. To learn what OwlBear is and how to install it, read the
[README](README.md).

## Terms

| Term | Meaning |
| --- | --- |
| Agent | A Copilot role with a specific job, such as shaping, planning, building, or review |
| Skill | Reusable instructions that teach an agent how to handle a domain or workflow |
| MCP server | A tool connection that lets agents use one OwlBear capability from VS Code |
| Change | One approved piece of work tracked from its brief through review and publication |

## Branch and releases

`main` is the only long-lived branch: the development checkout and the branch consumers clone.
Pull requests reach `main` with the required `CI` check; versions are Git tags (`vMAJOR.MINOR`)
that the release workflow sets on merges labelled `release:minor` or `release:major`.

## Set up the checkout

Requirements: macOS, Python 3.14.8 (3.14 series only), [uv](https://docs.astral.sh/uv/), VS Code with
GitHub Copilot, [GitHub CLI](https://cli.github.com/), the GitHub Copilot CLI (`brew install --cask copilot-cli`),
and Git. JSON linting also needs the Node version pinned in `.nvmrc`. Install the Copilot CLI with
Homebrew rather than `npm install -g`, whose copy is hidden when the Node version changes.

```shell
git clone https://github.com/maba-pag/owlbear.git
cd owlbear
uv sync --locked --all-packages --all-groups
uv run dep-sync
```

`uv run dep-sync` reconciles the local Python and root npm (Biome) environments with the checked-out
manifests.

Open this checkout directly in VS Code. Its repository settings already load the shared
`share/` and project-local `.owlbear/` agent, skill, and instruction roots; do not run
consumer setup against the OwlBear checkout itself. The machine's running OwlBear lives in
`~/.owlbear/runtime`, separate from this checkout.

Run the repository checks:

```shell
uv run test --all
uv run lint --no-fix
```

## Choose a starting point

| You are changing... | Start with |
| --- | --- |
| Agents, skills, or instructions | [Shared ecosystem guide](share/README.md) |
| A runtime package or MCP server | [Package map](serve/README.md) |
| Consumer installation and verification | [Setup guide](setup/setup-guide.md) |
| Consumer operation, updates, or uninstall | [Operating OwlBear](setup/operating-owlbear.md) |

For package or shared-ecosystem changes, use the focused guide first, then run the scoped checks
for the paths you changed. `uv run test --all` and `uv run lint --no-fix` are the full development
checks. The guide for each surface owns its exact commands and validation.

## Where things live

| Path | Purpose |
| --- | --- |
| `serve/` | Runtime packages and the [package map](serve/README.md) |
| `share/` | Agents, skills, instructions, and their [loading model](share/README.md) |
| `setup/` | Installation in the [setup guide](setup/setup-guide.md), daily operation in [Operating OwlBear](setup/operating-owlbear.md), and teams in the [sharing guide](setup/sharing-guide.md) |
| `.owlbear/` | Tracked project authority plus host-local runtime state in the [.owlbear guide](.owlbear/README.md) |
| `tests/` | Workspace regression and integration tests described in the [test guide](tests/README.md) |
| `store/` | Reference-only knowledge corpus manifest described in the [store guide](store/README.md) |
| `.github/` | Development-only automation described in the [GitHub automation guide](.github/README-automation.md) |
