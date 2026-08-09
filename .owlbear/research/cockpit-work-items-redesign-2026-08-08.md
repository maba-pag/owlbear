# Cockpit Work Items Redesign

> **Owning task:** User-directed Cockpit Delivery redesign
> **Date:** 2026-08-08
> **Question:** What user model, data contract, and interaction design make Delivery Work Items coherent across their full lifecycle?

## 1. Context and Question

The current Delivery page renders internal Work Item projections directly as five stage columns and uses a scope-blind operator detail response. The result does not let an expert project owner distinguish the Change container, Outcome result, executable Task, lifecycle Stage, orthogonal attention/Needs state, active agent Activity, and change-level Integration work.

This is an information-architecture and data-boundary problem, not a styling problem. The redesign must support four user jobs:

1. **Triage:** determine within seconds whether anything needs the user.
2. **Supervise:** understand whether each Change and Outcome is progressing.
3. **Inspect:** understand the promise, acceptance, progress, and evidence for one item.
4. **Intervene:** answer, clear, recover, repair, or administratively return work when exceptional states require it.

The complete original Opus 5 plan is preserved verbatim at `.owlbear/research/cockpit-work-items-redesign-evidence/opus-original-plan.md` (41,918 bytes; SHA-256 `1bd0045a11cbdf60f2ab987f89370e9093fdf13b76905e45b7e17213639f174e`). The first deep plan review is preserved at `.owlbear/research/cockpit-work-items-redesign-evidence/sol-plan-review.md` (11,202 bytes; SHA-256 `cf4bdec633d963a76afa4736fe3948c16ab5c5889c50de74bae954caf64af90e`). The final Opus 5 plan gate is preserved at `.owlbear/research/cockpit-work-items-redesign-evidence/opus-final-plan-review.md` (27,139 bytes; SHA-256 `284f1b8a5cd5b24e0774de37135c3e241402d5ca5ec1142bb7c8068f27d7d303`). The post-implementation top-down Opus 5 review is preserved at `.owlbear/research/cockpit-work-items-redesign-evidence/opus-top-down-implementation-review.md` (35,371 bytes; SHA-256 `a1cf7f96a903ad0d3bef492bd4a354b7c49f577f52c23b7c57104924dd3e8028`). This document records the consolidated plan after source verification, live visual challenge, and accepted Sol and Opus corrections.

## 2. Sources Studied

| Source | Relevant evidence | Limit |
|---|---|---|
| `serve/delivery/src/owlbear_delivery/work_items.py` | Projection scopes, stages, attention, progress, identity collision | Read model, not user intent |
| `serve/delivery/src/owlbear_delivery/portfolio_application.py` | Runtime evidence and operator detail composition | Current behavior only |
| `serve/delivery/src/owlbear_delivery/delivery_runtime.py` | Requests, blocks, claims, Integration attention/dispositions | Engine terminology |
| `serve/delivery/src/owlbear_delivery/target_authority.py` | Changes, Outcomes, commitments, acceptance | Semantic authority |
| `serve/cockpit/src/owlbear_cockpit/routes/target_work.py` | HTTP list/detail/control boundary | Adapter behavior |
| `serve/cockpit/web/src/components/WorkPortfolioBoard.tsx` | Five-column stage board | Current implementation |
| `serve/cockpit/web/src/components/WorkPortfolioBoard.tsx` | Board and card hierarchy, including tiny detail target | Current implementation |
| `serve/cockpit/web/src/components/WorkItemDetail.tsx` | Scope-blind sections and dominant rare controls | Current implementation |
| `serve/cockpit/web/src/api/workItems.ts` | Frontend contract and type gaps | Current contract |
| Live Cockpit `/delivery`, 1600x1000 and 1100x700 | Geometry, hierarchy, flyout behavior | One live portfolio state |
| Three focused research agents | Domain map, frontend audit, API/data map | Read-only synthesis |
| Opus 5 conceptual review | Ground-up WHY/WHAT/HOW plan | Initial reviewer lacked browser tools |
| Opus 5 live visual challenge | Measurements and responsive corrections | Current rendered state only |

