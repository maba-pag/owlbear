## 1. Verdict

**FINDINGS** — 13 material items, including one currently-failing test file and one contradictory operator instruction observable in the live Cockpit right now.

## 2. What I personally inspected

Live Cockpit at `http://127.0.0.1:8420` via a controlled headless Chromium (the VS Code integrated browser silently ignored `setViewportSize`, so I drove Playwright directly through [.owlbear/scratch/review-probe.cjs](.owlbear/scratch/review-probe.cjs)):

| Route | Viewports | My screenshot |
|---|---|---|
| `/delivery` | 1440×1000, 390×844 | `.owlbear/scratch/rv-delivery-wide.png`, `rv-delivery-compact.png` |
| `/delivery/knowledge-source-contract-alignment/integration` (no Retry clicked) | 1440×1000, 390×844 | `.owlbear/scratch/rv-integration-wide.png`, `rv-integration-compact.png` |
| `/delivery/malformed` | 1440×1000, 390×844 | `.owlbear/scratch/rv-notfound-wide.png`, `rv-notfound-compact.png` |
| `/delivery/ghost-change/outcome%3AOUT-999` (extra probe) | 1440×1000, 390×844 | `.owlbear/scratch/rv-ghost-wide.png`, `rv-ghost-compact.png` |

Plus a viewport-native capture at `.owlbear/scratch/review-delivery-1440.png`. I also ran DOM hit-testing (`elementFromPoint` per row), overflow measurement, and truncation detection at both widths.

All five supplied `test-results/**` screenshots and the four `.owlbear/scratch/cockpit-*-live-*.png` captures were inspected. Code reviewed: the full uncommitted diff (1113 lines), plus owning code in [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py), [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py), [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py), [target_work.py](serve/cockpit/src/owlbear_cockpit/routes/target_work.py), [WorkPortfolioTable.tsx](serve/cockpit/web/src/components/WorkPortfolioTable.tsx), [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx), [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx), [useWorkItems.ts](serve/cockpit/web/src/hooks/useWorkItems.ts), [routes.ts](serve/cockpit/web/src/routes.ts), [CockpitShell.tsx](serve/cockpit/web/src/CockpitShell.tsx). Read-only verification: vitest (2 failed / 200 passed), pytest (212 passed), `tsc --noEmit` clean, stylelint/htmlhint clean. No file edited outside `.owlbear/scratch/`, no Delivery mutation, no Retry/answer/backward control invoked.

## 3. Findings

### VISUAL-1 — Superseded Integration emits three mutually contradictory instructions
**Severity: High · Confidence: 97% · Implementation bug**

**Locator:** [serve/delivery/src/owlbear_delivery/work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L646) and [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L648); rendered by [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L355). Evidence: `.owlbear/scratch/rv-integration-wide.png`, `rv-integration-compact.png`.

**Observed:** The live inspector for `knowledge-source-contract-alignment` shows, in one panel, in this order:
1. Heading "Integration target moved" / "The Integration target moved since this attempt; retry against the current target."
2. "**Conflicting files**: `share/agents/knowledge-ingestor.agent.md`, `share/skills/h-knowledge-ops/SKILL.md`"
3. A primary button "**Retry Integration**"
4. "Next: **Admit a reviewed Integration repair** for this attention, then retry Integration."

`_integration_view` overrides `headline` and `explanation` when `superseded`, but passes `conflicted_paths=paths` and `retry_condition=attention.retry_condition` unconditionally — so merge-conflict evidence and merge-conflict guidance survive the supersession override. Note the same file already proves the correct pattern exists: `repair_active` *does* suppress `retry_condition` in the UI layer.

**Impact:** The operator cannot answer "what is safe to do". Two of the four statements say "just retry", two say "you must first get a reviewed repair". `integration_attention_superseded` only compares `target_head` — it asserts nothing about whether the conflict is resolved. The most likely operator behaviour (click the prominent button) produces a second failed Integration attempt and a fresh attention record.

**Repair:** In `_integration_view`, when `superseded` is true, emit `conflicted_paths=()` and `retry_condition="Retry Integration against the current target head; the previous verdict is stale."` Mirror the existing `repair_active` suppression rather than inventing a new mechanism.

**Benefits:** One consistent instruction per state; removes a guaranteed wasted Integration attempt. **Downsides:** The operator loses the (stale) hint of which files previously conflicted. **Repair risk:** Low — one branch in one function; `test_repair_activity_and_conflict_paths_use_retained_evidence` covers the non-superseded path and would not regress.

