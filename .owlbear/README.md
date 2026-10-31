# OwlBear Project Operations

`.owlbear/` is the project-local OwlBear operations area. It combines tracked project authority
with host-local runtime state. It is not a Python package and it is not the portable source tree
copied into a consumer project.

## What lives here

| Area | Role |
| --- | --- |
| `instructions/` and `skills/` | Project-local operational customizations loaded alongside the portable shared ecosystem; project workflows such as `doc-audit`, `w-agent-audit` and `owlbear-release-analysis` are skills invoked by name |
| `scripts/` | Development validators and operational helper scripts |
| `memory/` | Agent memory entries written by the `owlbear-memory` server; host-local memory databases are ignored |
| `knowledge/` | Local Knowledge database and placeholders; databases and vectors are ignored |
| `scratch/` | Temporary investigation output; it is ignored and should be cleaned up after use |

Tracked files and ignored runtime files intentionally coexist here. Use the owning Knowledge or
Memory workflow for lifecycle mutations instead of broad file operations over this directory.

Delivery keeps no state here. A registered project's Delivery state lives in
`~/.owlbear/projects/<id>/` on each machine, and its clone's Git folder holds only the project's id
and format marker; see [What OwlBear Installs](../setup/operating-owlbear.md#what-owlbear-installs).

## What belongs elsewhere

- OwlBear's research, its designs of unbuilt work and its external-sources log are in owlbear-data's `owlbear/`
  folder: [research and designs](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/research/) and [the sources log](https://github.com/maba-pag/owlbear-data/blob/main/owlbear/sources/overview.md) (D-01M5ZMXT7H851MZZFJA2P9X179). Its documents stay out of
  `.owlbear/`, which keeps agent customizations, scripts and placeholders; OwlBear's plan and status are the
  [pinned tracker issue](https://github.com/maba-pag/owlbear/issues/713).
- Shared agent ecosystem definitions are in [`share/`](../share/README.md).
- Runtime code and MCP servers are in [`serve/`](../serve/README.md).
- Development-only CI and repository automation are in [`.github/`](../.github/README-automation.md).
- Workspace-wide regression tests are in [`tests/`](../tests/README.md).

This directory is not copied into consumer projects; setup creates no `.owlbear/` area there.
