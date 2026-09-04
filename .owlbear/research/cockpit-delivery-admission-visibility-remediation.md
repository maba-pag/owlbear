# Cockpit Delivery Admission Visibility Remediation

> **Owning task:** `TASK-OUT-003-001` - Document the admission-visibility remediation and prove final boundaries
> **Date:** 2026-08-22
> **Status:** Implemented; documentation and exact-candidate proof are the final work package
> **Question:** How should Cockpit and Delivery keep persisted admission, lifecycle stage, runtime membership, and user-facing portfolio state consistent when a long-lived application observes an admission made after startup?

## 1. Context And Question

A long-lived Cockpit or Delivery process can outlive the admission event that creates a Change. The
incident was larger than a stale label: when process-local runtime membership was not refreshed, an
admitted Change could disappear from portfolio groups and totals and be projected as unadmitted
Design.

The controlling distinction is now explicit. Persisted `contract.json`, `admission.json`,
`frontier.json`, and coordination records are Delivery authority. `PortfolioApplication._runtimes`
is process-local actionable membership. Runtime membership must be reconciled from persisted Change
discovery before portfolio reads and direct runtime lookups; it is not an alternative authority.

The shipped remediation preserves that boundary, adds explicit per-Change status axes, and keeps the
existing Cockpit polling and user-control surfaces. It does not expand Delivery MCP or decide the
cause-specific taxonomy for missing coordination records.

## 2. Sources Studied

| Source | Relevant evidence | Limit |
| --- | --- | --- |
| `serve/delivery/src/owlbear_delivery/delivery_contract_discovery.py` | Read-only persisted Change discovery validates contract, admission, and frontier evidence and projects the generic `runtime_unavailable` diagnostic when admitted evidence cannot form an actionable runtime. | Defines discovery facts, not the application refresh policy. |
| `serve/delivery/src/owlbear_delivery/portfolio_application.py` | `_reconcile_runtimes()` discovers persisted Changes, retains unchanged runtimes, composes new or replaced runtimes when actionable, drops removed membership, and records reconciliation errors. Portfolio reads and `_runtime()` invoke reconciliation. | Runtime reconciliation does not classify every missing-coordination cause. |
| `serve/delivery/src/owlbear_delivery/portfolio_operating.py` | `PortfolioChangeLifecycleStatus` separates admission, stage, runtime actionability, and bounded diagnostics; `PortfolioOperatingView` carries the active status population. | Domain projection does not define frontend wording. |
| `serve/delivery/src/owlbear_delivery/work_items.py` | Planning bindings with no tasks use the stable `Task plan not published` progress label. | Work-item projection is not the HTTP serialization boundary. |
| `serve/cockpit/src/owlbear_cockpit/routes/target_work.py` and `target_models.py` | `/api/work-items` adapts the Delivery operating view through strict response models; the assembled route surface retains the user-owned POST controls. | Route assembly proves availability, not user intent for invoking a control. |
| `serve/cockpit/web/src/hooks/useWorkItems.ts`, `api/workItems.ts`, and `pages/WorkPortfolioPage.tsx` | The frontend polls `/api/work-items` every 3 seconds, consumes explicit status fields, and distinguishes unadmitted, admitted, and unavailable states. | Polling observes reads; it is not a push or full-reload mechanism. |
| `serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py` and `serve/delivery-mcp/tests/test_delivery_adapter.py` | The Delivery MCP operation inventory remains unchanged and its exact registry test guards prohibited method expansion. | This remediation does not design future user-control parity. |
| Implementation commits `291f84761a871effae97d5b9b646aa24fff9cafc`, `3452c5754bc1a5a62379f221e02fc824aae2b5b7`, `009b4f2ac2d2612ff53a34586e2eef6d076e955d`, and `52ed15738b74c58a5cc934f0fe7b4d5a526b5514` | The exact shipped sequence covers persisted runtime reconciliation, Delivery status projection, Cockpit API exposure, and explicit frontend rendering. | Commit history identifies implementation scope; the final task result binds fresh proof to its own candidate commit. |
| `.owlbear/research/1233-realtime-cockpit-updates.md` and the prior remediation plan | Existing polling and future push-transport boundaries, plus the original incident model and follow-up separation. | Earlier research is context; current source and exact tests control the final claims. |

## 3. Analysis

### Persisted Authority And Runtime Membership

`PortfolioApplication._reconcile_runtimes()` calls persisted discovery before reads that depend on
runtime membership. A validated unchanged contract keeps its runtime object, a new or replaced
contract is composed only when its persisted evidence is actionable, and removed persisted
authority no longer remains in the runtime map. Reconciliation records a bounded error for an
admitted observation that cannot provide an actionable runtime, allowing the read model to preserve
admission truth.

