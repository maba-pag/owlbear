# GitHub Automation

This guide intentionally is not named `README.md`: GitHub gives `.github/README.md` precedence over
the root README when choosing the repository landing page. The non-special filename keeps the root
OwlBear front door visible while still giving this folder a durable orientation guide.

`.github/` contains development-only repository automation and Copilot support. The consumer
`main` branch deliberately excludes this directory; changes here affect the OwlBear repository,
its checks, or its manual sync process rather than an installed project directly.

## What lives here

| Path | Purpose |
| --- | --- |
| `workflows/` | CI, dependency checks, ecosystem validation, and the manual `dev` to `main` sync |
| `scripts/` | Small checks used by workflows and the sync manifest projection |
| `skills/` | Development-only specialist guidance, including session review and hook authoring |
| `copilot-instructions.md` | The development checkout's workspace identity and repository map |
| `sync-manifest.json` | The allowlisted source paths and consumer exclusions for rolling `main` |
| `renovate.json` | Repository configuration for dependency update automation |

## What belongs elsewhere

- Portable agents, skills, instructions, and prompts live in [`share/`](../share/README.md).
- Consumer-project Copilot and VS Code templates live under `seed/` and are applied by
  [`setup/init.py`](../setup/init.py).
- Runtime packages and MCP servers live under [`serve/`](../serve/README.md).
- Installation and operating procedures live in the [setup guide](../setup/setup-guide.md) and
  [Operating OwlBear](../setup/operating-owlbear.md).

The development instructions in `.github/copilot-instructions.md` are not the same artifact as the
consumer template at `seed/.github/copilot-instructions.md`. The former describes this repository;
the latter is a placeholder that `init.py` adapts for a project using OwlBear.

## Changing the sync boundary

Treat [`sync-manifest.json`](sync-manifest.json) as the source of truth for the source allowlists
and excluded roots that feed `main`. The [sync workflow](workflows/sync-to-main.yml) owns the
transformations around those inputs, including the consumer README rename, pruning, and generated
outputs. When a projection changes, update the manifest, workflow, and regression coverage in
[`tests/test_sync_manifest.py`](../tests/test_sync_manifest.py). Do not edit `main` directly; the
manual sync workflow generates it from `dev`.
