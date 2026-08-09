# owlbear-delivery

`owlbear-delivery` is the transport-free control plane for target delivery. It projects semantic work
items from admitted Specification authority, owns deterministic Planning and Build transitions,
coordinates bounded execution and writer capacity, integrates reviewed changes, and publishes
recoverable completed history. It also retains the public cutover and evidence contracts used to
authorize the target store and inspect historical transformation state.

Parent project: [README.md](../../README.md)

## Launch / Usage

The package has no standalone service. Embedded callers use its public stores, runtimes, and
`PortfolioApplication`; agent clients use the `owlbear-delivery-mcp` adapter documented in
[serve/delivery-mcp/README.md](../delivery-mcp/README.md). The adapter is the public tool and startup
configuration reference.

The main public areas are:

| Area | Contracts |
|------|-----------|
| Authored Specification | `DesignPackageStore` create, verified read, compare-and-swap revision, and checkpoint |
| Compilation and admission | Deterministic contract derivation, validation, package binding, and atomic runtime admission |
| Operational Delivery | `DeliveryRuntime` and `PortfolioApplication` outcome stages, launch acquisition, typed role contexts, publication, worker transitions, requests, and exact-claim recovery |
| Work projection | Portfolio work items with dependency readiness, typed attention, requests, blocks, and task progress |
| Coordination | Per-change writers, separate execution/writer capacity, warm worktrees, and reviewed source boundaries |
| Integration and history | Atomic target publication, typed Integration attention, reviewed additive repair admission, and bounded completed lookup |
| Cutover and retained evidence | `TargetRuntime`, `list_frontier`, target snapshots, mutation authorization, receipts, and legacy verification remain public for activation and evidence consumers |

Assembly remains a live stage, projection, and required role-policy configuration type. Current
compiled bindings leave `assembly_required` false, and the agent MCP registry exposes no Assembly
context or result-publication operation. Operational agents therefore do not run that stage; an
unexpected launch is recovered by exact claim identity.

## Configuration

The package reads no environment variables. Callers pass package, target-state, repository,
worktree, Integration target, role policies, and capacity configuration explicitly. MCP, Cockpit,
and setup own process-level configuration and must authorize target mutation through the published
cutover receipt before writing runtime state.

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic` | Strict native schemas and validation |
| `ruamel.yaml` | Canonical YAML parsing and serialization |
| `pyyaml` | Manifest loading |

Filesystem writes use contained paths, locking, immutable create/replay semantics, and transactional
recovery. Callers should use the public target runtimes, coordinators, and cutover operations rather
than writing authority or runtime files directly.
