# owlbear-kanban

`owlbear-kanban` is the transport-free control plane for target delivery. It projects semantic work
items from admitted authority, runs reviewed plan, build, and assembly transformations, coordinates
one writable worktree per change, preserves exact-commit review evidence, and gates activation with
an immutable cutover receipt and hash-verified legacy snapshots.

Parent project: [README.md](../../README.md)

## Launch / Usage

The package has no standalone service. Import its public contracts directly, or use the
`owlbear-mcp-kanban` adapter documented in [serve/mcp-kanban/README.md](../mcp-kanban/README.md).

```python
from pathlib import Path

from owlbear_kanban import TargetAuthority, TargetRuntime

change_root = Path(".owlbear/target/changes/replace-cache")
authority = TargetAuthority.model_validate_json((change_root / "authority.json").read_bytes())
runtime = TargetRuntime(authority, change_root)
ready_jobs = runtime.list_frontier()
```

The main public areas are:

| Area | Contracts |
|------|-----------|
| Semantic authority | Commitments, outcomes, task-plan scopes, design re-entry, updates, and summaries |
| Work projection | Portfolio work items with stage, attention, dependency, and task progress |
| Transformations | `TargetRuntime` plan, build, and conditional assembly claims with nested review |
| Coordination | Per-change writers, global capacity, warm worktrees, and merge-only integration |
| Evidence | Immutable attempts, reviews, receipts, and contained exact-commit proof checkouts |
| Activation | Snapshot, readiness, mutation authorization, atomic cutover, and receipt verification |

Authority lives at `.owlbear/target/changes/<change-id>/authority.json`; each sibling
`target-runtime/` stores that change's job, attempt, request, and receipt evidence. Legacy snapshots
remain queryable evidence but never become active runtime input.

## Configuration

The package reads no environment variables. Callers pass repository, target-store, proof-checkout,
worktree, integration-target, and capacity configuration explicitly. MCP, Cockpit, and setup own
their process-level configuration and must authorize target mutation through the published cutover
receipt before writing runtime state.

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic` | Strict native schemas and validation |
| `ruamel.yaml` | Canonical YAML parsing and serialization |
| `pyyaml` | Manifest loading |

Filesystem writes use contained paths, locking, immutable create/replay semantics, and transactional
recovery. Callers should use the public target runtimes, coordinators, and cutover operations rather
than writing authority or runtime files directly.
