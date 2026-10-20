# OwlBear Project Operations

`.owlbear/` is the project-local OwlBear operations area. It combines tracked project authority
with generated indexes and host-local runtime state. It is not a Python package and it is not the
portable source tree copied into a consumer project.

## What lives here

| Area | Role |
| --- | --- |
| `hooks/` | Project-local write hooks used by the development checkout |
| `instructions/`, `prompts/`, and `skills/` | Project-local operational customizations loaded alongside the portable shared ecosystem |
| `scripts/` | Development validators and operational helper scripts |
| `research/` | OwlBear's decision record, its plan and status, and build designs of work not yet built; other research lives in the project's folder of the data repository |
| `sources/` | External-source attribution for research and implementation work |
| `memory/` | Agent memory entries written by the `owlbear-memory` server; host-local memory databases are ignored |
| `knowledge/` | Local Knowledge database and placeholders; databases and vectors are ignored |
| `scratch/` | Temporary investigation output; it is ignored and should be cleaned up after use |
| `*-index.md` | Generated navigation indexes; regenerate them from the repository root with `uv run indexes` |

Tracked files and ignored runtime files intentionally coexist here. Use the owning Knowledge or
Memory workflow for lifecycle mutations instead of broad file operations over this directory.

Delivery keeps no state here. A registered project's Delivery state lives in
`~/.owlbear/projects/<id>/` on each machine, and its clone's Git folder holds only the project's id
and format marker; see [What OwlBear Installs](../setup/operating-owlbear.md#what-owlbear-installs).

## What belongs elsewhere

- Portable project templates are in `seed/.owlbear/` and are rendered by
  [`setup/init.py`](../setup/init.py).
- Shared agent ecosystem definitions are in [`share/`](../share/README.md).
- Runtime code and MCP servers are in [`serve/`](../serve/README.md).
- Development-only CI and repository automation are in [`.github/`](../.github/README-automation.md).
- Workspace-wide regression tests are in [`tests/`](../tests/README.md).

This directory is not copied into consumer projects. A consumer project's `.owlbear/` area is
created from the seed templates by the optional agent workspace setup and then accumulates its own
memory, knowledge, and runtime state.
