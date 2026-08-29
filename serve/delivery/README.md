# owlbear-delivery

`owlbear-delivery` is the transport-free control plane for Change delivery. It projects semantic work
items from admitted Design authority, owns deterministic Planning and Build transitions, coordinates
bounded execution, publishes reviewed Change checkpoints, observes user-owned
pull-request acceptance, and projects recoverable completed history. It retains legacy Target cutover
and evidence contracts for historical consumers; canonical Change delivery does not use them.

**Use this guide when:** you need to extend or integrate the core Change authority, understand its
worktree and publication boundaries, or call its public stores and runtimes.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

## Launch / Usage

The package has no standalone service. Embedded callers use its public stores, runtimes, and
`PortfolioApplication`; agent clients use the `owlbear-delivery-mcp` adapter documented in
[serve/delivery-mcp/README.md](../delivery-mcp/README.md). The adapter is the public tool and startup
configuration reference.

The main public areas are:

| Area | Contracts |
| --- | --- |
| Authored Specification | `DesignPackageStore` create, verified read, compare-and-swap revision, and checkpoint |
| Compilation and admission | Deterministic contract derivation, validation, package binding, and atomic runtime admission |
| Operational Delivery | `DeliveryRuntime` and `PortfolioApplication` outcome stages, frontier acquisition, typed role contexts, publication, worker transitions, requests, and exact-claim recovery |
| Work projection | Portfolio work items with dependency readiness, typed attention, requests, blocks, and task progress |
| Coordination | Exact per-Change writer custody, one shared execution budget, warm worktrees, and reviewed source boundaries |
| Publication and acceptance | Change-branch checkpoints, draft pull-request reconciliation, finalization, acceptance observation, and publication supersession |
| Completed history | Receipt-backed completed Change projections with bounded list, search, and exact lookup |
| Legacy compatibility | Typed Integration attention/recovery and `TargetRuntime` evidence remain public for historical consumers |

Assembly is not a live Delivery stage or public Change authority. Historical runtime captures may
still contain reducible Assembly metadata, and legacy completed-history records retain their
historical schema for validation. New Changes use sequential Planning and Build outcomes directly.

## Admission And Portfolio Freshness

Persisted Delivery authority is held by the canonical `contract.json`, `admission.json`,
`frontier.json`, and coordination records under `.owlbear/delivery/runtime/changes/`. The
`PortfolioApplication` runtime map is process-local actionable membership, not a second authority.

Before portfolio reads and direct Change runtime lookups, `PortfolioApplication` reconciles
persisted Change discovery. It retains an unchanged runtime, composes a runtime for a newly
discovered or replaced contract when the persisted evidence is actionable, and removes runtime
membership when persisted authority is removed. Frontier access remains read-through. A read-side
reconciliation does not publish authority, allocate worktrees, or rewrite a valid frontier.

The operating projection exposes explicit status axes instead of inferring lifecycle from runtime
map membership: `admission`, `stage`, `actionable_runtime`, `diagnostic_code`, and
`diagnostic_detail`. Its active status population is built from verified package IDs plus persisted
discovery observations, including admitted observations and the unadmitted entries needed to keep
genuine Design packages visible. Completed history remains a separate surface.

| Persisted state | Portfolio projection |
| --- | --- |
| Genuinely unadmitted package | `admission=unadmitted`, `stage=design`, and `actionable_runtime=false`; it is included in `draft_design_change_ids`. |
| Admitted Planning Change, including `tasks: []` | A normal Change group with Planning progress labeled `Task plan not published`; it is not a draft Design entry. |
| Admitted Change explicitly returned to Design | `admission=admitted` and `stage=design`; it is included in `design_required_change_ids`, not the draft list. |
| Admitted Change without an actionable runtime | Admission remains visible with `actionable_runtime=false` and the generic `runtime_unavailable` diagnostic; it is never recast as unadmitted Design. |

Cause-specific missing-coordination classification is a separate follow-up Change. The Delivery MCP
operation inventory is also unchanged by this remediation; user-control parity remains a separate,
explicitly user-directed follow-up.

## Configuration

The package reads no environment variables. Canonical MCP and Cockpit startup uses the tracked
project policy and optional host-local runtime settings below. Embedded callers may provide the
same typed configuration directly.

| File | Optional? | Fields and defaults | Ownership |
| --- | --- | --- | --- |
| `.owlbear/delivery/config.json` | Required for canonical MCP/Cockpit startup | `schema_version` must be `2`; `remote`, `target_branch`, and `github_repository` are required and have no loader defaults. `delivery_state_branch` defaults to `owlbear/delivery-state` and is written by setup. `setup/init.py` defaults `remote` to `origin`, uses `main` as the non-interactive target-branch fallback, suggests the current branch interactively, and infers `github_repository` from the configured remote. | Tracked project policy |
| `.owlbear/delivery/runtime/host.json` | Optional and ignored | `execution_capacity` defaults to `3`. When present, `schema_version` must be `1`; execution capacity must be a positive integer. Unknown keys and non-integer values are rejected at startup. | Host-local configuration |
| `.owlbear/delivery/runtime/capacity.json` | Legacy migration export; do not edit | Historical `CapacityLedger` data may retain active-holder fields for migration validation. It is not current runtime authority and is absent from new runtime state. | Historical migration authority |

`execution_capacity` is the maximum number of active Planner or Builder outcome claims across the
portfolio. Each acquired Change has exact per-Change writer custody; there is no separate global
`writer_capacity` admission limit. The optional host file can allow three active claims:

```json
{"schema_version": 1, "execution_capacity": 3}
```

`setup/init.py` creates the tracked project policy but does not create `host.json`; the absence of
that file therefore preserves the defaults above.

### Portability And Recovery

Authored `intent.md` and `design.md` remain local drafts until admission. When a Change is admitted,
Delivery commits the verified `authority.json`, `design.md`, `intent.md`, and `manifest.json` to the
managed `owlbear/change/<change-id>` branch before opening its first draft pull request. Later Design
revisions are rejected for that Change; a semantic change starts a new or superseding Change.

Sparse semantic checkpoints are published to the configured `delivery_state_branch` at admission,
meaningful task or Outcome progress, finalization, and acceptance. They retain resumable authority
and terminal evidence, but never live claims, locks, capacity ledgers, process identifiers, or local
paths. A fresh clone can therefore recover the last published checkpoint and requeue incomplete work.
The local `refs/owlbear/packages/*` refs remain useful package history, but are not a remote backup.

If the remote package branch, state snapshot, contract, or local state disagree, startup reports
bounded Delivery attention and does not choose a side silently. Do not copy hidden `.git` refs or
ignored runtime files between machines; restore from the normal remote branches and the configured
state branch.

## Dependencies

| Package | Purpose |
| --- | --- |
| `pydantic` | Strict native schemas and validation |
| `ruamel.yaml` | Canonical YAML parsing and serialization |
| `pyyaml` | Manifest loading |

Filesystem writes use contained paths, locking, immutable create/replay semantics, and transactional
recovery. Callers should use the public Delivery application, stores, and coordinators rather than
writing authority or runtime files directly.
