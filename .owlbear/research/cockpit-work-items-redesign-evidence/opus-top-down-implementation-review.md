# Top-Down Review — Cockpit Delivery Work Items Redesign

**Scope reviewed:** `416d4b034` (product) + `f31372dcd` (indexes) on `dev`. Named hashes `6fb4dd8a…`/`da5c7c46…` exist as objects but the current branch tips are `416d4b034`/`f31372dcd`; the tree content is what I reviewed.
**Uncommitted state:** `.owlbear/research/cockpit-work-items-redesign-2026-08-08.md` differs only by three evidence-path strings; `.owlbear/research/cockpit-work-items-redesign-evidence/` is three untracked markdown files. **Confirmed documentation-only.**
**Live inspection:** `http://127.0.0.1:8420/delivery` returned connection code `000` — **the Cockpit is not running**, so no live browser verification was possible. All interaction findings are source-verified only.
**Tests run (read-only):** pytest 122 passed; Vitest 198 passed / 21 files; `tsc --noEmit` clean.

---

## A. Overall disposition

**FINDINGS** — 2 high, 5 medium, 5 low. The redesign's spine (snapshot ownership, two scopes, orthogonal Needs/Activity/Action, grouped table, routed inspector, structured Integration diagnostics, version-bound preview/confirm, movement guards) is genuinely implemented and correct. Two defects break the end-state lifecycle: an Integration proof failure that presents as "nobody needs to act", and a portfolio that self-destructs on a single failed background poll.

---

## B. Requirement-coverage matrix

