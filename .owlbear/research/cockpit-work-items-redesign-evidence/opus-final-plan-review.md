Browser automation was unavailable, but the live app answered directly over HTTP — I inspected `/api/work-items`, the outcome detail, and the integration attention on the running instance at `127.0.0.1:8420`. No files were edited.

```yaml
disposition: revise
reviewed_claim: "One immutable DeliveryPortfolioSnapshot with versioned list/detail derivation, two production scopes (outcome, change-integration), orthogonal Stage/Needs/Activity/Progress/Action, a code-specific Integration correction matrix, and an atomic Cockpit HTTP+frontend cutover to a grouped table with a routed inspector, coherently represent the live schema-v2 Delivery lifecycle and can be implemented in the stated six-phase sequence."
review_depth:
  actions: [critical-read, coherence-check, focused-contract-check, source-research]
  evidence_limit: "Read-only source inspection plus three live HTTP reads of the running Cockpit. No tests were run, no browser automation or screenshots, no viewport geometry, no independent reproduction of the reported PDS flyout Escape overlay. Only one live Change state existed (one completed Outcome plus a merge-conflict Integration row), so multi-Outcome, waiting, request, requestless-block, Design-return, recovery, retryable, operator-required, active-repair, and empty-portfolio states were verified against source and fixtures only."
dimensions:
  product_value: {disposition: pass, evidence: "Live leakage reproduced: the completed Outcome OUT-001 detail carries the Change's merge-conflict attention verbatim, including 12 raw git records. Grouping, scope correctness, and semantic-first detail address observed failures."}
  mental_model: {disposition: warning, evidence: "Section 4 and section 5 define two incompatible Needs enums, and a Design-returned Outcome has no defined Needs, Activity, Action, or exit path even though production can create one."}
  authority_and_control: {disposition: warning, evidence: "Integrate-now is already authorized by the existing retry route, but derivation ownership between the snapshot, work_items.py, and the MCP contract is unassigned, and backward movement for repair-authority is permitted in section 5 and forbidden in section 6."}
  failure_and_reentry: {disposition: error, evidence: "The correction matrix omits the target-changed case that orchestration already treats as retryable, and administrative movement lacks a published-completion guard plus the ordering constraint the frontier validator imposes."}
  information_hierarchy: {disposition: warning, evidence: "The group lifecycle chip derived from change_stage() reports Design for a Change whose builders are running, and Integration progress is tautologically m of m."}
  proportionality: {disposition: pass, evidence: "The snapshot is a net reduction if it replaces the legacy authority adapter; the persisted DeliveryIntegrationConflict model is unnecessary because retained diagnostics already carry the paths."}
```

---

## 1. Disposition

**Revise.** Every load-bearing root cause in the consolidated plan verifies against production source and the live API. The direction — snapshot ownership, two scopes, orthogonal axes, grouped table, routed inspector, atomic cutover — is correct and should not be reopened. Four blockers and nine majors are bounded amendments to wording, matrix rows, guards, and sequence, not redesigns.

---

## 2. Findings

### Blockers

**B1 — The plan defines two incompatible `Needs` enums.**
Section 4 defines Needs as "You, Agent, Dependency, Repair, Nobody". Section 5 defines it as "`you`, `dependency`, `repair`, `none`" with Agent moved to Activity. Section 8 then requires "Requests and blocks produce distinct Needs states", which contradicts section 5 again — under production both are operator-actionable and both map to `you` ([work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L200-L202) sets `USER` for any unresolved block, and blocks are created 1:1 with requests in [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L1390-L1431)).
*Consequence:* the implementer must guess the enum; filter chips, totals, and every acceptance test bind to the guess.
*Amendment:* Needs is exactly `you | dependency | repair | none`. Delete "Agent" from the section 4 table. Replace the section 8 bullet with: "An unresolved request and a requestless block both read Needs: you but carry distinct headlines and distinct action kinds (`answer-request` vs `clear-block`)."