---

### VISUAL-2 — `CockpitShell.test.tsx` is broken; all shell navigation coverage is gone
**Severity: High · Confidence: 99% · Implementation bug (regression)**

**Locator:** [serve/cockpit/web/src/CockpitShell.test.tsx](serve/cockpit/web/src/CockpitShell.test.tsx#L10-L16) vs. [CockpitShell.tsx](serve/cockpit/web/src/CockpitShell.tsx#L69).

**Observed:** `npm test -- --run` → `Test Files 1 failed | 20 passed`, `Tests 2 failed | 200 passed`. Both failures: `Error: [vitest] No "routeForPath" export is defined on the "./routes" mock.` The mock at line 10 still returns only `routeConfig`; the shell now calls `routeForPath`.

**Impact:** The two tests that failed are exactly *"navigates between the target product areas"* and *"opens labeled product navigation from the compact mobile header"* — i.e. desktop and mobile product navigation, plus `aria-current` correctness, are now entirely unverified. This is the seam the diff changed. The suite is red, so the change is not committable as-is.

**Repair:** Add `routeForPath` to the mock factory, delegating to the mocked `routeConfig` (e.g. return the entry whose `path` matches or prefixes the pathname). Add one assertion that an unmatched path renders `not-found-view`, so the new branch in `CockpitShell` gains coverage the mock currently defeats.

**Benefits:** Restores navigation regression coverage and covers the new Not Found branch. **Downsides:** None. **Repair risk:** Very low, test-only.

---

### VISUAL-3 — The portfolio summary has no bucket for actionable/ready work; live state reads "all zero"
**Severity: Medium-High · Confidence: 90% · Product design**

**Locator:** [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L22-L27). Evidence: `.owlbear/scratch/rv-delivery-wide.png`.

**Observed:** The live header reads `2 work items | 0 need you | 0 dependency | 0 need repair | 0 active | 1 complete`. The second work item — the Integration row, the only row on the page carrying an action affordance ("Retry Integration", Activity "Ready") — is counted in *no* bucket. `active` is `working + repairing`; `ready` is never surfaced.

**Impact:** The summary is the first thing an operator reads and it answers "nothing needs me, nothing is running, 1 of 2 done" while a stalled Integration sits below it. It fails the "what is active / what happens next" test and, more damagingly, it fails silently: the numbers are internally consistent, so nothing signals the omission.

**Repair:** Add a `ready` metric (`totals.activity.ready`) between `active` and `complete`, labelled "ready". `WorkItemPortfolioTotals.activity.ready` is already computed and returned by the API — no backend change needed.

**Benefits:** Every work item lands in exactly one activity bucket; the summary becomes exhaustive and auditable. **Downsides:** Six metrics become seven; at 390px the summary already wraps to two rows and would push toward three. **Repair risk:** Low; verify the 390px wrap in `rv-delivery-compact.png` after the change.

---

### VISUAL-4 — Active repair is projected as a red operator alarm with nothing to act on
**Severity: Medium-High · Confidence: 88% · Product design (category error)**

**Locator:** [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L482-L490); tag rendered at [WorkItemDetail.tsx](serve/cockpit/web/src/components/WorkItemDetail.tsx#L85). Evidence: `test-results/…-8baa3-…/delivery-wide-repair-inspector.png`.

**Observed:** When `integration_repair_claim` is set, the projector emits `needs=REPAIR`. The screenshot shows: header metric "**1 need repair**" in red; row Needs "**Repair**" in red with sub-label "Repair in progress"; Activity "Integration repairer working"; Action "—". The inspector simultaneously shows a `PTag` reading "**Repair required**" beside a heading reading "**Repair in progress**".

**Impact:** Needs is defined as *who must act*. Here an agent is already acting and the operator has no control at all, yet the state is rendered with the same red urgency as a genuinely blocked item. It inflates the "need repair" alarm and directly contradicts the adjacent Activity column. "Repair required" vs "Repair in progress" in the same panel is a plain contradiction.

**Repair:** In the `repair_active` branch set `needs=WorkItemNeed.NONE` and keep `needs_headline="Repair in progress"`; the `REPAIRING` activity state and the `active` metric already carry the signal. Separately, make the `DetailHeader` needs tag read from `needs_headline` when present rather than hard-mapping `repair → "Repair required"`.

**Benefits:** Red is reserved for genuine operator demand; Needs and Activity stop contradicting each other. **Downsides:** An in-flight repair becomes filterable only via Activity, not via the Needs filter. **Repair risk:** Low-medium — `test_repair_activity_and_conflict_paths_use_retained_evidence` and the e2e `1need repair` assertion both need updating, which is desirable since they currently pin the wrong semantics.

---

### VISUAL-5 — "Superseded" is presented as a Progress value
**Severity: Medium · Confidence: 90% · Product design (category error)**

**Locator:** [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L498). Evidence: `rv-delivery-wide.png` (Progress column) and `rv-integration-wide.png` (inspector `Progress — Superseded`).

**Observed:** Every other Progress value describes advancement toward the promise ("2 of 2 tasks reviewed", "Task plan not published", "Tasks reviewed — assembling", "Repair in progress"). "Superseded" describes the *validity of a retained record*, not progress, and is internal Delivery vocabulary.

**Impact:** In the inspector it renders as the bald pair `Progress / Superseded`, which tells an operator nothing about what has or has not happened. It also collides with the row's own Needs sub-label "Integration target moved", which says the same thing in comprehensible words.

**Repair:** Use `progress = "Attempt superseded — not yet retried"` (or reuse `"Not attempted against current target"`).

**Benefits:** Progress stays one category; the inspector's `Progress` row becomes self-explanatory. **Downsides:** Longer string; at 390px it wraps. **Repair risk:** Very low, string-only.

---

### VISUAL-6 — Primary identifier truncates at desktop while a fully empty Action column holds 14%
**Severity: Medium · Confidence: 95% · Product design / layout**

**Locator:** [WorkPortfolioTable.tsx](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L131-L138) (colgroup) and [WorkPortfolioTable.tsx](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L89) (`truncate`). Evidence: `rv-delivery-wide.png`, `rv-integration-wide.png`, `test-results/…-8baa3-…/delivery-wide-table.png`.

**Observed:** My DOM probe at 1440×1000 reports `titleTruncated: true` for "Enforced Knowledge source lifecycle contract" → renders "Enforced Knowledge source lifecycle c…". With the split inspector open it degrades to "Enforced Knowledge …". Meanwhile Progress/Activity/Action are near-empty. In `delivery-wide-table.png`, **all 8 rows** show Action "—" while "Verify dependent rollo…" truncates. `truncate` is single-line with no `title` attribute, so sighted users have no recovery path (screen readers do, via the accessible name).

**Impact:** The one thing an operator scans by — the work item title — is the first thing sacrificed, on a page with roughly half its width unused. The Action column is structurally near-empty because most Delivery actions are agent-owned.

**Repair:** Rebalance the colgroup toward Work item (e.g. 12 / 30 / 13 / 20 / 15 / 10) and replace `truncate` with `line-clamp-2` on the title span. If a further step is wanted, fold Action into the row (the whole row is already a click target) and render the action as an inline affordance beside the title.

**Benefits:** Titles stay readable at both the split and full widths; the layout stops paying full price for a rarely-populated column. **Downsides:** Two-line titles increase row height and reduce rows-per-screen. **Repair risk:** Low; `expectNoHorizontalOverflow` and the `min-w-[48rem]` floor already guard the failure mode.

---

### VISUAL-7 — Compact rows drop all column semantics, and "—" means two different things by position
**Severity: Medium · Confidence: 85% · Product design / accessibility**

**Locator:** [WorkPortfolioTable.tsx](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L176-L200). Evidence: `rv-delivery-compact.png`.

**Observed:** At 390px the `<article>` rows carry no headers, no labels, and no accessible name. My probe returns the flat string `"Nobody | Integration target moved | Integration | Change Integration | — | Superseded | Ready | Retry Integration"`. Concretely, in the Outcome row the right slot of line 1 is "Complete" (Stage) and the right slot of line 2 is "—" (Action); in the Integration row the right slot of line 1 is "—" (Stage) and line 2 ends with "Retry Integration". The same glyph occupies two different semantic slots in adjacent rows.

**Impact:** A mobile operator cannot tell that "Superseded" is Progress and "Ready" is Activity — the desktop table's `<th>` scaffolding is the only thing that assigns meaning, and it is `display:none` here. A screen reader user gets an unlabelled run-on. Note that the e2e axe scan runs only once, at 1440 with the inspector closed ([work-portfolio.spec.ts](serve/cockpit/web/e2e/work-portfolio.spec.ts#L163)), so this width has no automated a11y coverage at all.

**Repair:** Give each compact field a visually-hidden or 2xs inline label (`Progress`, `Activity`, `Stage`), and give the `<article>` an `aria-label` of the item title. Add an axe scan at 390px to the compact e2e test.

**Benefits:** Mobile reaches parity with the desktop table's semantics; the ambiguous "—" becomes disambiguated by its label. **Downsides:** More text in an already dense 390px row. **Repair risk:** Low.

---

### VISUAL-8 — `candidate-proof-failed` instructs a retry the UI does not offer
**Severity: Medium · Confidence: 85% · Implementation bug**

**Locator:** [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L1709-L1711) vs. [delivery_runtime.py](serve/delivery/src/owlbear_delivery/delivery_runtime.py#L281-L291) and the `else` branch at [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L500-L505).

**Observed:** The diff correctly demotes `CANDIDATE_PROOF_FAILED` from `RETRYABLE` to `OPERATOR_REQUIRED`, so the card gets `needs=YOU`, `action=NONE` — no Retry control, and `canIntegrate` is false in `IntegrationSection`. But `_integration_retry_condition` still stamps the attention with *"Correct the Integration profile or failing candidate verification step, **then retry Integration**."*, which the inspector renders as the "Next:" line. `test_candidate_proof_failure_requires_operator_correction` asserts `action.kind == NONE` and is green — the contradiction lives entirely in the guidance string.

**Impact:** The operator is told to retry, is given no way to retry, and no alternative route (MCP tool, slash command) is named. Unlike the merge-conflict path — which correctly surfaces `/integration-repair {change_id}` as a copyable command — this state is a dead end.

**Repair:** Change the string to name the actual next step without promising a control, e.g. *"Correct the Integration profile or failing candidate verification step, then re-run Integration from the orchestrator."* Better: give `OPERATOR_REQUIRED` attentions a `command` the way `RUN_REPAIR_COMMAND` does.

**Benefits:** Guidance matches available authority. **Downsides:** None for the string fix. **Repair risk:** Very low.

---

### VISUAL-9 — Stale-poll banner claims the portfolio is unavailable while showing it
**Severity: Medium · Confidence: 90% · Product design**

**Locator:** [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L359-L366), enabled by the `hasData && !error` → `hasData` change at line 368.

**Observed:** Keeping cached data on a failed background poll is the right call and is now covered by a new vitest case. But the banner text was not updated: a red-bordered `role="alert"` reading "**Work portfolio is unavailable.** …" now renders directly above a fully populated table. There is also no indication of *when* the visible data was last good.

**Impact:** The two halves of the screen contradict each other. Worse, the data below is silently frozen — an operator who does not read the banner acts on stale Needs/Activity values; one who does read it may distrust correct data.

**Repair:** Branch the message on `hasData`: *"Showing the last successful refresh — live updates paused. {error.message}"* when cached data exists, keeping "unavailable" only for the cold-start case. Consider appending a relative timestamp of the last success.

**Benefits:** The banner describes what is actually true and the staleness becomes explicit. **Downsides:** Slightly more state in the hook if a timestamp is added. **Repair risk:** Low.

---

### VISUAL-10 — MCP compatibility projection reports a failed Integration as stage `completed`
**Severity: Medium · Confidence: 80% · Implementation bug**

**Locator:** [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L558) — `stage=card.stage or WorkItemStage.COMPLETED`.

**Observed:** Making `stage` nullable is the correct modelling fix — Integration is Change-scoped and has no Outcome stage, and the Cockpit renders "—". But `_compatibility_projection`, which feeds `PortfolioApplication.list_work_items()` and therefore the Delivery MCP `WorkItemProjection` wire shape, backfills `None` to `COMPLETED`. An Integration item that is merge-conflicted, repairing, or superseded is reported to MCP consumers as stage `completed`.

**Impact:** The category error the Cockpit just removed is preserved on the MCP surface, where agents reason about it. `next_action` still carries the truth, so the record is internally inconsistent rather than merely lossy.

**Repair:** The old shape pre-dated nullability, so preserving `completed` is a deliberate compatibility choice — but it should be recorded as one. Either widen `WorkItemProjection.stage` to `WorkItemStage | None`, or keep the backfill and add a one-line comment stating that the MCP wire shape is frozen and consumers must read `next_action`. Add a durable test asserting the chosen behaviour; none currently exists.

**Benefits:** Removes (or documents) a silent semantic divergence between two projections of the same snapshot. **Downsides:** Widening the type is an MCP wire-shape change and needs consumer review. **Repair risk:** Medium if widened, negligible if documented.

---

### VISUAL-11 — `/delivery/{change}` is a hard Not Found, and Not Found offers no way forward
**Severity: Low-Medium · Confidence: 80% · Product design**

**Locator:** [routes.ts](serve/cockpit/web/src/routes.ts#L40-L46) (`segments.length === 1 || segments.length === 3`); [CockpitShell.tsx](serve/cockpit/web/src/CockpitShell.tsx#L139-L146). Evidence: `rv-notfound-wide.png`, `rv-notfound-compact.png`, `test-results/…-54d01-…/cockpit-not-found.png`.

**Observed:** Explicit Not Found routing is a genuine improvement over the previous silent fallback to `routeConfig[0]`. Three residual issues: (a) deleting one segment from a valid deep link — `/delivery/work-e2e` — yields a hard Not Found rather than the portfolio, and the e2e now pins that as intended; (b) the view contains no link or button back to Delivery (at 390px the only route back is behind the hamburger); (c) `text-center` on the section has no visible effect — heading and body are left-aligned at an identical x in all three screenshots.

**Impact:** Minor but avoidable friction; URL truncation is a common operator habit.

**Repair:** Redirect `/delivery/{changeId}` to `/delivery` via `legacyRouteRedirects` (the mechanism already exists for `/` and `/work`). Add a `PLinkPure` "Go to Delivery portfolio" to the Not Found body. Investigate why `text-center` does not apply, or drop the class.

**Benefits:** No dead ends; a partially-typed URL degrades gracefully. **Downsides:** One fewer explicitly-tested Not Found case; update the e2e to use a genuinely unknown path. **Repair risk:** Low.

---

### VISUAL-12 — Raw backend error text surfaced to the operator
**Severity: Low · Confidence: 75% · Implementation bug**

**Locator:** `EmptyDetail` in [WorkPortfolioPage.tsx](serve/cockpit/web/src/pages/WorkPortfolioPage.tsx#L247-L253).

**Observed:** At `/delivery/ghost-change/outcome%3AOUT-999` the inspector renders: *"This Work Item is unavailable. It may have completed or the link may be invalid. **Delivery runtime is absent: ghost-change**"*. Reproduced at both widths.

**Impact:** Low — the recovery controls ("Retry item", "Back to current delivery") are present and correct, and the framing sentence is good. But the appended internal string mixes implementation vocabulary into an otherwise well-written operator message.

**Repair:** Show `error.message` only for retry-safe transport errors, or move it into a collapsed "Technical evidence" `<details>` matching the pattern already used in `IntegrationSection`.

**Benefits:** Consistent evidence-disclosure pattern across the surface. **Downsides:** One extra click when diagnosing. **Repair risk:** Very low.

---

### VISUAL-13 — "Needs: You" rows offer no way to satisfy the need
**Severity: Low · Confidence: 70% · Product design**

**Locator:** [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L411-L412) (`DESIGN` → `YOU`, "Re-admission required") with [work_items.py](serve/delivery/src/owlbear_delivery/work_items.py#L446-L455) (`_outcome_action` returns no action for that case). Evidence: `test-results/…-8baa3-…/delivery-wide-table.png`, row "Plan release notes".

**Observed:** The row reads Needs "**You** / Re-admission required", Stage "Design", Progress "Returned to Design — re-admission required", Action "—". The inspector adds reason, "Evidence:", and "Source boundary:" — good, and the returned-Design evidence labelling in this diff is a clear improvement over the old `Next: {locators}` mislabel. But nothing tells the operator *how* to re-admit, and the Needs headline and Progress label say the identical sentence twice in one row.

**Impact:** The operator learns they are the blocker but not what to do next; the duplication spends the Progress column on redundant text.

**Repair:** Emit a command-bearing action for returned-Design (mirroring `RUN_REPAIR_COMMAND`, e.g. `/design-session {change_id}`), and shorten the Progress label to "Awaiting re-admission" so it does not restate the Needs headline.

**Benefits:** Closes the loop on the one Needs state the operator genuinely owns. **Downsides:** Requires agreeing the canonical re-admission entry point. **Repair risk:** Low-medium.

## 4. Suspected concerns I rejected after inspection

| Concern | Why rejected |
|---|---|
| Whole-row `after:absolute after:inset-0` overlay swallows Action clicks (positioned pseudo-element paints above non-positioned later cells) | `ActionLink` carries `relative z-[1]` ([WorkPortfolioTable.tsx](serve/cockpit/web/src/components/WorkPortfolioTable.tsx#L100)). My `elementFromPoint` probe confirms the Action cell resolves to `A.relative z-[1] inline-flex…` and the Needs cell to the overlay — exactly the intended split. |
| `position: relative` on `<tr>` unsupported, so the overlay misses | Hit-testing confirms the overlay covers the full row in the live Chromium render. |
| The supplied `test-results/**` screenshots are stale or from a failed run (they show 1 need you, no "Decision required", every Action "—", contradicting the spec's `2need you`) | `delivery-wide-table.png` is captured at [line 167](serve/cockpit/web/e2e/work-portfolio.spec.ts#L167), *after* the test answers the release-mode request and performs the backward move. The counts are correct post-mutation states. mtimes (04:26) are ~10 min old. |
| `delivery-wide-table.png` and `delivery-wide-repair-inspector.png` disagree on "Assemble release" stage (Planning vs Assembly) | Same cause — the backward move to `planning` happens between the two captures. |
| Horizontal overflow at 390px or 1440px | `document.scrollWidth === clientWidth` at both widths on `/delivery` and `/delivery/…/integration`; `expectNoHorizontalOverflow` also guards the table's own scroller. |
| Focus restoration broken when the triggering row is re-rendered or removed | The `lastTriggerIdentity` + `[data-work-item-primary-trigger]` fallback with an `isConnected` check is correct, and `closeInspector` asserts `toBeFocused()` in e2e. |
| Nullable `stage` crashes `BackwardMoveSection` or `DetailHeader` | Both guarded (`available = currentStage ? … : []` with an `available.length === 0` early return; conditional `PTag`). `tsc --noEmit` clean. |
| Raw enum leakage into the UI (`worker_role`, request `kind`, task `status`, backward-move stage options) | All now routed through `WORKER_ROLE_LABELS` / `REQUEST_KIND_LABELS` / `TASK_STATUS_LABELS` / `STAGE_LABELS`, and a vitest case asserts `not.toHaveTextContent('builder working')`. Verified in `delivery-compact-flyout.png` ("Pending", "Implementation"). |
| Duplicate column headers (`toHaveCount(2)`) indicates a hidden duplicate table | Two Change groups render two tables in the assembled fixture; `.first()` is asserted visible. Correct. |
| Active-repair retry custody guard is unenforced | [target_work.py](serve/cockpit/src/owlbear_cockpit/routes/target_work.py#L174-L180) returns `409 ERR_DELIVERY_INTEGRATION_ACTION_REQUIRED` with `retry_safe=False` *before* the supersession allowance, and `test_active_integration_repair_rejects_retry_after_target_moves` pins call ordering. Correct and durably tested. |
| Type, lint, or Python regressions | `tsc --noEmit` exit 0; stylelint exit 0; htmlhint exit 0; 212 pytest passed across `serve/delivery/tests/` and `tests/test_cockpit_work_items.py`. |

## 5. Residual risk and readiness

**Not ready to commit.**

Two items are blocking. **VISUAL-2** leaves the vitest suite red and deletes navigation coverage on the exact seam the diff modified — a green suite is a precondition, not a nicety. **VISUAL-1** is live right now on the only real Change in the workspace: the Integration inspector simultaneously instructs retry and forbids retry, and the prominent control leads to a predictable failed attempt.

**VISUAL-3** and **VISUAL-4** are the substantive product-design gaps: the summary cannot currently answer "what is active / what happens next" (its live reading is all zeros next to a stalled Integration), and `repair_active` raises a red operator alarm for work an agent already owns. Both are cheap to fix and both are pinned by tests asserting the current wrong semantics, so they will calcify if deferred.

The redesign's core is sound and several changes are clear improvements: nullable Integration Stage removes a genuine category error; candidate-proof demotion correctly narrows retry authority; the active-repair retry guard is well-placed and well-tested; cached-poll retention, identity-based focus restoration, canonical label maps, returned-Design evidence labelling, and explicit Not Found routing all move in the right direction. The Needs / Stage / Progress / Activity / Action axis separation is the right model — the defects are in a handful of projector branches that populate it inconsistently, not in the model.

Residual risk after fixing VISUAL-1 through VISUAL-4 is **low**: the remaining findings are cosmetic, mobile-semantic, or confined to the MCP compatibility shim. The largest untested area is the 390px compact layout, which has no axe coverage and the weakest field semantics (**VISUAL-7**); I recommend adding that scan in the same pass.