This is a membership-freshness repair, not a second frontier cache. Existing frontier reads remain
read-through, and read-side discovery does not publish authority, allocate worktrees, or rewrite a
valid frontier.

### Explicit Status And Planning Semantics

Delivery now exposes separate status axes: `admission`, `stage`, `actionable_runtime`,
`diagnostic_code`, and `diagnostic_detail`. The active status population is built from verified
package IDs plus persisted discovery observations, including admitted observations and any
unadmitted entries needed to preserve genuine Design visibility. Completed history remains a
separate surface.

| State | Shipped projection |
| --- | --- |
| Genuine unadmitted package | `admission=unadmitted`, `stage=design`, `actionable_runtime=false`, and inclusion in `draft_design_change_ids`. |
| Admitted Planning with zero tasks | A normal Change group with `Task plan not published`; absence of tasks is not loss of admission. |
| Admitted Design re-entry | `admission=admitted`, explicit Design stage, and inclusion in `design_required_change_ids`, not the draft list. |
| Admitted but unavailable runtime | Admission remains admitted with `actionable_runtime=false` and generic `runtime_unavailable`; it is never projected as unadmitted Design. |

The status population and operating counts use the same current Change set. Completed Change history
is not synthesized into current statuses.

### Cockpit Read And Control Boundary

The HTTP response uses strict adapters for the Delivery operating projection, and TypeScript
consumes the same explicit fields. The current 3-second poll therefore observes reconciled reads
without reloading the full Cockpit application. No SSE, watcher, or full-application reload was
introduced.

Cockpit retains 21 user-owned POST controls in the assembled FastAPI inventory: five request and
outcome controls, nine publication and acceptance controls, and seven target and worktree controls.
They continue to call Delivery domain methods and locks. Cockpit remains an operator surface; it
does not schedule work, choose worker transitions, interpret reviewer evidence, or silently turn
user controls into agent actions.

### Shipped And Deferred Boundaries

| Shipped in this remediation | Deferred to a separate follow-up Change |
| --- | --- |
| Persisted runtime membership reconciliation and cross-instance visibility. | Cause-specific investigation and typed handling for missing-coordination states. |
| Explicit Delivery status projection and strict Cockpit API adaptation. | Delivery MCP user-control parity with explicit confirmation semantics. |
| Cockpit rendering for genuine Design, admitted Planning, Design re-entry, and runtime-unavailable states. | SSE, filesystem watchers, or full application reload. |
| Preservation of the existing 21 Cockpit user-control routes and unchanged Delivery MCP operation inventory. | Generated `serve/cockpit/dist/` commits on `dev`. |

### Implementation Commit Chain

| Commit | Scope |
| --- | --- |
| `291f84761a871effae97d5b9b646aa24fff9cafc` | Reconcile persisted runtime consumers and preserve the stale-reader regression boundary. |
| `3452c5754bc1a5a62379f221e02fc824aae2b5b7` | Project explicit Delivery lifecycle statuses and correct operating population/count derivation. |
| `009b4f2ac2d2612ff53a34586e2eef6d076e955d` | Expose lifecycle statuses through strict Cockpit transport models. |
| `52ed15738b74c58a5cc934f0fe7b4d5a526b5514` | Render explicit lifecycle states in Cockpit and preserve the existing polling/control behavior. |

The final Delivery result for this task binds fresh exact-candidate observations to the
implementation above. Required evidence covers the three document assertions, focused Delivery,
Cockpit, frontend, build, browser, and Delivery MCP checks, the assembled 21-route inventory, and
the repository-mapped four-domain test run. No transient test log is checked in.

## 4. Recommendation, Confidence, And Limits

**Recommendation:** Keep persisted Delivery evidence authoritative and treat runtime reconciliation
as the application read/mutation boundary. Keep explicit admission and runtime-health fields in the
operating projection so API and UI consumers do not infer lifecycle from dictionary membership,
counts, or missing groups. Preserve Cockpit user controls and keep MCP parity out of the incident
fix until its confirmation and annotation contract is designed separately.

**Confidence:** High for the stale-membership root cause and the shipped reconciliation/status/API/UI
boundaries. The implementation commits, current source, focused tests, and exact route/MCP
contracts provide direct evidence for those claims.

**Limits:** `runtime_unavailable` is intentionally generic. It preserves admitted authority without
claiming that every missing-coordination state has been classified. The separate investigation must
trace cleanup, abandonment, completion, migration, and interrupted-transaction states before
assigning cause-specific diagnostics or recovery rules. Current polling improves freshness only at
its existing cadence, and this task does not change the transport model or commit generated frontend
output.