**B2 — The Integration correction matrix omits the target-changed case, which production already treats as retryable.**
[portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L641-L660) admits a Change to `integration_ready_change_ids` when its attention's `target_head` differs from the current target head, and [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L663-L686) suppresses such attention from operator listing entirely. Cockpit does the opposite: [target_work.py](serve/cockpit/src/owlbear_cockpit/routes/target_work.py#L126-L140) rejects retry for any non-retryable disposition regardless of target movement, and `DeliveryOperatorIntegrationAttention` ([portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L385-L392)) exposes no head identities, so the UI cannot detect it.
*Consequence:* after `dev` moves, orchestration retries the Change while Cockpit displays an unresolvable merge conflict and refuses the retry — precisely the stale-evidence failure the redesign claims to remove.
*Amendment:* add a derived boolean `superseded` computed with the same predicate as `list_integration_attention`; add a matrix row "Attention superseded (target moved) → **Retry Integration**, labelled *The integration target moved since this attempt*"; and align the retry gate in `TargetCockpitService.retry_integration` to that predicate.

**B3 — Derivation ownership is unassigned, so the snapshot creates a third projection instead of replacing the second.**
MCP `list_work_items` / `show_work_item` ([target_server.py](serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py#L212-L220)) return the same projections the Cockpit list uses, produced by `_work_item_projector` ([portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L772-L777)) through the legacy adapters `_project_runtime_authority` and `_project_runtime_evidence` ([portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L108-L166)). The plan forbids two projections only for Cockpit list and detail.
*Consequence:* MCP and Cockpit diverge on exactly the fields being corrected — Design stage, request-vs-block, Activity — and the "one immutable owner" claim fails. This is what makes the snapshot look like needless complexity.
*Amendment:* state that `DeliveryPortfolioSnapshot` **replaces** both adapters and is the sole derivation input for the MCP projection as well; `WorkItemProjection` / `WorkItemDetail` keep their wire shape while their corrected semantics propagate intentionally. Name the owning module for each new type (snapshot and axis derivation in `serve/delivery`; DTO mapping in `serve/cockpit`). Name the code to delete: `_project_change_design`, `_project_change_assembly`, the `AuthorityStatus`/`superseded_by` branches, and the `TargetAuthority` dependency of [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L128-L135) — and the tests that must move with them ([test_work_items.py](serve/delivery/tests/test_work_items.py), [test_target_public_surface.py](serve/delivery/tests/test_target_public_surface.py), [test_target_runtime.py](serve/delivery/tests/test_target_runtime.py#L477)).

**B4 — A Design-returned Outcome has no defined presentation and no exit, and the promised design-reentry briefing is never populated.**
Production can put a binding in DESIGN ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L664-L668)), but it is then not claimable ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L946-L958)), has no valid worker role, and cannot be moved backward because movement requires a strictly earlier stage ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L1165)). It is inert until re-admission. Separately, `WorkItemDetail.briefing` is always `None` in production: `_project_runtime_evidence` never sets `design_reentry_briefings` and `_project_runtime_authority` never sets `design_reentries`.
*Consequence:* the corrected projection produces a permanently stalled row that reads idle-and-healthy — a worse supervision failure than today's mislabel — and section 5's promise to "merge acceptance and briefing into Cockpit detail" delivers acceptance only.
*Amendment:* define the Design row explicitly — Needs `you`, Activity `idle`, progress "Returned to Design — re-admission required", action kind `none`. Source the detail section from `return_context` (target, reason, locators, `source_boundary`), not from `briefing`; delete `briefing` from the plan's detail model.

### Majors