| # | Accepted-plan clause | Status | Evidence |
|---|---|---|---|
| 1 | Outcome detail never renders Change Integration attention | **Met** | [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L367-L397) — `integration` only on `CHANGE_INTEGRATION` branch |
| 2 | Structured Integration paths; raw evidence collapsed | **Met** | [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L286-L296), [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L336-L343) |
| 3 | Runtime Design Outcomes appear as Design | **Met** | [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L410) |
| 4 | Change Design / Assembly / supersession rows deleted | **Met** | `WorkItemScope` has exactly two members |
| 5 | Scope-qualified keys cannot collide | **Met** | `outcome:OUT-NNN` / `integration` |
| 6 | Request and requestless block → Needs `you`, distinct actions | **Met** | [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L423-L441) |
| 7 | No task text on Integration | **Met** | `WorkItemProgressKind.INTEGRATION` labels |
| 8 | Activity and Action simultaneously visible | **Met** | recovery case yields `working` + `recover-claim` |
| 9 | Empty conditional sections do not render | **Met** | every section early-returns `null` |
| 10 | Promise and acceptance present for Outcomes | **Met** | [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L379-L393) |
| 11 | Bounded task/result evidence + technical references | **Met** | `WorkItemTaskEvidence`, `SemanticDetail` |
| 12 | Design-returned row: Needs you, return context, no Action, re-admission progress | **Partial** | progress string exists but is **absent from detail** — TOPDOWN-5 |
| 13 | Change mixing Design and Implementation reads *In delivery* | **Met** | [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L339-L347) — lifecycle never returns Design |
| 14 | Whole-row navigation updates URL | **Not met** | TOPDOWN-3 |
| 15 | Reload restores selection; route-family nav stays active | **Met** | [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L157-L164), [CockpitShell.tsx](serve/cockpit/web/src/CockpitShell.tsx#L68-L71) |
| 16 | Escape closes and unmounts the flyout | **Unproven** | conditional render is correct; no test — see §E |
| 17 | Close restores focus to invoking row | **Met** | [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L307-L320) |
| 18 | Background refresh without stale overwrite | **Partial** | polling correct; **error handling destroys the surface** — TOPDOWN-2 |
| 19 | Preview names exact invalidated Outcomes; stale confirm rejected | **Met** | [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L1171-L1213) |
| 20 | Active repair rejects backward movement | **Met** | [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L1562-L1575) |
| 21 | Repair-authority correction retires attention transactionally | **Met** | same replacement sets `integration_attention: None` |
| 22 | Published completion rejects backward movement | **Met** | [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L1569) |
| 23 | Superseded attention offers retry and names target movement | **Met** | [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L500-L505), [target_work.py](serve/cockpit/src/owlbear_cockpit/routes/target_work.py#L164-L182) |
| 24 | MCP projections derive from the same snapshot, wire shape preserved | **Met** | `_compatibility_projection`; `briefing` removal is plan-sanctioned (B4) |
| 25 | Unparseable diagnostics degrade to raw-only; no read path spawns Git | **Met in code, unproven** | `_workspace_manager.show()` reads persisted JSON; no assertion test |
| 26 | Completed selected item → history, no dead route | **Met** | [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L322-L337) |
| 27 | 1100/1440 geometry; serious/critical axe clean | **Met (fixture)** | [work-portfolio.spec.ts](serve/cockpit/web/e2e/work-portfolio.spec.ts#L44-L57) |
| 28 | `repair-authority` added to frontend attention-code union | **Not met** | TOPDOWN-8 |
| 29 | Explicit not-found fallback | **Not met** | TOPDOWN-9 |
| 30 | Never expose raw enum tokens as labels | **Not met** | TOPDOWN-4 |
| 31 | Totals: Needs partition = total; Activity partition = total; complete is lifecycle | **Met (backend)**, `complete` never rendered | [target_work.py](serve/cockpit/src/owlbear_cockpit/routes/target_work.py#L385-L406) |
| 32 | Commit only owned Delivery/Cockpit paths | **Not met** | TOPDOWN-12 |

---

## C. Findings

### TOPDOWN-1 — Candidate proof failure is a dead end presented as "nobody needs to act"
**Severity: high · Confidence: 95%**

**Location**
- [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L282-L292) — `CANDIDATE_PROOF_FAILED` reclassified `OPERATOR_REQUIRED → RETRYABLE` by this commit
- [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L515-L518) — `needs = NONE`, `headline = "Integration retry available"`
- [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L1013-L1021) and [#L1709-L1716](serve/delivery/src/owlbear_delivery/portfolio_application.py#L1709-L1716)
- [integration_verification.py](serve/delivery/src/owlbear_delivery/integration_verification.py#L307-L317)

**Violated clause** — §5 correction matrix: *"Other operator-required attention | Explain exact recovery condition; expose only actions authorized for that code"*; §4: *"Needs | condition requiring intervention"*; §8: *"authority offered without a valid backend path"*.

**Producer→consumer trace** — `IntegrationVerifier.verify()` returns a non-passing receipt → `_integration_attention(CANDIDATE_PROOF_FAILED)` with `retry_condition = "Retry Integration against the current target head."` → `integration_attention_disposition` → `RETRYABLE` → (a) `_integration_card` sets `needs=NONE`, `headline="Integration retry available"`, `action=retry-integration`; (b) `list_integration_ready_changes` re-admits the change to `integration_ready_change_ids` on every acquisition; (c) `authorize_integration_retry` permits the retry.

**Concrete impact** — three distinct failure shapes, all indistinguishable in triage:
1. **Unconfigured target.** If the integration target has no `.owlbear/delivery/verification.json`, `_parse_profile` returns `UNCONFIGURED`, `receipt.passed` is `False`, and every Integration attempt forever fails. Cockpit reports *Needs: Nobody · Integration retry available*. A fresh consumer workspace (`setup/init.py` only emits a `UserWarning`, observed in the test run) can never integrate anything and the portfolio says nothing needs the user.
2. **Profile-changing change.** Any change that edits `verification.json` yields `CHANGED` → permanent `candidate-proof-failed`. There is no state from which such a change can integrate.
3. **Genuine test failure.** `retry_condition` says "Retry Integration against the current target head", which is false — the candidate commit is reproduced from the same tree, so the durable receipt replays or the same suite fails again. Meanwhile orchestration re-attempts the full candidate preparation + verification suite on every acquisition cycle, unbounded.

**Smallest coherent repair** — return `CANDIDATE_PROOF_FAILED` to `OPERATOR_REQUIRED`; keep a narrow retry only when `target_head` moved (which the superseded predicate already handles). Give it a code-specific `retry_condition` naming the failed step, and let `_integration_card` fall to the `needs=YOU` / `_integration_headline(code)` branch so the row reads *Needs: You · Candidate verification failed*.

**Proving test** — production-boundary test in `serve/delivery/tests/test_portfolio_application.py`: seed an Integration-ready change with no `verification.json` on the target, call `integrate_ready_change` twice, and assert (i) `list_integration_ready_changes()` is empty after the first attempt, (ii) `group_view().items[-1].needs is WorkItemNeed.YOU`, (iii) the card headline is not `"Integration retry available"`.

---

### TOPDOWN-2 — One failed background poll destroys the whole portfolio and the open inspector
**Severity: high · Confidence: 97%**

**Location** — [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L363) (`{hasData && !error ? <PortfolioWorkspace …> : null}`); [useWorkItems.ts](serve/cockpit/web/src/hooks/useWorkItems.ts#L46-L63) (`onError: setError`, data retained); [usePollingFetch.ts](serve/cockpit/web/src/hooks/usePollingFetch.ts#L82-L88).

**Violated clause** — §6: *"Errors stay local to the failed surface"*; §5: *"Poll the current portfolio and selected detail … reconcile only responses from the latest snapshot/request generation."*

**Producer→consumer trace** — `usePollingFetch` polls `/api/work-items` every 3 s. Any non-`ok` response or network hiccup calls `onError` without clearing `portfolio`. `WorkPortfolioPage` gates rendering on `hasData && !error`, so `PortfolioWorkspace` — table **and** the routed inspector — unmounts and is replaced by the error banner, then re-mounts on the next successful poll.

**Concrete impact** — a transient 409/500 from any concurrent Delivery mutation (the engine holds acquisition/integration locks; `authorize_integration_retry` legitimately returns 409) blanks the entire supervision surface for up to 3 s and discards all uncommitted inspector input: the block operator note, the evidence locator, the backward-move reason, the open confirm modal, and the request answer text. Under repeated flapping the operator cannot complete any multi-field intervention. Note the detail hook does this correctly — `SelectedDetail` renders data first and ignores the error — so the inconsistency is within one file.

**Smallest coherent repair** — render `PortfolioWorkspace` on `hasData` alone and demote the error banner to a non-blocking inline notice above the table (mirroring `SelectedDetail`'s precedence rule).

**Proving test** — Vitest: render the page, resolve the first `/api/work-items` poll, type a reason into `backward-reason`, make the next poll reject, advance timers, and assert `work-portfolio-table` is still in the document and the input retains its value.

---

### TOPDOWN-3 — Whole-row hit area was specified and never built
**Severity: medium · Confidence: 99%**

**Location** — [WorkPortfolioTable.tsx](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L140-L153) (`<tr>` has no `relative`), [#L61-L82](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L61-L82) (`ItemLink` is `block min-w-0 py-1`, no `after:absolute` overlay), [#L84-L97](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L84-L97) (`ActionLink` retains a vestigial `relative z-[1]` with nothing to sit above). No CSS anywhere in `serve/cockpit/web/src/**/*.css` supplies a row overlay.

**Violated clause** — §6: *"The work-item cell contains a real routed anchor whose hit area spans the row; separate action controls remain independently focusable"*; §8: *"Whole-row navigation updates URL."*

**Producer→consumer trace** — the plan's row contract was reduced to two ordinary inline links; the `z-[1]` on `ActionLink` is direct evidence the overlay was designed and then dropped.

**Concrete impact** — the clickable target is the truncated title text (one line, `truncate`, inside a 24 %-width column). At the 1408 px split threshold that is roughly 180 px of text in a 40 px row; the other ~85 % of the row is inert. This is the density affordance the redesign was justified by, and the E2E only ever clicks `getByRole('link')`, so the gap is invisible to proof.

**Smallest coherent repair** — add `relative` to `<tr>`/`<article>` and `after:absolute after:inset-0 after:content-['']` to the `ItemLink` anchor. `ActionLink`'s existing `relative z-[1]` then works as designed.

**Proving test** — Playwright: `row.click({ position: { x: <stage-column-x>, y: 10 } })` and assert `page` has URL `/delivery/work-e2e/outcome%3AOUT-00N`.

---

### TOPDOWN-4 — Raw enum tokens render as user-facing labels in six places
**Severity: medium · Confidence: 98%**

**Location**
- [WorkPortfolioTable.tsx](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L46) — `` `${activity.worker_role} working` `` → *"assembly-reviewer working"*, *"integration-repairer working"*
- [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L128) — `{request.kind}` → *"decision"*
- [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L183) — `{claim.worker_role}`
- [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L214) — `` `Returned to ${returned.target}` `` → *"Returned to design"*
- [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L253) — backward-move `<PSelectOption>{stage}</PSelectOption>`
- [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L259) — confirm modal *"Move to planning"*
- [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L286) — `{task.status}`

**Violated clause** — §4: *"Never expose raw enum tokens as labels."* This was an explicit terminology decision, not styling.

**Concrete impact** — the destructive backward-move confirmation — the single highest-blast-radius control in the product — asks the operator to confirm *"Move to planning"* against options labelled `design`/`planning`/`implementation`/`assembly`. A `STAGE_LABELS` map already exists in the same file ([WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L41-L47)) and is used for dependencies but not here. The E2E actively locks the defect in by asserting `toContainText('builder working')`.

**Smallest coherent repair** — apply the existing `STAGE_LABELS` at lines 214, 253, 259; add `WORKER_ROLE_LABELS`, `REQUEST_KIND_LABELS`, `TASK_STATUS_LABELS` next to it and use them at 46, 128, 183, 286.

**Proving test** — Vitest assertion that the rendered inspector contains no member of the raw `WorkItemStage`/`DeliveryWorkerRole` unions as standalone visible text.

---

### TOPDOWN-5 — The inspector drops Progress and Activity, stranding the Design-returned Outcome
**Severity: medium · Confidence: 93%**

**Location** — [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L344-L361) — the composed section list contains no progress or activity rendering; `card.progress.label` and `card.activity` are consumed only by [WorkPortfolioTable.tsx](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L150). `ExceptionalStateSection` renders return context as [`Next: {locators}`](serve/cockpit/web/src/components/WorkItemDetail.tsx#L214-L219), and `return_context.source_boundary` / `preserved_commit` are never rendered.

**Violated clause** — §6: *"Ordinary Outcome order: identity; labelled Promise; acceptance; bounded task/result evidence; **Stage/progress/Activity**; then only present exceptional sections"*; §4: *"It renders … progress *Returned to Design — re-admission required*."*

**Producer→consumer trace** — `_outcome_progress` produces `"Returned to Design — re-admission required"` ([work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L461-L466)); it reaches the DTO, reaches the browser, and is rendered only in the table's Progress cell.

**Concrete impact** — a Design-returned Outcome is inert: not claimable, no worker role, no backward move, no typed Action. Its inspector shows Stage *Design*, *Needs you*, promise, acceptance, and *"Returned to design / <reason> / Next: <locators>"* — a "Next:" line that shows evidence locators rather than a next step, and no statement anywhere that re-admission is the exit. The single sentence that tells the operator what to do exists only in a truncated table cell they navigated away from. `source_boundary`, which the plan named as part of this section's source, is dropped entirely.

**Smallest coherent repair** — add a state line under the header rendering `card.progress.label` plus an activity chip when `card.activity.state !== 'idle'`; relabel `AttentionItem`'s third slot to `Evidence:` and render `return_context.source_boundary` when present.

**Proving test** — Vitest: render a detail fixture with `stage: 'design'` and a `return_context`, assert the inspector contains *"re-admission required"* and does not label locators as "Next".

---

### TOPDOWN-6 — `repair_active` is projected and never consumed; the inspector contradicts the row during an active repair
**Severity: medium · Confidence: 95%**

**Location** — produced at [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L621-L631), typed at [workItems.ts](serve/cockpit/web/src/api/workItems.ts#L155), consumed **nowhere** (verified by workspace-wide search: only test fixtures reference it). Same for `superseded` at [workItems.ts](serve/cockpit/web/src/api/workItems.ts#L154).

**Violated clause** — §5 correction matrix: *"Active repair claim | Show repairing Activity; reject administrative movement."*

**Producer→consumer trace** — with a repair claim held, `_integration_card` sets `needs=REPAIR`, `headline="Repair in progress"`, `activity=repairing`, `action=none`. `_integration_view`, however, derives its headline from the attention code, so the inspector for the same item reads **"Merge conflict"** with *"Next: Admit a reviewed Integration repair for this attention, then retry Integration."* and no repair-in-progress statement.

**Concrete impact** — the operator opens the row that says *Repair in progress* and the inspector tells them to start a repair. The most likely reaction — dispatching a second `/integration-repair` — is rejected by `activate_integration_repair_claim`, so the user is pushed toward a guaranteed-failing action by the product's own most detailed surface.

**Smallest coherent repair** — in `IntegrationSection`, when `integration.repair_active` is true, prefix the headline with the repairing state and suppress the `retry_condition` line in favour of "A reviewed repair is currently in progress."

**Proving test** — Vitest: integration detail fixture with `repair_active: true`, assert the inspector states a repair is in progress and does not instruct the user to admit one.

---

### TOPDOWN-7 — `authorize_integration_retry` bypasses every guard when `superseded`, ignoring an active repair claim
**Severity: medium · Confidence: 88%**

**Location** — [target_work.py](serve/cockpit/src/owlbear_cockpit/routes/target_work.py#L164-L182). The `superseded` short-circuit consults `detail.integration.superseded` but not `detail.integration.repair_active`, which is available on the same object.

**Violated clause** — §5: *"Merge conflict, active repair claim | Activity **repairing**; administrative movement rejected"* — the same exclusivity the runtime enforces for `activate_claim` ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L998-L1001)) and `publish_integration_completion` ([#L859](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L859)).

**Producer→consumer trace** — if the integration target moves while a repair worker holds the claim, `integration_attention_superseded` becomes true; `POST /api/changes/{id}/integration/retry` returns 202 and runs `integrate_ready_change` in a background task. `publish_integration_attention` has **no** repair-claim guard ([#L876-L889](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L876-L889)), so the attempt can replace the attention the repair worker is bound to. The worker's subsequent `integration_repair_replacement` then fails with *"Integration repair does not match the current attention"*, discarding reviewed repair work.

**Concrete impact** — an independently reviewed repair is silently invalidated. **Not reachable from the reviewed UI** (`_integration_card` checks `repair_active` first and emits `action=none`), so this is an API-surface hole on a localhost service, which caps severity.

**Smallest coherent repair** — one clause: reject with `ERR_DELIVERY_INTEGRATION_ACTION_REQUIRED` when `detail.integration.repair_active` is true, before the superseded short-circuit.

**Proving test** — extend `tests/test_cockpit_work_items.py`: fake with `integration_superseded=True` **and** `repair_active=True`; assert `POST …/integration/retry` returns 409 and `integrate_ready_change` is never called.

---

### TOPDOWN-8 — `repair-authority` missing from the frontend attention-code union
**Severity: low · Confidence: 99%**

**Location** — [workItems.ts](serve/cockpit/web/src/api/workItems.ts#L15-L24). The backend enum has nine members ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L268-L279)); the TS union has eight.

**Violated clause** — §5, verbatim: *"Add `repair-authority` to the frontend attention-code union and keep backend/frontend dispositions aligned."* This was blocker-level correction M6 and was explicitly re-stated in the accepted plan.

**Concrete impact** — no runtime break today (the code field is never switched on), but the contract silently misdescribes the wire, and any future exhaustive `Record<DeliveryIntegrationAttentionCode, …>` will type-check while omitting the one code whose correction path is backward movement.

**Repair** — add `| 'repair-authority'`. **Proving test** — a type-level fixture asserting `Record<DeliveryIntegrationAttentionCode, string>` covers all nine backend codes.

---

### TOPDOWN-9 — Half of the routing amendment shipped: prefix matching without a not-found fallback
**Severity: low · Confidence: 96%**

**Location** — [CockpitShell.tsx](serve/cockpit/web/src/CockpitShell.tsx#L68-L71) (`?? routeConfig[0]`), [App.tsx](serve/cockpit/web/src/App.tsx#L18-L25) (`{ path: '*' }` unchanged).

**Violated clause** — §6/M8: *"replace the exact-path match with a route-family prefix match **plus an explicit not-found fallback**."*

**Concrete impact** — every unrecognised path (including `/delivery/a/b/c`, where `parseSelection` returns `null`) renders the Delivery portfolio with `aria-current="page"` on Delivery navigation and the original URL retained. A mistyped or truncated deep link looks like a successfully loaded portfolio with no selection, so the operator cannot tell a bad link from an item that completed.

**Repair** — render an explicit not-found view when no route family matches. **Proving test** — Vitest: render `/nonsense`, assert a not-found region and no `work-portfolio-table`.

---

### TOPDOWN-10 — The Integration row's Stage cell reads "Complete" while the attempt has failed
**Severity: low · Confidence: 90%**

**Location** — [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L531) — `stage=WorkItemStage.COMPLETED` is hardcoded for every Integration card regardless of attention.

**Violated clause** — §4: *"The lifecycle is **Complete** after publication"*; §6: *"Needs owns urgency colour; Stage remains neutral."*

**Concrete impact** — a merge-conflicted Integration row renders `Needs: Repair · Integration · Stage: Complete · Attempt failed`. In the one column an operator scans to answer "where is this", the change-level row asserts completion that has not occurred; the true state lives in the adjacent Progress cell. Since the Integration row exists *only* when every Outcome is complete, the Stage cell carries no information it does not duplicate from the group header.

**Repair** — render `—` in the Stage cell for `change-integration` scope, or add a `stage: WorkItemStage | None` and omit it.

**Proving test** — Vitest: portfolio fixture with a merge-conflict Integration card; assert its Stage cell is not "Complete".

---

### TOPDOWN-11 — Canonical vocabulary drift in the portfolio header; `totals.complete` computed and never rendered
**Severity: low · Confidence: 92%**

**Location** — [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L20-L29). `needs.dependency` is labelled **"waiting"** while [WorkPortfolioTable.tsx](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L21-L26) and the Needs filter both label it **"Dependency"**. `totals.complete` — the split the plan required from `attention == none` ([target_work.py](serve/cockpit/src/owlbear_cockpit/routes/target_work.py#L392)) — has no consumer. `PTagDismissible label={\`Change: ${changeFilter}\`}` shows the raw slug id rather than the group title.

**Violated clause** — §4: *"Use one canonical term per concept"*; §5: *"Split active-idle from complete rather than overloading `attention == none`."*

**Concrete impact** — the triage strip's third number cannot be matched to any filter value or column value by name, and the lifecycle count the redesign specifically un-collapsed is invisible.

**Repair** — label it "dependency"; add a `complete` metric or drop the field.

---

### TOPDOWN-12 — The commit bundles an unplanned Integration-verification subsystem that silently changed reviewed behaviour
**Severity: low (governance) / high (as TOPDOWN-1's root enabler) · Confidence: 97%**

**Location** — `416d4b034` adds [integration_verification.py](serve/delivery/src/owlbear_delivery/integration_verification.py) (486 lines, `subprocess.Popen`, worktree materialisation, durable receipts), `.owlbear/delivery/verification.json`, `_verification_steps`/`_write_verification_profile` in [setup/init.py](setup/init.py#L295-L340), a `.gitignore`/`seed/.gitignore` migration, and the `CANDIDATE_PROOF_FAILED` disposition flip.

**Violated clause** — §7 phases 1–6 and the §8 acceptance set contain no verification work; §8 review protocol: *"Commit only owned Delivery/Cockpit paths after complete validation."*

**Concrete impact** — the plan gate (98 % confidence, two deep reviews) certified a different scope than what shipped. The one behaviour change the bundled feature made to reviewed surfaces — the disposition flip — is exactly TOPDOWN-1 and passed both reviews unexamined because it was not in the reviewed artifact.

**Repair** — none to the code; record the verification subsystem as separately-planned work and give it its own gate. Its `.owlbear/delivery/verification.json` correctness for this repo is not a defect (root `npm test` delegates to `serve/cockpit/web` — verified).

---

## D. Explicitly rejected candidate findings

| Candidate | Why rejected |
|---|---|
| Request-owned block is a dead end (`_outcome_action` returns `NONE` when `block.request_id` is set) | `DeliveryBlock.resolved` is `resolution_note is not None` and `resolve_request` sets it ([delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L1121-L1149)). An unresolved request-owned block always has an unresolved request, which the `answer-request` branch catches first. No unreachable state. |
| A read path spawns Git | `_work_item_projector` uses `PortfolioCoordinator.show()` (persisted JSON) and `runtime.frontier_bytes()` (file read). `target_head` is the persisted coordination value, refreshed only during acquisition — the same value orchestration's predicate uses, so the two agree. Verified clean. |
| Design-returned Outcome offers no exit | Correct and plan-sanctioned (B4): production has no runtime path out of DESIGN. `BackwardMoveSection` correctly suppresses itself (`STAGES.indexOf('design') === 0 → available = []`). |
| Backward move offered during an active repair | The UI does not disable it, but `_administrative_move_closure` guards **both** `preview` and `move`, so the very first click fails closed with a typed message before any mutation. Correct fail-closed behaviour, not a dead end. |
| Duplicate `data-work-item` between `DesktopTable` and `CompactRows` | One branch is always `display: none` via `hidden`/`md:hidden`, so it is out of the accessibility tree; E2E filters on `:visible`. |
| `aria-labelledby="work-board-heading"` dangles | The id is supplied by `WorkspaceViewHeader headingId="work-board-heading"` ([WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L346)). Resolves. |
| MCP `WorkItemDetail` lost `briefing` | Explicitly sanctioned by plan gate B4 ("delete `briefing` from the plan's detail model"); it was always `None` in production. |
| `snapshot_version` not required on answer/clear/recover | §5 requires it only for "stale-sensitive preview/mutation pairs"; only backward movement has a preview, and it is correctly version-bound. |
| References accordion rendered before Block/Requests | Both are collapsed; the accepted plan constrains only that references and administrative actions "remain collapsed", not their relative order. Style. |
| `except OSError, json.JSONDecodeError:` at [setup/init.py](setup/init.py#L316) | Tool display artifact — `ast.parse` on the real bytes returns PARSE OK and the module imports in the passing test run. Not a defect. |
| Totals partitions could disagree with row count | Verified: `total = len(items)`; Needs and Activity are each computed from the same `items` list over exhaustive enums. Sound. |
| `ActionLink` navigates instead of acting | Deliberate and coherent — the plan places all mutating controls in the inspector; the row action is a labelled deep link into the section that owns it. |

---

## E. Residual proof gaps (not implementation defects)

1. **Escape dismissal is untested.** [work-portfolio.spec.ts](serve/cockpit/web/e2e/work-portfolio.spec.ts#L20-L30) closes via the *Dismiss flyout* button. §8 explicitly requires *"Escape closes and unmounts the flyout; another row is immediately clickable."* Sol flagged this in the plan review and it remains unproven. Conditional rendering makes the unmount structurally correct, but PDS's `onDismiss`-on-Escape contract is asserted nowhere.
2. **"No read path spawns Git" has no assertion.** §8 names it as a durable observation; no test patches `resolve_git_executable`/`subprocess` around `list_work_item_groups`/`show_work_item_view`.
3. **Cockpit HTTP tests still run against a fake application.** `tests/test_cockpit_work_items.py` hand-builds `ChangeGroupView`/`WorkItemDetailView`, so the DTO↔projection contract is proven only by `tsc` and Pydantic types — Sol's original acceptance objection is partly unaddressed.
4. **The E2E fixture covers no exceptional Integration state.** No merge-conflict, superseded, repair-active, repair-authority, or proof-failed Integration row; no Design-returned row; no loading, error, or empty portfolio; no long-content overflow. §8 named most of these.
5. **Polling reconciliation and stale-response handling are untested** at both the Vitest and Playwright levels.
6. **No live verification.** The Cockpit at `127.0.0.1:8420` is down, so I cannot confirm whether a running instance serves this build, and the only axe evidence is the fixture-driven E2E run — not the real portfolio.
7. **`repair-authority` end-to-end** (label, disposition, permitted previewed backward move) has no test at any layer, which is how TOPDOWN-8 survived.

---

## F. Layer ratings

| Layer | Rating |
|---|---|
| Intent fidelity | **86** — every root cause is genuinely fixed; misses are late-phase polish and one unplanned bundle |
| User layer | **80** — triage, grouping, and orthogonal axes work; TOPDOWN-1 breaks triage for the one state that most needs it, TOPDOWN-5 strands a reachable state |
| Data / authority | **85** — snapshot ownership, versioning, scope isolation, Git-free reads, and movement guards are all correct and well-ordered; TOPDOWN-1/-7 are the exceptions |
| Design / interaction | **72** — routing, focus restoration, flyout unmount, responsive split, and conditional disclosure are right; the signature row affordance is missing and raw enums leak into a destructive confirmation |
| Implementation correctness | **82** — code matches the plan closely; drift is concentrated in the unplanned verification bundle and the frontend's final 10 % |
| Proof quality | **70** — 320 passing tests with real production-boundary coverage in `serve/delivery`, but the named acceptance set has ~7 unproven items and the HTTP layer is still faked |
| Overall coherence | **78** |

---

## G. Landability verdict

**Land with a required follow-up, do not revert.**

The committed implementation is a substantial, coherent improvement over what it replaced, and every load-bearing architectural decision from the accepted plan is genuinely present in source. Nothing here justifies reopening the design.

Two defects should be repaired before this is treated as the operational surface of record:

- **TOPDOWN-1** must be fixed first. It is a small, surgical change (one disposition, one headline branch, one retry-condition string), and until it lands, an OwlBear workspace whose integration target lacks a committed `verification.json` cannot integrate anything while the portfolio reports that nothing needs the user. That is a worse supervision failure than the one the redesign was commissioned to remove.
- **TOPDOWN-2** is a one-line gating change with a large blast radius on every intervention workflow.

**TOPDOWN-3** through **TOPDOWN-6** should be scheduled as one bounded follow-up: they are the difference between "the plan was implemented" and "the plan was implemented as specified", and TOPDOWN-4's presence inside the backward-move confirmation makes it more than cosmetic. **TOPDOWN-7** through **TOPDOWN-11** are low-cost cleanups. **TOPDOWN-12** is a process correction: the verification subsystem needs its own design gate, because it currently owns the publication authority of every future change without ever having been reviewed as such.