# Cockpit Delivery Admission Visibility Remediation Design

> Status: candidate architecture; challenge and validation pending
> Governing research: `.owlbear/research/cockpit-delivery-admission-visibility-remediation.md`

## Ownership And Flow

Persisted Delivery contract entries, admission receipts, frontier files, and coordination records remain authoritative. `PortfolioApplication` owns process-local runtime objects and will gain one private reconciliation boundary. The boundary discovers persisted Change observations, computes a stable fingerprint over contract identity/content, compares it with the application's known membership, and applies additions, replacements, and removals. It retains unchanged `DeliveryRuntime` objects. It also retains a bounded observation/status for admitted entries that cannot currently compose an actionable runtime. It does not reconstruct the complete application or write authority during a read.

To avoid the current import direction, extract low-level persisted Change discovery, admission validation, contract validation, frontier-binding validation, and fingerprint calculation into a dependency-free Delivery module such as `owlbear_delivery.delivery_contract_discovery`. That module must not import `PortfolioApplication`. `delivery_application_loader` and `PortfolioApplication` both depend on that module. The existing loader remains the startup composition owner; it is not called from the HTTP read path. The extracted helper reuses the existing `_read_contract`, `_load_contracts`, and runtime-binding validation semantics while changing discovery output from an all-or-nothing map into per-Change observations. This is the single persisted-discovery path for startup and read reconciliation.

Each observation contains the Change ID, persisted admission identity, contract/fingerprint when valid, frontier/stage when valid, a safe bounded diagnostic when one persisted entry cannot be read, and whether an actionable `DeliveryRuntime` was composed. Admission is derived from validated persisted admission evidence and Change identity, not from `_runtimes`. A verified package with no persisted admission is unadmitted Design. A persisted admitted observation whose runtime is absent or cannot compose remains admitted and gets `actionable_runtime=unavailable`; if its frontier is valid, stage is still derived from that frontier. The generic diagnostic is `runtime_unavailable`; this Change does not classify the cause-specific coordination state.

Use an application-local re-entrant reconciliation lock to serialize membership comparison and map/status updates within one process. After discovery, a valid new contract is composed immediately. An unchanged fingerprint retains the existing runtime object. A valid replacement is adopted only after the new contract and frontier bindings validate. If the Change has active claims, do not replace its live runtime object during the active operation; retain it for the active claim, mark the fingerprint mismatch, and block the start of new mutating operations for that Change with a typed retry condition until the replacement is safely adopted. A removed persisted admission is removed from the active map only after discovery confirms its absence and no current operation is using that runtime. These rules protect in-flight worker and user-control operations without creating a second persisted authority.

Malformed or mid-write entries are contained per Change. Existing transaction recovery and locks run before discovery as they do for current package reads. If a pending recovery resolves the entry, discovery continues normally. If an entry remains unreadable, the previous known runtime is retained for the current operation when one exists, new mutating operations for that Change are blocked with a typed retry condition, and the status reports persisted admission plus `runtime_unavailable` rather than draft Design. If no previous runtime exists but admission identity is valid, the status remains admitted with unavailable stage/actionability. Unrelated Changes continue to project. This policy prevents a single malformed or torn entry from becoming a whole-portfolio outage while preserving a bounded failure boundary; cause-specific coordination handling remains a future Change.

The reconciliation boundary covers every direct runtime-map consumer, not only portfolio reads and `_runtime(change_id)`. The implementation must remove direct access from or route through the reconciled accessor for: `_portfolio_snapshots`, `_portfolio_operating_view`, `reconcile_awaiting_acceptance`, `_retained_change_worktree_view`, `acquire_frontier_work` capacity accounting, `_candidates`, admission/user-control lookups, and `_runtime`. A focused source audit proves no public behavior-critical enumeration or retrieval bypass remains. User-control methods receive the same reconciled map, so Cockpit controls do not acquire a second state owner.

## API And Projection

Add a bounded per-Change status projection at the Delivery operating-view or HTTP response ownership boundary. Its population is the union of verified package IDs and persisted admitted observations, with one status per Change ID; completed-history records remain owned by the existing completed-history surface and are not synthesized into this active portfolio status list. It exposes separate axes rather than one overloaded lifecycle enum:

