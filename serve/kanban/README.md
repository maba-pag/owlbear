# owlbear-kanban

`owlbear-kanban` is the transport-free native control plane for durable change authority and
graph-aware Delivery. It validates and admits change revisions, stores purpose-specific jobs and
attempts, manages Decision and Action Requests, writes immutable receipts and findings, derives
activity and health views, and preserves hash-verified legacy inventory outside runtime state.

Parent project: [README.md](../../README.md)

## Launch / Usage

The package has no standalone service. Import its public contracts directly, or use the
`owlbear-mcp-kanban` adapter documented in [serve/mcp-kanban/README.md](../mcp-kanban/README.md).

```python
from pathlib import Path

from owlbear_kanban import NativeWorkspace, load_change

workspace = NativeWorkspace(Path(".owlbear/kanban"))
revision = load_change(workspace.changes_dir, "replace-cache")
```

The main public areas are:

| Area | Contracts |
|------|-----------|
| Change authority | `load_change`, validation, admission assessment, admission transaction |
| Work selection | `DispatchRuntime`, dependency-aware job waves, claims, expiry recovery |
| Job lifecycle | `NativeRuntime`, purpose-specific finish and reject operations |
| Evidence | Receipt, attempt, finding, activity, health, and proof-checkout contracts |
| Requests | Native Decision and Action Request creation, inspection, and resolution |
| History | Immutable legacy snapshot creation and manifest verification |

Authority lives under `.owlbear/changes/<change-id>/`. Operational jobs, attempts, requests,
findings, and activity live under `.owlbear/kanban/`. Successful receipts are immutable authority
inside the owning change. Legacy snapshots live under `.owlbear/legacy/` and have no compatibility
reader into the active runtime.

## Configuration

`NativeWorkspace` accepts an explicit native work root and an optional positive claim-expiry
duration. The default claim expiry is one hour. `parse_claim_expiry` accepts positive values such as
`30m`, `2h`, or `1d`.

The package itself reads no environment variables. Adapters own process configuration; the MCP and
Cockpit adapters use `OWLBEAR_WORK_ROOT`, defaulting to `.owlbear/kanban` relative to the process
working directory.

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic` | Strict native schemas and validation |
| `ruamel.yaml` | Canonical YAML parsing and serialization |
| `pyyaml` | Delivery document loading |

Filesystem writes use contained paths, locking, immutable create/replay semantics, and transactional
recovery. Callers should use the package stores and runtimes rather than writing control-plane files
directly.