**M1 — Conflicted paths must be parsed from retained diagnostics, never recomputed.**
`_integration_conflict_paths` ([change_workspace.py](serve/delivery/src/owlbear_delivery/change_workspace.py#L980-L994)) is private, re-executes `git merge-tree -z`, and calls `_workspace_failure` when no conflict exists — so a read-only detail fetch could raise, surfacing as HTTP 409. The live attention response proves recomputation is unnecessary: the retained `diagnostics` already contain both `<mode> <oid> <stage>\t<path>` records and `CONFLICT (content): Merge conflict in <path>` lines, written at [change_workspace.py](serve/delivery/src/owlbear_delivery/change_workspace.py#L970-L978) and stored at [change_workspace.py](serve/delivery/src/owlbear_delivery/change_workspace.py#L877-L881).
*Amendment:* derive paths in the projection by parsing `attention.diagnostics` — prefer the `CONFLICT (…) in <path>` lines, fall back to stage records with de-duplication (each path appears up to three times), degrade to raw-only when nothing parses. Drop the persisted `DeliveryIntegrationConflict` model. Add an explicit rule: **no Git process may run on a read path.**

**M2 — The group lifecycle chip is misleading.** `change_stage()` ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L972-L982)) returns `design` if *any* binding is in DESIGN, ahead of active delivery. A Change with one returned Outcome and three building Outcomes reads "Design". *Amendment:* derive the chip as Complete > Integration > In delivery, and express Design return through the row Needs plus a group Needs rollup.

**M3 — Integration progress is tautological.** The Integration item exists only when every binding is COMPLETED ([portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L139-L150)), so `n of m Outcomes complete` is always `m of m` and duplicates the group header rollup. *Amendment:* the Integration row's progress cell carries attempt state — `Not attempted` / `Attempt failed` / `Repair in progress` / `Superseded` — and the group header owns completion.

**M4 — Administrative-movement guards are incomplete and order-sensitive.** [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L1158-L1189) checks only stage order and move-id uniqueness. It does not reject an active `integration_repair_claim`, does not clear `integration_attention`, and does not reject a Change with a published `integration_completion` — nothing in `_validate_identities` ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L487-L510)) forbids attention on non-completed bindings. Ordering is forced: rejection must precede clearing, because `_validate_integration_repair_claim` ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L512-L531)) rejects a frontier holding a repair claim with no attention. *Amendment:* add all three guards in that order; add a pure preview over `_completed_dependent_closure`; note that `DeliveryOperatorMove.invalidated_outcome_ids` has `min_length=1`, so the preview and the move always name at least the moved Outcome.

**M5 — Sections 5 and 6 contradict each other on repair-authority.** Section 5 permits "version-bound backward preview/move" for repair-authority; section 6 states "Backward movement is unavailable while unresolved Integration attention exists". The runtime's own retry condition for that code is "Revise admitted authority or move the change to an earlier stage" ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L929-L937)), and at that point every binding is COMPLETED, so backward movement is the only exit. *Amendment:* narrow the section 6 prohibition to "while a merge-conflict attention is under an active repair claim".