## 3. Verified Root Causes

1. **Projection leakage:** outcome `DeliveryOperatorContext` receives the Change's Integration attention. A completed Outcome therefore displays a merge conflict owned by Integration.
2. **Incomplete detail boundary:** Cockpit asks for operator context but drops `WorkItemDetail.acceptance` and design-reentry briefing, leaving exceptional controls without semantic context.
3. **Production-model mismatch:** Cockpit round-trips the schema-v2 `DeliveryContract + DeliveryFrontier` through a richer legacy `TargetAuthority` projector. That projector supports pre-admission Change Design, Change Assembly, and supersession, but the production contract requires active Outcomes and has none of those authorities. It also maps a returned Outcome in runtime Design to projected Planning.
4. **Abstract identity collision:** the richer projector keys Change Assembly and Integration by the same Change ID. Production cannot currently create Change Assembly, so this is not a live concurrent-state bug; it is evidence that scope must be explicit and that unsupported projector states must not define the Cockpit contract.
5. **Request/block conflation:** unresolved blocks populate `pending_request_work_item_ids`, making the projection name and user meaning false.
6. **Axis conflation:** Stage, attention, Activity, progress, and action are compressed into `stage`, `attention`, task counts, and free-text `next_action`.
7. **Container loss:** the stage board fragments Outcomes from one atomically integrated Change across unrelated columns; duplicate bare Change IDs are the only grouping cue.
8. **Wrong applicability:** task counts render on scopes where tasks are not the concept, producing `No tasks yet` on Integration.
9. **Exception-first detail:** empty Requests and always-visible backward movement occupy more space than promise, acceptance, and result evidence.
10. **Unstructured diagnostics:** raw `merge-tree` output is joined into a wall despite conflict-path parsing already existing in the domain.
11. **Transient interaction defect:** closing the PDS flyout with Escape can leave a visible, pointer-active slotted detail overlay that blocks the board.
12. **Correction invariant gap:** administrative backward movement preserves Integration attention and does not reject an active Integration repair claim, even though `repair-authority` explicitly requires revision or earlier-stage movement.
13. **Freshness gap:** the current portfolio fetches only on mount and local mutation, so background agent progress is invisible until manual navigation or refresh.
14. **Completion continuity gap:** a Change disappears from current delivery after Integration without defining how an open inspector transitions to completed history.

`dependency_ready` is also semantically muddled by deriving its initial value from user attention, but the dependency pass corrects blocked dependency cases. Treat it as part of the view-model redesign, not as an isolated production incident.

## 4. User Layer: Why and Vocabulary

Use one canonical term per concept:

| Term | User meaning |
|---|---|
| **Change** | One admitted body of work integrated as a unit; the portfolio grouping root |
| **Outcome** | One promised user-facing result under a Change |
| **Work item** | An admitted Outcome or the Change-level Integration row |
| **Task** | One executable build unit under a planned Outcome or Assembly scope |
| **Stage** | Lifecycle position: Design, Planning, Implementation, Assembly, Complete |
| **Needs** | Orthogonal condition requiring intervention or blocking progress: You, Dependency, Repair, Nobody |
| **Activity** | A currently held agent claim, including role and elapsed time |
| **Integration** | Change-level publication to the configured target |

Delete `Reviewed` as an alias for `completed`; show **Complete** for an Outcome and separately show the enclosing Change lifecycle as **Design**, **In delivery**, **Integration**, or **Complete**. Replace user-facing `Attention` with explicit **Needs** language. Never expose raw enum tokens as labels.

Current Delivery begins at admitted Outcomes. Pre-admission Change Design belongs to the Design workflow, not this page. Assembly is an Outcome stage in schema-v2 production. Superseded Outcomes are not part of the active `DeliveryContract`; semantic revision history belongs to completed or design authority rather than being invented as current Work Items.

An Outcome returned to Design is inert in current production: it is not claimable, has no worker role, and cannot move farther backward. It renders Needs **you**, Activity **idle**, progress *Returned to Design — re-admission required*, and no typed Action. Its detail is sourced from `return_context` (target, reason, locators, and source boundary); the richer projector briefing is never populated by the production adapter and is not part of this plan.

