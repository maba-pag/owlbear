# OwlBear

This is the OwlBear development checkout. OwlBear gives GitHub Copilot a reliable path from an idea
to a reviewed change on a Mac, combining a Delivery engine that serves every project on the machine
with reusable agent instructions and tools for memory, knowledge, browser access, and human review.

If you want to know what OwlBear is or how to install it in a project, read
[README-consumer.md](README-consumer.md). That file owns the product story, the requirements, and
the install path.

## Choose your path

| You are here to... | Start here |
| --- | --- |
| Decide whether OwlBear fits your work | [README-consumer.md](README-consumer.md) |
| Install OwlBear and add a project | [Setup guide](setup/setup-guide.md) |
| Develop OwlBear itself | [Develop OwlBear](#develop-owlbear) |
| Find a runtime package or MCP server | [Package map](serve/README.md) |
| Change agents, skills, prompts, or instructions | [Shared ecosystem guide](share/README.md) |
| Share one setup with teammates | [Sharing guide](setup/sharing-guide.md) |

## What OwlBear does

You describe an outcome. Copilot helps shape it into a brief you approve, and OwlBear runs the
result through reviewed steps. OwlBear runs once per Mac, started with the `owlbear` command, and
its pages (Changes, Backlog, Memory, Settings, Maintenance) show each Change and give a person the
controls for approvals, answers, merge consent and pausing.

OwlBear supports macOS only; Linux and Windows are not supported yet. It expects VS Code with
GitHub Copilot and a Git project with a GitHub repository identity. A completed Change becomes a
pull request that OwlBear merges once its checks and branch rules pass, or that a person approves
on the Changes page or merges in GitHub.

The main terms are simple:

| Term | Meaning |
| --- | --- |
| Agent | A Copilot role with a specific job, such as shaping, planning, building, or review |
| Skill | Reusable instructions that teach an agent how to handle a domain or workflow |
| MCP server | A tool connection that lets agents use one OwlBear capability from VS Code |
| Change | One approved piece of work tracked from its brief through review and publication |

The normal path is **New Change** on the Changes page, which opens a shaping chat; OwlBear then
plans, builds, reviews and publishes that Change. It keeps the work ordered and reviewed; you
decide when to approve, answer, pause, or merge.

Current surface maturity is published on the consumer front door in
[Status and expectations](README-consumer.md#status-and-expectations). The
[package map](serve/README.md) covers the implementation and tool boundary behind each surface.

## Develop OwlBear

`main` is the only long-lived branch: the development checkout and the branch consumers clone.
Pull requests reach `main` with the required `CI` check; versions are Git tags (`vMAJOR.MINOR`)
that the release workflow sets on merges labelled `release:minor` or `release:major`.

Requirements: macOS, Python 3.14.8 (3.14 series only), [uv](https://docs.astral.sh/uv/), VS Code with
GitHub Copilot, [GitHub CLI](https://cli.github.com/), the GitHub Copilot CLI (`brew install --cask copilot-cli`),
and Git. JSON linting and diagram rendering also need the Node version pinned in `.nvmrc`. Install
the Copilot CLI with Homebrew rather than `npm install -g`, whose copy is hidden when the Node version
changes.

The checked-in development runtime is pinned to Python 3.14.8; OwlBear supports the 3.14 series only.

```shell
git clone https://github.com/maba-pag/owlbear.git
cd owlbear
uv sync --locked --all-packages --all-extras --all-groups
uv run dep-sync
```

`uv run dep-sync` reconciles the local Python and root npm (Biome) environments with the checked-out
manifests.

Open this checkout directly in VS Code. Its repository settings already load the shared
`share/` and project-local `.owlbear/` agent, skill, instruction, and prompt roots; do not run
consumer setup against the OwlBear checkout itself. The machine's running OwlBear lives in
`~/.owlbear/runtime`, separate from this checkout.

Run the repository checks:

```shell
uv run test --all
uv run lint --no-fix
```

### Choose a starting point

| You are changing... | Start with |
| --- | --- |
| Agents, skills, instructions, prompts, or hooks | [Shared ecosystem guide](share/README.md) |
| A runtime package or MCP server | [Package map](serve/README.md) |
| Consumer installation and verification | [Setup guide](setup/setup-guide.md) |
| Consumer operation, updates, or uninstall | [Operating OwlBear](setup/operating-owlbear.md) |

For package or shared-ecosystem changes, use the focused guide first, then run the scoped checks
for the paths you changed. `uv run test --all` and `uv run lint --no-fix` are the full development
checks.

The guide for each surface owns its exact commands and validation. This page keeps the development
checkout and the next decision visible.

## Where things live

| Path | Purpose |
| --- | --- |
| `serve/` | Runtime packages and the [package map](serve/README.md) |
| `share/` | Agents, skills, instructions, prompts, and their [loading model](share/README.md) |
| `setup/` | Installation in the [setup guide](setup/setup-guide.md), daily operation in [Operating OwlBear](setup/operating-owlbear.md), and teams in the [sharing guide](setup/sharing-guide.md) |
| `.owlbear/` | Tracked project authority plus host-local runtime state in the [.owlbear guide](.owlbear/README.md) |
| `tests/` | Workspace regression and integration tests described in the [test guide](tests/README.md) |
| `store/` | Reference-only knowledge corpus manifest described in the [store guide](store/README.md) |
| `.github/` | Development-only automation described in the [GitHub automation guide](.github/README-automation.md) |
