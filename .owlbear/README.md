# OwlBear Project Operations

`.owlbear/` is the project-local OwlBear operations area. It combines tracked authority and
research with generated indexes and host-local runtime state. It is not a Python package and it is
not the portable source tree copied into a consumer project.

## What lives here

| Area | Role |
| --- | --- |
| `delivery/` | Change configuration and Delivery authority; runtime capacity, worktrees, and locks are host-local or ignored |
| `hooks/` | Project-local write, session, and lint hooks used by the development checkout |
| `instructions/`, `prompts/`, and `skills/` | Project-local operational customizations loaded alongside the portable shared ecosystem |
| `scripts/` | Development validators and operational helper scripts |
| `research/` | Durable source-grounded findings for future design and implementation work |
| `sources/` | External-source attribution for research and implementation work |
| `memory/` | Tracked agent memory entries; host-local memory databases are ignored |
| `knowledge/` | Local Knowledge database and placeholders; databases and vectors are ignored |
| `ideas.md` | Markdown ideas notebook read by Cockpit and edited through its ideas workflow |
| `legacy/` | Retired briefs and historical artifacts kept for provenance, not active authority |
| `scratch/` | Temporary investigation output; it is ignored and should be cleaned up after use |
| `*-index.md` | Generated navigation indexes; regenerate them from the repository root with `uv run indexes` |

Tracked files and ignored runtime files intentionally coexist here. Use the owning Delivery,
Knowledge, or Memory workflow for lifecycle mutations instead of broad file operations over this
directory.

## What belongs elsewhere

- Portable project templates are in `seed/.owlbear/` and are rendered by
  [`setup/init.py`](../setup/init.py).
- Shared agent ecosystem definitions are in [`share/`](../share/README.md).
- Runtime code and MCP servers are in [`serve/`](../serve/README.md).
- Development-only CI and repository automation are in [`.github/`](../.github/README-automation.md).
- Workspace-wide regression tests are in [`tests/`](../tests/README.md).

This directory is not included in the consumer sync manifest. A consumer project's `.owlbear/`
area is created from the seed templates and then accumulates its own authority, research, memory,
and runtime state.