Portfolio rows always show scope/identity, title, Stage, applicable progress, Needs, live Activity, and typed Action independently when one exists. Promise, acceptance, bounded result evidence, dependencies, and references belong in detail. Requests, blocks, recovery, return context, design reentry, and Integration attention render only when present. Raw diagnostics and administrative actions are collapsed by default.

## 5. Data Layer: What

Replace the lossy production-to-legacy projection with one immutable source snapshot and two explicit presentation levels:

- `DeliveryPortfolioSnapshot`: one `DeliveryContract` plus one validated `DeliveryFrontier` read, current Integration-target context, its SHA-256 version, and derived Change lifecycle/claimability. This is the only projection input.
- `ChangeGroupView`: `change_id`, display title, snapshot version, Change lifecycle, Outcome totals, and child items.
- `WorkItemCardView`: scope-aware opaque key, title, lifecycle, Needs, Activity, applicable progress, and typed Action.
- `WorkItemDetailView`: derived from the same snapshot version with identity, promise, acceptance, bounded task/result evidence, resolved commitments/dependencies, state, and nullable conditional operator sections.

`DeliveryPortfolioSnapshot` replaces `_project_runtime_authority` and `_project_runtime_evidence` and is the sole derivation input for Cockpit list/detail and MCP `WorkItemProjection`/`WorkItemDetail`. Snapshot and axis derivation live in `serve/delivery`; Cockpit DTO mapping lives in `serve/cockpit`. MCP wire shapes remain stable while corrected semantics propagate intentionally. Delete unreachable projector branches for Change Design, Change Assembly, authority status, and supersession with their obsolete tests. Do not maintain two independent state projections: list and detail derive from the same frontier bytes.

Required semantics:

- Use two production scopes: `outcome` and `change-integration`.
- Use an opaque scope-qualified key such as `outcome:OUT-001` or `integration`; never infer scope from `outcome_id == change_id`.
- Integration attention is legal only for `change-integration` detail.
- Project active claims to portfolio Activity.
- Replace `next_action: str` with a typed action kind, label, and optional command.
- Keep Needs, Activity, and Action orthogonal. Needs is exactly `you`, `dependency`, `repair`, or `none`; Activity is exactly `idle`, `ready`, `working`, or `repairing`; Action remains independently visible even when Activity exists. An unresolved request and a requestless block both read Needs **you**, but carry distinct headlines and action kinds (`answer-request` and `clear-block`).
- Split active-idle from complete rather than overloading `attention == none`; totals count Needs and Activity separately rather than forcing one partition to represent both.
- Resolve dependency IDs to titles/stages and commitment IDs to statements in detail.
- Expose acceptance and `return_context` in Cockpit detail; do not expose the unpopulated legacy briefing.
- Add `repair-authority` to the frontend attention-code union and keep backend/frontend dispositions aligned.
- Include the snapshot version on list/detail and require it for stale-sensitive preview/mutation pairs.
- Poll the current portfolio and selected detail through the existing race-safe polling primitive; reconcile only responses from the latest snapshot/request generation.

Progress applicability:

| Scope | Progress |
|---|---|
| Outcome returned to Design | `Returned to Design — re-admission required` |
| Outcome with plan | `n of m tasks reviewed` |
| Outcome before plan | `Task plan not published` |
| Outcome in Assembly | `Tasks reviewed — assembling` |
| Integration | `Not attempted`, `Attempt failed`, `Repair in progress`, or `Superseded` |

Structured Integration detail contains code, disposition, human headline/explanation, conflicted paths, retry condition, typed action, superseded flag, repair-active flag, and retained raw evidence. Derive paths by parsing retained `attention.diagnostics`: prefer `CONFLICT (...) in <path>` records, fall back to de-duplicated stage records, and degrade to raw-only evidence. No read path may execute Git. Default presentation is `Merge conflict — 3 files conflict between this Change and dev`, a path list, the required next step, and a copyable command. Raw Git records remain behind disclosure.

Correction behavior is code-specific:

| Integration state | User-visible correction |
|---|---|
| Ready, no attention | **Integrate Change**; existing Cockpit authority calls `integrate_ready_change` |
| Retryable | **Retry Integration** when the retry condition is current |
| Attention superseded because the Integration target moved | **Retry Integration**, labelled *The Integration target moved since this attempt*; use the same target-head predicate as orchestration |
| Merge conflict | Copy/run reviewed repair command; no direct retry |
| Active repair claim | Show repairing Activity; reject administrative movement |
| Repair authority | Permit version-bound backward preview/move or semantic revision; retiring Integration attention is part of the same transition |
| Other operator-required attention | Explain exact recovery condition; expose only actions authorized for that code |

Backward movement becomes a preview/confirm operation. Preview returns the exact non-empty invalidated Outcome closure and snapshot version. Confirm requires that version; rejects a published Integration completion and an active repair claim before any clearing; applies the move; and transactionally retires stale Integration attention when the Change exits Integration. Backward movement is unavailable only while a merge-conflict attention is held under an active repair claim. Repair-authority explicitly permits a previewed move because movement or semantic revision is its sanctioned correction.

Outcome detail includes bounded evidence, not only acceptance and counts: task title/result, task status, reviewed commit when present, acceptance observations/proof boundaries, and technical references. Completed history remains a separate projection and route, but current-item completion has a defined handoff to the latest completed Change record.

## 6. Design Layer: How

Replace the five-column kanban with a compact Change-grouped operational table. Engine-owned Stage is not a draggable workflow, and a stage board is the wrong axis for triage and Change supervision.

Group header: Change title, conditionally displayed non-duplicative slug ID, derived Change lifecycle, and Outcome rollup. The lifecycle is **Complete** after publication, **Integration** when all Outcomes are Complete, and otherwise **In delivery**; a returned Design Outcome affects the group Needs rollup rather than relabelling a concurrently active Change as Design. Child rows are admitted Outcomes in contract order, followed by Integration only when every Outcome is Complete.

Table columns:

`Needs | Work item | Stage | Progress | Activity | Action`

- Needs owns urgency color and an icon/text channel; Stage remains neutral.
- The work-item cell contains a real routed anchor whose hit area spans the row; separate action controls remain independently focusable. Use native tab order, not roving tabindex or an incomplete ARIA grid pattern.
- Selection uses background and outline, not the urgency border.
- Hide `change_id` when it is merely the lowercase slug of the visible title; use real slug identities rather than fictional `CHG-NNN` examples.
- Use compact 40px rows and aligned columns for comparison.

Detail uses `/delivery/:changeId/:itemKey` so it survives reload and browser navigation. Route-family matching must keep Delivery navigation active. Use a persistent 480-520px inspector only when measured workspace width leaves the table's work-item column readable; otherwise use a correctly unmounted PDS flyout. The initial browser expectation is approximately 1440px viewport, but container/workspace width, not viewport width alone, owns the mode.

Ordinary Outcome order: identity; labelled Promise; acceptance; bounded task/result evidence; Stage/progress/Activity; then only present exceptional sections. Integration order: identity; promise; Integration condition/action immediately; structured paths; collapsed raw evidence. References and administrative actions remain collapsed. Backward movement is unavailable during active repair; permitted correction states use preview/confirm and disclose affected Outcomes before mutation.

At compact widths, rows become two lines rather than reintroducing narrow cards. Loading uses geometry-preserving skeleton rows. Empty current delivery shows one message, not five empty-column explanations. Errors stay local to the failed surface. Split-to-flyout mode changes preserve the selected route, restore focus to the invoking row when closed, and fully unmount or disable the dismissed overlay.

## 7. Implementation Sequence

