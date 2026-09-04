# Cockpit Delivery Admission Visibility Remediation

> Status: candidate authority; admission gates pending
> Research: `.owlbear/research/cockpit-delivery-admission-visibility-remediation.md`

## Problem And Product Promise

An admitted Delivery Change can disappear from Cockpit when Cockpit starts before admission. The long-lived `PortfolioApplication` retains a process-local `_runtimes` membership map. Portfolio projection derives groups, counts, and `draft_design_change_ids` from that stale map, so an admitted Planning Change can be falsely shown as `Not admitted to Delivery` Design work.

The user must be able to admit a Change through Delivery, keep Cockpit running, and see the admitted Change in the correct lifecycle stage on the next portfolio read. Genuine unadmitted Design packages must remain Design. A persisted admitted Change that cannot currently compose an actionable runtime must retain its admission truth and be visibly unavailable rather than becoming unadmitted Design. The remediation must preserve Cockpit's intentional user-owned controls: answering requests, clearing blocks, administrative movement, recovery, and acceptance reconciliation.

## Normal Workflow

1. A Change is admitted through the existing Delivery boundary.
2. An already-running Cockpit reads `/api/work-items`.
3. The application discovers persisted admission evidence and reconciles runtime membership from contract fingerprints before every operation that enumerates or retrieves `_runtimes`.
4. The portfolio projection distinguishes unadmitted Design, admitted Planning, admitted Design re-entry, and admitted-but-unavailable states.
5. Cockpit polling observes the corrected state without a process restart or full application reload.
6. Focused regression tests and the repository-mapped suites prove the behavior.

## In Scope

- A deterministic cross-application stale-reader regression.
- Fingerprinted persisted-contract discovery and runtime membership reconciliation supporting additions, replacements, and removals while retaining unchanged runtime objects.
- Persisted-admission-based lifecycle classification independent of successful runtime composition.
- Per-entry handling for malformed or mid-write runtime directories so one affected Change does not become a global portfolio outage or false Design row.
- Reuse of existing contract validation, transaction recovery, locking, workspace, coordination, and frontier-read boundaries.
- Explicit additive API fields for admission, lifecycle stage, runtime availability, and safe diagnostic identity.
- Correct Cockpit rendering, operating-summary arithmetic, and focused backend/frontend tests.
- Documentation and operational proof for the persisted-authority versus process-membership distinction.

## Out Of Scope And Preserved Remainder

Detailed missing-coordination investigation and cause-specific typed degraded-coordination behavior are a separate future Change. This Change may emit a bounded generic `runtime_unavailable` status when persisted admission is present but actionable runtime composition is unavailable; it does not classify the underlying coordination cause or change recovery policy. Delivery MCP parity for Cockpit-only user controls is a later independent follow-up. SSE or filesystem watchers, full application reload per request, Work Portfolio redesign, removal of Cockpit controls, speculative telemetry, and generated `serve/cockpit/dist/` commits are excluded. Existing persisted Delivery authority, transactional writes, locks, OCC, frontier rereads, user-control domain methods, and polling remain intact.

## Confirmed Decisions

- Persisted Delivery admission evidence is the source of lifecycle truth; process-local runtime membership is an actionable-runtime cache.
- Reconciliation uses a fingerprint of persisted contract identity/content rather than parent-directory mtime alone.
- Unchanged runtime objects are retained; additions, replacements, and removals are handled explicitly.
- Every path that enumerates or retrieves `_runtimes` goes through the reconciliation boundary.
- The full application is not rebuilt for every request.
- API status fields are added in this Change so frontend code does not infer lifecycle from dictionary membership or count arithmetic.
- The initial status contract emits generic unavailable plus safe diagnostic identity for persisted admitted entries that cannot compose; cause-specific coordination handling belongs to the separate Change.
- Cockpit user controls remain available.
- Existing polling remains initially; correct reads make it effective again.

## Success

With a reader application created before admission and a writer application admitting the Change, the reader's next portfolio read contains the admitted Change's Planning group and every admitted outcome, reports `Task plan not published` for empty task plans, excludes the Change from draft Design IDs, and restores the unfinished count. A package without admission remains in genuine Design. An explicitly admitted Design re-entry remains distinct. If persisted admission is present but runtime composition is unavailable, the status remains admitted, derives stage from a valid persisted frontier when possible, reports generic runtime unavailability, and never enters draft Design. Read-side reconciliation does not publish authority or change contract/frontier/claim/capacity content, although existing transaction recovery may complete an already-pending recovery operation. Existing Cockpit user controls continue to resolve current runtime membership or return their established bounded error when actionability is unavailable.

## Technically Done But Wrong

Refreshing only the Design label while omitting the group or count; deriving admission from `_runtimes`; rebuilding the whole application per HTTP request; using directory mtime alone; caching frontier state separately; allowing one malformed or mid-write Change to fail every portfolio poll; starting a new mutation against a known superseded runtime; removing Cockpit controls; changing cause-specific coordination policy in this Change; adding MCP tools inside the incident fix; or replacing current polling before correct backend membership exists.

## Evidence And Limits

Observed source confirms that Cockpit and Delivery MCP retain one `PortfolioApplication` per process lifetime, `PortfolioApplication._runtimes` drives group and Design projections, admission updates only the current application, persisted admission files are independently discoverable under the runtime Change directory, package reads and frontier reads already use recovery/locking, several user and worker paths enumerate `_runtimes` directly, and Cockpit exposes intentional user-owned controls. The current incident is therefore a stale process-local membership defect, not evidence that persisted admission is invalid. The exact cause taxonomy for missing coordination is intentionally outside this Change. Fingerprints assume existing Delivery locks and OCC remain the mutation authority; they do not claim to solve every future multi-process writer policy.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: observed incident plus user-confirmed remediation goal
statement: An admitted Change must be discoverable by an already-running Delivery application from persisted admission and contract authority without process restart or full application reload, even when actionable runtime composition is temporarily unavailable.
```

```yaml target-contract
kind: commitment
id: COM-002
class: protected-request
provenance: user-confirmed freshness decision
statement: Runtime membership reconciliation must detect persisted contract additions, replacements, and removals using stable contract fingerprints while retaining runtime objects for unchanged contracts and protecting active claims.
```

```yaml target-contract
kind: commitment
id: COM-003
class: dealbreaker
provenance: user-confirmed lifecycle truth
statement: Portfolio and API projections must distinguish genuine unadmitted Design from admitted Planning, admitted Design re-entry, and admitted-but-unavailable states using persisted admission evidence rather than runtime-map presence.
```

```yaml target-contract
kind: commitment
id: COM-004
class: protected-request
provenance: user-confirmed control boundary
statement: Existing Cockpit user-owned controls remain available and use current Delivery runtime membership after reconciliation across every direct runtime-map access path.
```

```yaml target-contract
kind: commitment
id: COM-005
class: important-reviewed
provenance: source-grounded safety boundary
statement: Read-side reconciliation reuses existing validation, recovery, locking, workspace, coordination, and frontier-read boundaries, isolates malformed entries per Change, and does not publish or mutate authority merely because a read occurs.
```
