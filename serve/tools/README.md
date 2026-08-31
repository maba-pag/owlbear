# owlbear-tools — Workspace Utilities

Workspace utility scripts for the OwlBear project. Provides generated documentation, Python, and ECMAScript indexes used by agents for navigation.

**Use this guide when:** you need to maintain documentation and source indexes, synchronize local
dependencies, or run repository migration utilities.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

---

## Launch / Usage

```bash
# Regenerate all indexes concurrently
uv run indexes

# Regenerate .owlbear/doc-index.md
uv run doc-index

# Regenerate .owlbear/py-index.md
uv run py-index

# Regenerate .owlbear/ts-index.md (TypeScript, TSX, JavaScript, and JSX)
uv run ts-index

# Preview retired Delivery live-state migration from the project root
uv run migrate-delivery-state .

# Apply or recover and retry the one-way migration
uv run migrate-delivery-state . --apply
```

Each command regenerates its complete index on every invocation. `doc-index` is also the required
refresh step for `.owlbear/prompts/doc-audit.prompt.md`, which regenerates it before scanning and at
closeout. `py-index` and `ts-index` are optional, on-demand orientation aids. No index is
regenerated automatically by pre-commit or CI; source files remain authoritative.

`uv run megalint` runs the pinned MegaLinter image through Docker. On macOS, if the Docker CLI or engine is unavailable, it checks for OrbStack and Docker Desktop, starts the first installed runtime that can become ready, waits for Docker, and retries the command. It stops only a runtime started by this invocation when `OWLBEAR_DOCKER_STOP_RUNTIME=1` is set; otherwise the runtime remains available for later commands. Other platforms require a ready Docker engine.

`migrate-delivery-state` validates retired authority without mutation unless `--apply` is present. Apply moves registered Change worktrees through Git, preserves unrelated registered worktrees under ignored scratch storage, archives retired state under `.owlbear/legacy/delivery-state-migration/`, and resumes safely from an interrupted attempt.

## Configuration

Index commands write fixed artifacts under `.owlbear/`; `migrate-delivery-state` accepts an optional repository path and the `--apply` flag. Dependency commands use the repository checkout and do not require environment variables. Set `OWLBEAR_DOCKER_STOP_RUNTIME=1` when `megalint` should stop a runtime it started after the command finishes.

### Dependency environment

Use `uv run dep-sync` to reconcile the checked-out manifests and lockfiles with the local Python and Cockpit npm environments. Use `uv run dep-status` for a read-only check. Both commands support `--all` (`-a`) for the complete workspace profile; `--pds` (`-p`) includes generated Porsche Design System assets, and `--browsers` (`-b`) installs the Playwright Chromium browser. Status also supports `--verbose` (`-v`) and `--json` (`-j`).

These commands consume the dependency versions already selected in the checkout. Hosted Renovate remains responsible for selecting updates and opening pull requests; synchronization never edits manifests or lockfiles.

### Dependency profile

The dependency commands use the repository checkout and do not require environment variables. The default profile covers the uv workspace and the Cockpit npm root; `--all` adds the other npm roots, PDS assets, and Playwright Chromium.

## Dependencies

Python indexing uses the standard-library AST. ECMAScript indexing uses `tree-sitter-language-pack`.

## Public API

```python
from owlbear_tools.doc_index import generate_index as generate_doc_index
from owlbear_tools.indexes import generate_indexes
from owlbear_tools.py_index import generate_index as generate_py_index
from owlbear_tools.ts_index import generate_index as generate_ts_index

generate_indexes(root)  # writes all three indexes concurrently
generate_doc_index(root)  # writes .owlbear/doc-index.md
generate_py_index(root)  # writes .owlbear/py-index.md
generate_ts_index(root)  # writes .owlbear/ts-index.md
```

| Function | Description |
| --- | --- |
| `generate_indexes(root)` | Regenerate all fixed index artifacts concurrently |
| `doc_index.generate_index(root)` | Regenerate the documentation index |
| `py_index.generate_index(root)` | Regenerate the Python structure index |
| `ts_index.generate_index(root)` | Regenerate the TS/TSX/JS/JSX structure index |
| `doc_index.parse_index(content)` | Parse an existing documentation index into entries |

## Excluded directories

The documentation index excludes workspace state, generated indexes, caches, external stores, and
directories named `fixtures`. It keeps the root README files from otherwise-excluded `store/` and
`tests/` trees but excludes the rest of those trees. Excalidraw entries retain top-level
`describes` source-path globs for diagram audits. Source indexes additionally exclude tests and
conventional test filenames, `vendor`, `public`, `generated`, coverage, and build output.