```text
change_id
admission: admitted | unadmitted
stage: design | planning | implementation | completed | unavailable
actionable_runtime: available | unavailable
diagnostic_code: string | null
diagnostic_detail: string | null
```

A healthy reconciled active runtime emits its persisted admission, frontier-derived stage, `actionable_runtime=available`, and null diagnostics. An unadmitted verified package emits `admission=unadmitted`, `stage=design`, `actionable_runtime=unavailable`, and null diagnostics because no Delivery runtime exists. A persisted admitted observation that cannot compose emits `admission=admitted`, `stage` from the valid frontier when available or `unavailable` otherwise, `actionable_runtime=unavailable`, `diagnostic_code=runtime_unavailable`, and a bounded safe detail. An admitted Planning Change with no tasks remains Planning and reports `Task plan not published`.

`draft_design_change_ids` is derived only from statuses with `admission=unadmitted` and `stage=design`. `design_required_change_ids` remains the explicit admitted Design re-entry signal. Counts, groups, guidance, and frontend rendering use the same status population. Python HTTP models and TypeScript API interfaces are updated additively with focused fixture coverage.

Cockpit scope explicitly includes `serve/cockpit/web/src/pages/WorkPortfolioPage.tsx`, `serve/cockpit/web/src/components/PortfolioOperatingSummary.tsx`, `serve/cockpit/web/src/components/DesignWorkSection.tsx`, `serve/cockpit/web/src/api/workItems.ts`, and their focused tests. The page and summary consume explicit status/count fields rather than adding ID-list lengths; the Design section renders only genuine unadmitted statuses. Admitted Planning and admitted unavailable states cannot be duplicated in Design.

## Migration And Compatibility

The implementation sequence is WP-0 cross-instance regression, WP-1 persisted observation/reconciliation and exhaustive runtime-map coverage, WP-2 explicit API status plus corrected Cockpit rendering, and WP-3 documentation and operational proof. Missing-coordination cause investigation/typed handling and MCP user-control parity are separate future Changes, not hidden tasks in this contract.

Existing portfolio fields and controls are preserved during the additive API migration where practical. No SSE, watcher, full reload, board redesign, or generated `dist/` commit is included. The current polling interval remains. Genuine package-without-admission behavior remains covered as a regression guard.

## Proof Boundaries

- Delivery unit and application tests create a reader application before a writer admits a Change, then assert the reader discovers the persisted admission, group, every admitted outcome, count, and absence from draft Design.
- Delivery tests cover unchanged runtime retention, contract replacement, contract removal, admission derived without runtime composition, malformed and mid-write per-entry containment, transaction-manifest safety, active-claim replacement deferral, new-mutation blocking after observed fingerprint mismatch, authority non-publication, and exhaustive direct-map consumer coverage.
- Cockpit backend tests cover `/api/work-items`, explicit status serialization and fixed population, stale-reader visibility, admitted-but-unavailable projection, and user-control freshness including acceptance reconciliation.
- Cockpit frontend tests cover genuine Draft, admitted Planning, admitted Design re-entry, and admitted unavailable fixtures; `WorkPortfolioPage`, `PortfolioOperatingSummary`, `DesignWorkSection`, and `workItems.ts` consumers are all covered. Frontend build/typecheck and relevant E2E run after focused tests.
- Documentation states that cause-specific missing-coordination classification and MCP parity are separate follow-up Changes and does not claim those behaviors are shipped here.
- Repository-mapped Python, MCP, frontend, build, and relevant E2E suites run for changed domains. Generated `serve/cockpit/dist/` remains uncommitted on `dev`.

## Risks And Known Weaknesses

A fingerprint must include enough contract identity/content to detect replacement within an existing Change directory while remaining bounded and stable. Reconciliation must not race a transaction manifest or weaken package recovery. Replacing a runtime while active claims exist is deferred until a safe boundary, while new mutating operations are blocked so stale authority is not used. Per-entry malformed handling must distinguish valid persisted admission identity from an unreadable contract without exposing internal paths or changing the cause-specific coordination policy. The API status population intentionally excludes completed-history synthesis. User-control parity could expand the MCP public surface and therefore remains a separate Change.

