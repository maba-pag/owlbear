# owlbear-tools — Workspace Utilities

Workspace commands for the OwlBear project: quality checks, test routing, dependency
synchronization and repository helpers. `uv run help` lists them.

**Use this guide when:** you need to run or change a workspace command or synchronize local
dependencies.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

```bash
# List the workspace commands
uv run help

# Run the tests that a change affects
uv run test --changed
```

## Configuration

The commands use the repository checkout and do not require environment variables.

### Dependency environment

Use `uv run dep-sync` to reconcile the checked-out manifests and lockfiles with the local Python and root npm environments, after checking the running Node against `.nvmrc`. Use `uv run dep-status` for a read-only check; it also supports `--verbose` (`-v`) and `--json` (`-j`).

These commands consume the dependency versions already selected in the checkout. Hosted Renovate remains responsible for selecting updates and opening pull requests; synchronization never edits manifests or lockfiles.

### Dependency profile

The dependency commands cover the uv workspace and the repository-root npm package, which holds Biome.