1. In `serve/delivery`, establish runtime invariants only: reject administrative movement during an active repair claim and after published Integration completion; clear stale Integration attention in the same valid correction, with rejection before clearing because frontier validation forbids a repair claim without attention.
2. In `serve/delivery`, add the canonical `DeliveryPortfolioSnapshot`, repoint MCP and Cockpit derivation at it, delete legacy adapters/unreachable branches, and correct request/block and Design-stage semantics once.
3. Add semantic/evidence projection, structured Integration diagnostics, correction preview/version contracts, and current-to-history lookup.
4. Across `serve/cockpit` backend and web as one Cockpit-domain cutover, replace the HTTP/frontend contract with grouped rows, typed Needs/Activity/Action, route-family matching with explicit not-found behavior, routed selection, and conditional inspector. Do not ship a frontend expecting the new contract against the old endpoint.
5. Replace nonce refresh with race-safe polling/reconciliation, then add responsive split/flyout behavior, completion handoff, and local action feedback.
6. Complete keyboard, focus, loading/error, accessibility, long-content, and visual proof.

Each phase must preserve a coherent production invariant and receive focused backend validation. Phase 4 is an intentional atomic HTTP/frontend cutover; its old and new UI contracts are not maintained in parallel.

## 8. Acceptance and Review Protocol

Minimum durable observations:

- Outcome detail never renders Change Integration attention.
- Integration detail presents structured paths; raw evidence is collapsed.
- Runtime Design Outcomes appear as Design, not Planning.
- Unsupported Change Design/Assembly/supersession rows never appear in current Delivery.
- Scope-qualified keys cannot collide.
- Requests and requestless blocks both produce Needs **you** with distinct headlines and action kinds.
- Task text never appears on Integration; Integration reports Outcome completion.
- Activity and Action can appear simultaneously without conflation.
- Empty conditional sections do not render.
- Promise and acceptance are present for Outcomes.
- Outcome detail contains bounded task/result evidence and technical references.
- A returned Design Outcome shows Needs **you**, its return context, no Action, and re-admission-required progress; a Change mixing Design and Implementation remains **In delivery**.
- Whole-row navigation updates URL; reload restores selection.
- Escape closes and unmounts the flyout; another row is immediately clickable.
- Close restores focus to the invoking row, including after split/flyout mode changes.
- Background progress refreshes current portfolio and selected detail without stale response overwrite.
- Backward preview names the exact invalidated Outcomes; stale confirmation is rejected.
- Active Integration repair rejects backward movement; repair-authority correction retires stale attention transactionally.
- Published Integration completion rejects backward movement.
- Superseded Integration attention offers retry and names target movement.
- MCP projections derive from the same snapshot and preserve their wire shape.
- Unparseable conflict diagnostics degrade to raw-only evidence, and no detail/list read spawns Git.
- A selected current item that completes transitions to completed history without a dead route.
- 1100px has no horizontal overflow or overlap; 1440px split pane preserves readable titles.
- Keyboard, focus, and serious/critical axe checks pass.

Review sequence requested by the user:

1. Deep Sol review of root cause, all three layers, and end-state coherence.
2. Verify and incorporate accepted Sol findings.
3. Deep Opus 5 plan review and accepted corrections.
4. Implement only once plan confidence is at least 98%.
5. Opus 5 implementation review; rate findings and repair accepted issues.
6. Second Opus 5 implementation review; repair accepted issues.
7. Commit only owned Delivery/Cockpit paths after complete validation.

## 9. Recommendation, Confidence, and Limits

**Recommendation:** implement the grouped-table and routed-inspector design after sequential deep review, but project it directly from the production `DeliveryContract + DeliveryFrontier` snapshot rather than the richer legacy Work Item authority. The board should not be incrementally restyled because its organizing axis and flattened data contract are root causes.

**Confidence after final Opus gate amendments:** root-cause analysis 99%; user layer 99%; production lifecycle 99%; data architecture 98%; portfolio direction 99%; detail direction 99%; correction matrix 98%; implementation sequence 98%. Exact responsive geometry remains an implementation proof item rather than a domain decision.

**Limits:** only one live Change state was available. Multi-Outcome, waiting, user-request, requestless block, design reentry, Outcome assembly, recovery, retryable/operator-required Integration, active repair, repair-authority correction, and empty portfolio states require fixtures and browser proof. Completion evidence must remain bounded enough for a fast detail query. Poll interval and exact split threshold should be tuned from assembled-browser measurements rather than treated as domain constants.