```yaml target-contract
kind: outcome
id: OUT-001
title: Fresh persisted admission and runtime membership
promise: An already-running Delivery application discovers newly admitted Changes from persisted authority and preserves correct portfolio groups, counts, Design classification, and safe runtime availability.
acceptance:
  - "Given reader and writer PortfolioApplication instances sharing one temporary persisted state root, with the reader constructed before the writer admits a Change, the reader's next portfolio view discovers persisted admission, contains that Change's group, and excludes it from draft_design_change_ids."
  - "Given an admitted Change whose outcomes are at planning with empty task lists, the reader reports every admitted outcome, Task plan not published guidance for each applicable outcome, and an unfinished count that includes the Change."
  - "Given a verified package without admission, the package remains in genuine draft Design; given an explicitly admitted Design re-entry, it is represented separately from draft Design."
  - "Given persisted contract additions, replacements, and removals, reconciliation adds, safely replaces, and removes runtime membership while retaining the object for unchanged contract fingerprints and deferring replacement while active claims exist."
  - "Given a persisted admitted observation that cannot compose an actionable runtime, the status remains admitted, derives its stage from a valid persisted frontier when possible, reports generic runtime_unavailable, and does not enter draft_design_change_ids."
  - "Given a malformed or mid-write Change entry, per-entry containment preserves unrelated portfolio entries, retains a previous runtime for the current operation when available, blocks new mutation for the affected Change, and never classifies it as unadmitted Design."
  - "Given a reader-side reconciliation, no admission, frontier, claim, capacity, or contract content is published or rewritten; existing transaction recovery may complete an already-pending recovery operation under its existing lock and recovery rules."
commitments: [COM-001, COM-002, COM-003, COM-005]
dependencies: []
```

```yaml target-contract
kind: outcome
id: OUT-002
title: Explicit lifecycle API and Cockpit rendering
promise: Cockpit receives independent admission, stage, runtime-health, and diagnostic fields and renders admitted Planning correctly without removing user controls.
acceptance:
  - "Given the union of verified package IDs and persisted admitted observations, the API emits one explicit status per Change ID with separate admission, stage, actionable_runtime, diagnostic_code, and diagnostic_detail fields."
  - "Given an unadmitted verified package, the API emits unadmitted Design with no Delivery runtime; given an admitted Planning Change with no published task plan, the API emits admitted Planning with available runtime, includes it in its normal group, excludes it from draft_design_change_ids, and reports Task plan not published."
  - "Given an admitted Design re-entry or admitted-but-unavailable observation, the API and Cockpit render it distinctly through status fields and `design_required_change_ids` rather than as genuine unadmitted Design."
  - "Given the corrected API fixtures, `WorkPortfolioPage`, `PortfolioOperatingSummary`, and `DesignWorkSection` render genuine unadmitted Design, admitted Planning, admitted Design re-entry, and admitted unavailable state without deriving counts or classification from ID-list arithmetic."
  - "Given the existing Cockpit user-control routes, focused backend and frontend tests prove the controls remain available after reconciliation and API changes, including acceptance reconciliation against a Change admitted by another application instance."
commitments: [COM-003, COM-004]
dependencies: [OUT-001]
```

```yaml target-contract
kind: outcome
id: OUT-003
title: Durable incident proof and follow-up boundary
promise: The stale-admission visibility fix is documented and proven while deferred coordination and MCP work remain separately governable.
acceptance:
  - "Given the changed Delivery and Cockpit domains, focused tests, frontend build/typecheck, relevant E2E, and repository-mapped broader suites pass with exact commands recorded against the implementation commits."
  - "Given the remediation document and affected API/Delivery documentation, the files contain named statements for persisted authority versus process-local membership, Planning with zero tasks, polling freshness, the active status population, generic runtime_unavailable boundaries, and missing-coordination/MCP work as separate follow-up Changes."
  - "Given the completed incident-fix Change, no Delivery MCP user-control tools are added and all existing Cockpit user-control routes remain available; MCP parity is explicitly deferred rather than accepted as work here."
commitments: [COM-004]
dependencies: [OUT-002]
```
