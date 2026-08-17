# OwlBear

OwlBear gives GitHub Copilot a reliable path from an idea to a reviewed change inside VS Code.
It combines reusable agent instructions with tools for planning, execution, memory, knowledge,
browser access, and human review.

## Choose your path

| You are here to... | Start here |
| --- | --- |
| Decide whether OwlBear fits your work | [What OwlBear does](#what-owlbear-does) |
| Add OwlBear to another project | [Consumer setup](README-consumer.md) |
| Develop OwlBear itself | [Develop OwlBear](#develop-owlbear) |
| Find a runtime package or MCP server | [Package map](serve/README.md) |
| Change agents, skills, prompts, or instructions | [Shared ecosystem guide](share/README.md) |
| Share one setup with teammates | [Sharing guide](setup/sharing-guide.md) |

## What OwlBear does

You describe an outcome. Copilot helps refine it, creates an approved work package, and runs the
result through reviewed steps. Cockpit shows the current work and gives a person the controls for
requests, recovery, publication, and completed history.

The main terms are simple:

| Term | Meaning |
| --- | --- |
| Agent | A Copilot role with a specific job, such as design, planning, building, or review |
| Skill | Reusable instructions that teach an agent how to handle a domain or workflow |
| MCP server | A tool connection that lets agents use one OwlBear capability from VS Code |
| Change | One approved piece of work tracked from design through review and publication |
| Cockpit | The browser UI for seeing work and taking human-owned actions |

The normal path is `/ideate` to refine the outcome, `/design` to approve the work package, and
`/orchestrate <change-id>` to run it. The Delivery engine keeps the work ordered and reviewed;
you decide when to approve, answer, recover, publish, or merge.

## Current surfaces

| Surface | Status | Use it for |
| --- | --- | --- |
| Delivery | Core / active | Reviewed Change planning, execution, publication, and acceptance |
| Cockpit | Core / active | Human visibility, requests, recovery, and completed history |
| Memory | Available | Durable, scoped knowledge for future agents |
| Knowledge | Alpha | Searchable documents and knowledge graphs; needs field validation |
| Browser | Alpha | Authenticated web acquisition; needs field validation |

See the [package map](serve/README.md) for the implementation and tool boundary behind each
surface.

## Develop OwlBear

The `dev` branch is the development checkout. The `main` branch is generated from it and is the
rolling supported consumer branch; do not edit `main` directly. OwlBear has no numbered product
releases.

Requirements: Python 3.14.6+, [uv](https://docs.astral.sh/uv/), VS Code with GitHub Copilot, and
Git. Cockpit frontend development also needs the Node version pinned in
`serve/cockpit/web/.nvmrc`.

```shell
git clone -b dev https://github.com/OWNER/owlbear.git
cd owlbear
uv sync --all-extras
```

Run the repository checks:

```shell
uv run test --all
uv run lint --no-fix
```

For the exact development commands, consumer installation, and recovery procedures, use the
[setup guide](setup/setup-guide.md). The guide owns commands; this page owns orientation.

## Where things live

| Path | Purpose |
| --- | --- |
| `serve/` | Runtime packages and the [package map](serve/README.md) |
| `share/` | Agents, skills, instructions, prompts, and their [loading model](share/README.md) |
| `seed/` | Files copied into a consumer project by `setup/init.py` |
| `setup/` | Installation, sharing, and operational procedures |
| `.owlbear/` | Tracked project authority plus host-local runtime state |
| `tests/` | Workspace regression and integration tests |