**M6 — `repair-authority` renders as nothing, and Activity `repairing` has no wire source.** [attentionVocabulary.ts](serve/cockpit/web/src/attentionVocabulary.ts#L26-L35) has no `repair-authority` key, so the label lookup yields `undefined`; the TS union at [workItems.ts](serve/cockpit/web/src/api/workItems.ts#L4-L13) omits it; `DeliveryWorkerRole` at [workItems.ts](serve/cockpit/web/src/api/workItems.ts#L3) omits `integration-repairer`; and `integration_repair_claim` is exposed by no HTTP field. *Amendment:* add the label, both union members, and a `repair_active` boolean on the Integration projection (the value already exists as `WorkItemIntegrationState.repair_active`).

**M7 — Totals arithmetic is undefined under two partitions, and `in_progress_idle` is a no-op as described.** Today `attention == none` holds if and only if `stage == completed` — `_project_outcome` assigns `AGENT` to every unclaimed Planning Outcome — so Opus's "split `none`" changes nothing on its own; it is meaningful only as a consequence of re-deriving Needs and Activity. Meanwhile [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L36-L47) sums five attention counts as the total and both the Vitest suite and the E2E "6work items" assertion bind to it. *Amendment:* define total = rendered row count; the Needs partition sums to total; the Activity partition sums to total; `complete` is a lifecycle count and not a Needs bucket.

**M8 — Sol's routing finding is directionally right but its consequence is overstated.** [App.tsx](serve/cockpit/web/src/App.tsx#L20-L25) registers `{ path: '*' }`, so `/delivery/:changeId/:itemKey` renders today, and [CockpitShell.tsx](serve/cockpit/web/src/CockpitShell.tsx#L69) falls back to `routeConfig[0]`, which happens to be `/delivery`, so nav highlighting is accidentally correct. *Consequence:* deep links work by coincidence; reordering `routeConfig` silently breaks them, and every unknown path renders Delivery. *Amendment:* replace the exact-path match with a route-family prefix match plus an explicit not-found fallback, and place this in the atomic cutover phase rather than polish.

**M9 — The acceptance set has no proof for seven verified risk areas.** Missing: superseded/target-changed Integration retry; `repair-authority` label and its backward-movement route; administrative movement rejected after a published completion; the Design-returned row's Needs/Action/progress; the group chip for a Change mixing Design and Implementation; MCP projection parity after re-derivation; conflicted-path parse degradation to raw-only; and an assertion that no read path spawns Git.

### Minors

- **m1.** Both documents cite `serve/cockpit/web/src/components/WorkItemCard.tsx`. No such file exists — `WorkItemCard` is a local function at [WorkPortfolioBoard.tsx](serve/cockpit/web/src/components/WorkPortfolioBoard.tsx#L22). Correct the source table.
- **m2.** Change identities are lowercase slugs ([target_contract.py](serve/delivery/src/owlbear_delivery/target_contract.py#L16)); the live id is `knowledge-source-contract-alignment` against title "Knowledge Source Contract Alignment". This validates the "hide the id when it is the title slug" rule — say so, and replace the fictional `CHG-014` examples.
- **m3.** `lifecycle.is_superseded` can never be true: `DeliveryOutcome` has no `superseded_by`, so the round-trip at [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L124) always yields `()`. Delete the field rather than shipping a permanently false flag.
- **m4.** The progress table has no row for an Outcome in Assembly — the live E2E fixture OUT-003 is exactly that state, and it would read `1 of 1 tasks reviewed` while incomplete. Add "Outcome in Assembly → *Tasks reviewed — assembling*".
- **m5.** Phases 1–3 touch `serve/delivery/` and phase 4 touches `serve/cockpit/`; the architecture rule requires one domain per task. State the split so tasks decompose cleanly.
- **m6.** `onChanged` currently re-enters `useWorkPortfolio` through `retryNonce`, showing the loading status beside retained data ([useWorkItems.ts](serve/cockpit/web/src/hooks/useWorkItems.ts#L46-L60)). Polling must replace that path, not layer on top of it.

### Sequence coherence

The six-phase order has no dependency cycle, but phase 1 mixes two kinds of work and creates an incoherent intermediate state: "distinguish unresolved requests from requestless blocks" and "remove unsupported Change Design/Assembly/supersession" both edit `work_items.py` immediately before phase 2 replaces its input. *Amendment:* phase 1 contains **runtime invariants only** (the three movement guards); all projection edits move into phase 2 with the snapshot re-point.

---

## 3. Sol's accepted corrections — confirmed or falsified

| Sol correction | Verdict | Exact evidence |
|---|---|---|
| No production Change Design / Change Assembly / supersession | **Confirmed** | Contract requires ≥1 outcome; adapter emits only `PlanScopeKind.OUTCOME`; `DeliveryOutcome` has no status or `superseded_by` |
| Runtime Design projects as Planning | **Confirmed** | DESIGN bindings are excluded from `planned_scope_ids`, so `_project_outcome` falls to the Planning branch |
| Assembly is an Outcome stage, not a Change scope | **Confirmed** | `assembly_required` on the binding drives `composition_claim`; live fixture OUT-003 |
| Identity collision is latent, not live | **Confirmed** | Live Integration self-link is `/outcomes/knowledge-source-contract-alignment` |
| `ready` is not an attention disposition | **Confirmed** | `DeliveryIntegrationAttentionDisposition` has three members; `ready` lives only on `WorkItemIntegrationDisposition` |
| Conflict paths need a maintained parser, not the existing helper | **Confirmed and refined** | The helper re-runs Git and fails closed; the retained diagnostics already contain the paths (M1) |
| `Integrate now` expands current UI authority | **Partially falsified** | `/integration/retry` already calls `integrate_ready_change` when attention is absent ([target_work.py](serve/cockpit/src/owlbear_cockpit/routes/target_work.py#L126-L140)); the change is UI-visible only, and the plan's resolution is correct |
| `resume-design` has no Cockpit route | **Confirmed and stronger** | There is no runtime path out of DESIGN at all (B4) |
| `repair-authority` needs revision or backward movement | **Confirmed** | And the consolidated plan reintroduced the contradiction (M5) |
| Movement neither clears attention nor rejects an active repair claim | **Confirmed, plus a third gap** | No published-completion guard, and the clearing order is constrained (M4) |
| AGENT assigned without a claim | **Confirmed and stronger** | `attention == none` ⟺ `stage == completed`, so `in_progress_idle` is always zero today (M7) |
| Separate runtime reads, no version | **Confirmed** | List, detail, and operator context each re-read and re-validate the frontier through `_read()` |
| No polling despite an existing primitive | **Confirmed** | `useWorkPortfolio` fetches on mount and nonce only; `usePollingFetch` supports pause, abort, and generation guarding |
| Completion handoff undefined | **Confirmed** | `list_work_items` skips `DeliveryChangeStage.COMPLETED` |
| Work Item projections are also an MCP contract | **Confirmed** | [target_server.py](serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py#L212-L220) |
| Route family, focus, and table navigation | **Confirmed, consequence corrected** | M8 |
| Acceptance proof gaps | **Confirmed** | Python route tests use a fake application; Vitest mocks the API module; the E2E dismisses by button, not Escape |
| Merge `briefing` into Cockpit detail | **Falsified as valuable** | Never populated in production (B4) |

Opus items also checked: `WorkItemLinks` is returned and never used (**confirmed** — the client rebuilds every URL); the E2E depends on `data-stage-heading` / `data-stage-empty` (**confirmed**); `dependency_ready` is initialised from attention (**confirmed but not user-visible** — the plan's downgrade is right); "reuse `_integration_conflict_paths`, no new Git work" (**falsified**, M1).

---

## 4. Replacement language, ready to insert

**§4, Needs row —** replace with:

> **Needs** | Orthogonal condition requiring intervention or blocking progress: **You**, **Dependency**, **Repair**, **Nobody**. Agent execution is not a Needs value; it is carried by Activity.

**§4, add after the Assembly sentence —**

> An Outcome returned to Design is inert: production offers no claim, no worker role, and no backward move out of Design. It renders Needs **you**, Activity **idle**, progress *Returned to Design — re-admission required*, and no typed action. Its detail section is sourced from `return_context` (target, reason, locators, source boundary); the design-reentry briefing is never populated in production and is not part of this plan.

**§5, replace the correction matrix with —**

| Integration state | User-visible correction |
|---|---|
| Ready, no attention | **Integrate Change** — the existing `/integration/retry` route already calls `integrate_ready_change` |
| Retryable attention | **Retry Integration** |
| Attention superseded — current target head differs from the attention's target head | **Retry Integration**, labelled *The integration target moved since this attempt*; same predicate as `list_integration_attention` |
| Merge conflict, no repair claim | Copy or run the reviewed repair command; no direct retry |
| Merge conflict, active repair claim | Activity **repairing**; administrative movement rejected |
| Repair authority | Backward preview and move permitted; retiring the attention is part of the same transition |
| Other operator-required | Explain the exact recovery condition; expose only actions authorized for that code |

**§5, add —**

> `DeliveryPortfolioSnapshot` replaces `_project_runtime_authority` and `_project_runtime_evidence`; it is the sole derivation input for the Cockpit list, the Cockpit detail, and the MCP `WorkItemProjection` / `WorkItemDetail`. MCP wire shapes are preserved; corrected semantics propagate to MCP intentionally. Unreachable projector branches — Change Design, Change Assembly, authority status, and supersession — are deleted with their tests. Conflicted paths are derived by parsing the retained `attention.diagnostics` already produced by `merge-tree`; no read path may execute Git.

**§6, replace the movement sentence —**

> Backward movement is unavailable only while a merge-conflict attention is held under an active repair claim. For repair-authority and other operator-required attention, movement is the sanctioned correction and retires the attention in the same transaction.

**§7, replace steps 1–2 —**

> 1. Runtime invariants only, in `serve/delivery/`: reject administrative movement during an active Integration repair claim; reject it after a published Integration completion; clear stale Integration attention in the same replacement when the move leaves Integration — rejection strictly before clearing, because the frontier validator forbids a repair claim without attention.
> 2. Introduce `DeliveryPortfolioSnapshot` in `serve/delivery/`, re-point both the MCP projection and the Cockpit derivation at it, delete the legacy adapters and unreachable branches, and correct request-versus-block and Design-stage derivation there — once, not twice.

**§8, add acceptance observations —**

> Superseded Integration attention offers retry and is labelled as superseded. `repair-authority` renders a real label and permits a previewed backward move. Administrative movement is rejected after a published completion and during an active repair claim. A Design-returned Outcome renders Needs you with its return context and no action. A Change mixing Design and Implementation reads *In delivery*, not *Design*. MCP `list_work_items` output is asserted against the same snapshot the Cockpit list uses. Unparseable conflict diagnostics degrade to raw evidence only. No read path spawns a Git process.

---

## 5. Risk and confidence per layer

| Layer | Confidence after amendments | Residual risk |
|---|---|---|
| Root-cause chain | 99% | None — leakage, dead scopes, request/block conflation, and raw diagnostics were reproduced against source and the live API |
| Production lifecycle model | 99% | Design-stage inertness is a product decision, not a coding risk |
| Snapshot ownership | 97% | Medium: cost of retiring `WorkItemProjector`'s public surface and its tests is real but bounded and known |
| Integration correction matrix | 97% | Medium: `target_changed` requires a workspace read per Change; verify it stays cheap for many Changes |
| Conflicted-path parsing | 96% | Medium: format-coupled to `merge-tree` output; mitigated by raw retention and a degradation test |
| Axis orthogonality | 98% | Low after B1 and M7 |
| HTTP/MCP cutover and sequence | 97% | Medium: phase 4 is genuinely atomic and rewrites the E2E suite; accepted and now correctly ordered |
| Table, routing, inspector | 95% | Medium: block-link plus native tab order inside a semantic table, and the PDS flyout Escape/unmount behaviour, remain unproven without a browser |
| Responsive geometry and accessibility | 92% | Highest remaining: split threshold, container-versus-viewport measurement, and axe results are proof items, not design items |

---

## 6. Direct answer

**Yes — after applying B1–B4, M1–M9, and the sequence correction, the plan is coherent enough to implement at ≥98% confidence.** No blocker requires a new stage, artifact, reviewer, or abstraction; each is a wording fix, a matrix row, a guard, or an ownership statement grounded in source. The residual gap to 100% is not conceptual: it is three unmeasured browser facts — the PDS flyout Escape and unmount behaviour, the real split threshold at the measured workspace width, and axe results on the new table — all of which the acceptance set already schedules as proof.