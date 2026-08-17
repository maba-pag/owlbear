Browser tools are not available in this session — I could not open http://127.0.0.1:8420/delivery or take screenshots. Everything below is grounded in the three research reports, the owning source, and your live observations. No files were edited.

---

# OwlBear Cockpit — Work Items Redesign

## 0. Diagnosis before design

The interface is not badly styled. It is **rendering the projector's internal model directly as UI**, and the detail endpoint is **scope-blind**. Four independent user questions have been collapsed into two backend enums plus one free-text string:

| User question | Current carrier | Problem |
|---|---|---|
| Where is this in its life? | `stage` | Rendered as a column axis *and* as a raw pill (`completed`) |
| Who is acting right now? | `attention` (partly) | Conflated with "what's wrong" |
| What is wrong? | `attention` (partly) | `none` means both "healthy, agent idle" and "finished" |
| What can I do? | `next_action: str` | Free text rendered as a line of prose — "View result" reads as a dead button |

Three confirmed defects make this worse than a labelling problem:

1. **Cross-scope contamination is in the backend, not the UI.** [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L738) attaches `integration_attention=_operator_integration_attention(runtime.integration_attention())` to **every outcome context**. That is exactly why the completed outcome "Enforced Knowledge source lifecycle contract" shows the change-level merge conflict.
2. **Change-scope cards cannot be inspected at all.** `show_operator_context` fails with `"change work item is not in Integration"` unless the change is in Integration — so `scope="change"` (design) and `scope="change-assembly"` cards render a "View details" button that returns HTTP 409.
3. **The semantic half of the projection is thrown away.** `WorkItemProjector.show()` produces `acceptance` and `briefing`; `TargetCockpitService.show_item` calls `show_operator_context` instead and discards both. The detail panel is therefore *only* exception controls — which is precisely why it feels like "exceptional controls dominate ordinary inspection."

Two further semantic bugs found while reading:

- `pending_request_work_item_ids` is populated from **unresolved blocks**, not requests ([portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L152-L175)). "Needs you" therefore fires on blocks and mislabels them.
- `dependency_ready` is initialised as `attention != USER` in `_projection`, then conditionally overwritten by `_apply_dependency_state`. The field does not mean what it is named.

Everything below assumes these are fixed first.

---

# Layer 1 — User layer (why to show it)

## 1.1 Primary jobs

| # | Job | Surface | Budget | Success |
|---|---|---|---|---|
| J1 | **Triage** — "Is anything waiting on *me*?" | Portfolio | ~5 s | Zero-or-N answer without scrolling or reading titles |
| J2 | **Supervise** — "Is the machine moving, and where is each change?" | Portfolio | ~30 s | Per-change progress and current activity readable in one pass |
| J3 | **Inspect** — "What is this result / why is this stuck?" | Detail | 1–3 min | Promise + acceptance + evidence, without exception controls in the way |
| J4 | **Intervene** — answer, clear, recover, repair, revert | Detail | rare | Deliberate, guarded, out of the default reading path |

The current UI optimises for none of these. It optimises for J-null: "show every projected field."

## 1.2 Canonical vocabulary

One noun per concept, used identically in UI, API, and tests. Where backend and UI diverge today, **the UI adopts the backend noun** — this is an operational tool for the person who also reads the engine.

| Concept | Canonical UI term | Definition surfaced in-product |
|---|---|---|
| Admitted container | **Change** | One admitted body of work, integrated into the target as a single unit. |
| Promised result | **Outcome** | One user-facing result promised by a change. |
| Any projected row | **Work item** | An outcome, or a change-level item (Design, Assembly, Integration). |
| Change-level row, pre-outcome | **Change design** | The change itself, before outcomes exist. |
| Change-level row, composition | **Change assembly** | Cross-outcome composition owned by the change. |
| Change-level row, publish | **Integration** | Publishing the reviewed change to the integration target. |
| Executable unit | **Task** | One build unit under an outcome's plan. |
| Lifecycle position | **Stage** | design → planning → implementation → assembly → **completed** |
| Orthogonal interrupt | **Needs** | Who must act: *you*, *an agent*, *a dependency*, *repair*, *nobody*. |
| Active execution | **Activity** | An agent currently holding a claim on this item. |

### Terminology decisions

- **"Reviewed" is deleted** as a stage label. The stage is `completed`. Because a completed *outcome* is not a completed *change*, the stage chip reads **"Complete"** and the change group header carries the change lifecycle (`Design / In delivery / Integration / Complete`). The relationship "all outcomes complete → change awaits Integration" is shown structurally by the change group, not by relabelling a stage.
- **"Attention" is deleted** as a user-facing word. It is an engine word that means five unrelated things. Users see **"Needs"** with an explicit subject: *Needs you* / *Agent working* / *Waiting on OUT-002* / *Needs repair* / *—*.
- **`attention: none` is split.** `none` currently covers "healthy and idle" and "finished". The card view model derives `needs: 'none'` with a distinct `lifecycle.is_terminal` flag; the portfolio counter labels them separately (see 2.2).
- **`next_action` free text is deleted from the card contract.** It becomes a typed `action` object. "View result" was never an action — it was a description of the row's own affordance.

## 1.3 Card vs detail vs conditional

**Always on a row (portfolio):**
`needs` chip · scope badge (only when ≠ outcome) · title · stage · progress · activity (when live) · one primary action (only when one exists).

**Never on a row:**
`change_id` as bare text (it belongs to the group header) · `promise` (secondary, detail-owned) · raw diagnostics · commitment/dependency IDs · `next_action` prose · task counts for scopes without tasks.

**Always in detail:**
Identity + scope · title · **promise (labelled)** · **acceptance criteria** · stage stepper · needs · progress with named noun.

**Conditional in detail (render nothing when absent — no empty sections):**
Requests · Block · Active claim · Return context · Recovery attention · Integration attention · Design reentry briefing · Superseded-by · Dependencies.

**Collapsed by default:**
Raw diagnostics · Administrative actions (backward move) · Commitment IDs.

## 1.4 Making change grouping and scope legible

Grouping is the fix for the single most disorienting artefact you reported: the same `change_id` appearing unlabeled on two adjacent cards that mean different things.

- The **change is the grouping unit**, rendered once as a group header: `change_id` (labelled, monospace, de-emphasised) · change title · change lifecycle chip · rollup `3 of 5 outcomes complete`.
- Outcomes are rows inside the group, indented, with `OUT-003` as a labelled identity cell.
- Change-level items (Design / Assembly / Integration) are rows inside the group too, but visually pinned last, carrying an explicit scope badge and a distinct icon. They read as *"this row is about the change itself"*, not about a result.

---

# Layer 2 — Data layer (what to show)

## 2.1 Portfolio view model

Replaces the raw `WorkItemProjection` on the wire. One response, two levels.

```ts
type Needs = 'you' | 'agent' | 'waiting' | 'repair' | 'none'
type Scope = 'outcome' | 'change-design' | 'change-assembly' | 'change-integration'

interface WorkPortfolioResponse {
  groups: ChangeGroupView[]
  totals: PortfolioTotals
}

interface ChangeGroupView {
  change_id: string
  title: string
  change_stage: 'design' | 'active-delivery' | 'integration'   // DeliveryChangeStage
  outcome_total: number
  outcome_completed: number
  items: WorkItemCardView[]
}

interface WorkItemCardView {
  work_item_id: string          // OUT-NNN, or change_id for change-level scopes
  change_id: string
  scope: Scope                  // 4 explicit values, no string
  title: string
  promise: string               // detail-owned; row uses it only as title tooltip

  lifecycle: {
    stage: WorkItemStage        // design|planning|implementation|assembly|completed
    step: number                // 1..5, for the stepper glyph
    is_terminal: boolean        // stage === completed
    is_superseded: boolean      // replacement_ids.length > 0
  }

  activity: {                   // NEW on the card — currently detail-only
    state: 'idle' | 'working' | 'repairing'
    worker_role: DeliveryWorkerRole | null
    started_at: string | null
    task_id: string | null
  }

  needs: {
    kind: Needs
    headline: string            // "Decision required" | "Merge conflict" | ...
    blocking_ids: string[]      // dependency outcome ids when kind === 'waiting'
  }

  progress: {
    kind: 'tasks' | 'outcomes' | 'none'
    done: number
    total: number
    label: string               // "4 of 6 tasks reviewed" | "5 of 5 outcomes complete"
  }

  action: {                     // typed — replaces free-text next_action
    kind: 'none' | 'answer-request' | 'clear-block' | 'recover-claim'
          | 'retry-integration' | 'run-repair-command' | 'resume-design'
    label: string
    command: string | null      // e.g. "/integration-repair CHG-014"
  }
}

interface PortfolioTotals {
  needs_you: number
  agent_working: number
  waiting: number
  needs_repair: number
  in_progress_idle: number   // was folded into `none`
  complete: number           // was folded into `none`
}
```

### Derivation and sourcing

| Field | Source | Status |
|---|---|---|
| `work_item_id`, `change_id`, `title`, `promise`, `scope` | `WorkItemProjection` | reuse |
| `lifecycle.stage`, `.step`, `.is_terminal` | `WorkItemProjection.stage` | reuse |
| `lifecycle.is_superseded` | `replacement_ids` | **available, dropped by UI today** |
| `activity.*` | `OutcomeAuthorityBinding.active_claim`; `frontier.integration_repair_claim` for repair | **available, detail-only — must be projected onto the card** |
| `needs.kind` | `WorkItemAttention` after the two semantic fixes | reuse |
| `needs.headline` | derived from block reason / request kind / integration code | **new derivation** |
| `needs.blocking_ids` | `dependency_ids` filtered to non-completed | available, dropped |
| `progress.*` | `TaskProgress` for task scopes; group rollup for integration | **new derivation** |
| `action.*` | typed replacement for `_next_action()` | **backend change** |
| `PortfolioTotals` split | `_attention_counts` in [target_work.py](serve/cockpit/src/owlbear_cockpit/routes/target_work.py) | **backend change** |
| `ChangeGroupView.change_stage` | `DeliveryRuntime.change_stage()` | **available, never projected** |

## 2.2 Detail view model

```ts
interface WorkItemDetailResponse {
  identity: { change_id: string; work_item_id: string; scope: Scope; title: string }

  semantic: {                       // NEW — currently produced then discarded
    promise: string
    acceptance: string[]            // WorkItemDetail.acceptance
    commitments: Array<{ commitment_id: string; commitment_class: string; statement: string }>
    dependencies: Array<{ outcome_id: string; title: string; stage: WorkItemStage }>
    superseded_by: Array<{ outcome_id: string; title: string }>
  }

  state: {
    stage: WorkItemStage
    needs: Needs
    activity: WorkItemCardView['activity']
    progress: WorkItemCardView['progress']
  }

  // every field below is null/[] when absent; UI renders no section for absent data
  requests: DeliveryRequest[]
  block: DeliveryBlock | null
  return_context: ReturnContextView | null
  recovery_attention: RecoveryAttentionView | null
  design_reentry: DesignReentryView | null          // WorkItemDetail.briefing
  integration: IntegrationAttentionView | null      // ONLY when scope === 'change-integration'

  administrative: {
    backward_targets: WorkItemStage[]               // [] disables the whole section
  }
}
```

### 2.3 Structured Integration diagnostics

This is the largest single quality win and it needs **no new git work** — the parsing already exists in [change_workspace.py](serve/delivery/src/owlbear_delivery/change_workspace.py#L978) as `_integration_conflict_paths`, which parses `git merge-tree --write-tree -z` into conflicted paths. Today, `_merge_tree` instead dumps raw stdout lines into `diagnostics: tuple[str, ...]` ([change_workspace.py](serve/delivery/src/owlbear_delivery/change_workspace.py#L968-L976)) and the UI joins them with `' '` into one wall.

New domain model:

```python
class DeliveryIntegrationConflict(_DeliveryModel):
    """Structured, user-legible evidence for one merge-conflict attention."""

    conflicted_paths: tuple[str, ...] = Field(min_length=1)
    added_by_change: tuple[str, ...] = ()
    added_by_target: tuple[str, ...] = ()
    raw: tuple[str, ...] = Field(min_length=1)  # unchanged merge-tree output
```

Exposed as:

```ts
interface IntegrationAttentionView {
  code: DeliveryIntegrationAttentionCode        // + 'repair-authority', missing from TS today
  disposition: 'ready' | 'retryable' | 'repair-required' | 'operator-required'
  headline: string                              // "Merge conflict"
  explanation: string                           // one sentence, human, code-derived
  conflicted_paths: string[]                    // structured
  retry_condition: string
  action: { kind: 'retry-integration' | 'run-repair-command' | 'none'; label: string; command: string | null }
  raw: string[]                                 // behind <PAccordion>, never in the default path
}
```

The user reads: **Merge conflict — 3 files conflict between this change and `dev`** followed by a path list, then a disclosure `Show raw git evidence (11 lines)`.

### 2.4 Progress where tasks do not apply

`"No tasks yet"` on an Integration row is a category error. Resolution table:

| Scope | Condition | `progress.kind` | Label |
|---|---|---|---|
| `outcome` | plan published | `tasks` | `4 of 6 tasks reviewed` |
| `outcome` | no plan yet | `none` | `Task plan not published` |
| `outcome` | superseded/dropped | `none` | `Replaced by OUT-007` |
| `change-design` | always | `none` | `No outcomes admitted yet` |
| `change-assembly` | plan published | `tasks` | `2 of 3 assembly tasks reviewed` |
| `change-integration` | always | `outcomes` | `5 of 5 outcomes complete` |

### 2.5 Cross-scope leakage fix (mandatory, phase 1)

```python
def show_operator_context(self, change_id: str, outcome_id: str) -> DeliveryOperatorContext:
    runtime = self._runtime(change_id)
    if outcome_id == change_id:
        return self._change_scope_context(runtime)  # integration attention lives ONLY here
    binding = runtime.show_binding(outcome_id)
    return DeliveryOperatorContext(
        ...,
        # integration_attention deliberately absent for outcome scope
    )
```

Plus: `_change_scope_context` must serve `design` and `active-delivery` change stages instead of raising, so change-level rows are inspectable. And `DeliveryOperatorContext` gains an explicit `scope` field so the frontend stops inferring scope from `outcome_id === change_id` — an inference repeated in three components today.

### 2.6 Data ledger

**Reuse as-is:** `stage`, `attention`, `task_count`, `reviewed_task_count`, `title`, `promise`, `scope`, `change_id`, `work_item_id`, all `DeliveryRequest` and `DeliveryBlock` fields.

**Available today, silently dropped by Cockpit:**
`WorkItemDetail.acceptance` · `WorkItemDetail.briefing` · `active_claim` on cards · `dependency_ids` · `commitment_ids` · `replacement_ids` · `block.expected_evidence` · `block.locators` · `return_context.preserved_commit / completed_boundary / source_boundary` (serialised, absent from the TS type) · `WorkItemLinks` (returned by both endpoints, never used — the client rebuilds URLs by hand in [workItems.ts](serve/cockpit/web/src/api/workItems.ts)).

**Backend/domain additions required:**
1. Merge `show_work_item` into the Cockpit detail path (acceptance + briefing).
2. Scope-correct `show_operator_context`; add `scope`; serve change design/assembly scopes.
3. `DeliveryIntegrationConflict` structured diagnostics.
4. Card-level `activity` projection from active claims.
5. `ChangeGroupView` rollup from `DeliveryRuntime.change_stage()`.
6. Typed `action` replacing `next_action: str`.
7. Split `AttentionCounts.none` into `in_progress_idle` + `complete`.
8. Commitment resolution (IDs → statements) for the detail semantic block.
9. **Bug:** populate `pending_request_work_item_ids` from unresolved *requests*, and add a separate `blocked_work_item_ids` for blocks.
10. **Bug:** stop initialising `dependency_ready` from `attention != USER`.
11. **Type gaps:** add `repair-authority` to `DeliveryIntegrationAttentionCode` and `ready` to `DeliveryIntegrationAttentionDisposition` in [workItems.ts](serve/cockpit/web/src/api/workItems.ts).

---

# Layer 3 — Design layer (how to show it)

## 3.1 Portfolio IA — replace the board

**Decision: remove the 5-column stage kanban.** Reasons, each concrete:

1. **The columns lie about affordance.** Cards are never moved by the user; stage is engine-owned. A kanban promises direct manipulation it cannot honour.
2. **It shreds the primary container.** A change with 5 outcomes appears in up to 5 disconnected columns. The change — the thing that integrates atomically — has no visual existence. This is the direct cause of "the same `change_id` on two cards that mean different things."
3. **It fails the primary job.** J1 is *"does anything need me?"* Stage is the wrong axis for that; needs is. Today you must scan five columns to answer a boolean.
4. **It cannot afford density.** Five columns at 1100 px yields ~200 px cards, forcing `line-clamp-2` on the title *and* the promise *and* the action. Truncating three of four fields is how "unlabeled competing text" happens.

**Replacement: a change-grouped work table.**

```
┌ Delivery portfolio ──────────────────────────────────────────────────────────┐
│  3 need you   2 agents working   1 waiting   1 needs repair   6 complete     │  ← filter chips
├──────────────────────────────────────────────────────────────────────────────┤
│  [Needs you ▾]  [All changes ▾]  [All stages ▾]          12 of 18 shown      │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▾ CHG-014  Knowledge Source Contract Alignment      In delivery  4 of 5 done │  ← group header
│   ┌────┬────────────────────────────────────────┬──────────┬─────────┬─────┐ │
│   │NEED│ WORK ITEM                              │ STAGE    │PROGRESS │ ACT │ │
│   ├────┼────────────────────────────────────────┼──────────┼─────────┼─────┤ │
│   │ ●  │ OUT-003 Enforce source lifecycle …     │ ▪▪▪▪▪ Complete │ 6/6 tasks │  │ │
│   │ ◐  │ OUT-004 Migrate ingest coordinator     │ ▪▪▪▫▫ Implementation │ 3/7 tasks │ Builder 12m │ │
│   │ ▲  │ ⧉ Integration                          │ ▪▪▪▪▪ Complete │ 5/5 outcomes │ Repair │ │
│   └────┴────────────────────────────────────────┴──────────┴─────────┴─────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

Group ordering: by highest urgency inside the group (`you` > `repair` > `waiting` > `agent` > `none`), then `change_id`. Row ordering inside a group: outcomes by ID, change-level rows last.

Rationale for a table over cards: the audience is an expert supervising agents. Aligned columns make *comparison* free — "which of my nine outcomes is stalled" is answered by scanning one column, not nine card interiors.

## 3.2 Row anatomy and interaction

| Cell | Width | Content | Rules |
|---|---|---|---|
| **Needs** | 32 px | Icon-only status glyph | `aria-label` carries the full phrase; colour is *never* the sole carrier |
| **Work item** | 1fr (min 0) | `OUT-003` (monospace, `text-contrast-medium`) + title, one line, `truncate` | Whole row is the link target; `title` attribute carries full text |
| **Stage** | 168 px | 5-segment stepper glyph + stage word | Stepper is `aria-hidden`; the word is the accessible value |
| **Progress** | 140 px | `progress.label`, shortened (`3/7 tasks`) | Full label in `sr-only` |
| **Activity / Action** | 180 px | Live activity chip *or* the one primary action button | Mutually exclusive; empty when neither |

**Interaction contract:**

- The **entire row opens detail**. Implemented as a "block link" — a `<PLinkPure>`/anchor in the Work item cell with an `::after` overlay spanning the row. This yields: one tab stop per row, real link semantics (`Enter` activates, middle-click/⌘-click opens a new tab, hover shows the URL), full-row hit area, and no `aria-pressed` button pretending to be navigation.
- Interactive controls in the Activity/Action cell sit **above** the overlay (`relative z-10`) so they remain independently focusable and do not trigger navigation.
- Selection is expressed by **row background + `outline`**, never by the left border. The left border is reserved exclusively for needs severity — this removes the border/attention duplication you flagged.
- Keyboard: `↑/↓` move focus between rows (roving tabindex within the group), `Enter` opens, `Escape` closes the inspector, `Tab` moves to the row's action control.
- **"View details" is deleted.**

## 3.3 Detail anatomy

**Container decision: replace the screen-filling flyout with a routed split-pane inspector.**

- Route becomes `/delivery/:changeId/:workItemId` — linkable, refresh-safe, back-button correct. Today identity lives in `useState` inside `PortfolioWorkspace`, so a reload loses it.
- ≥ 1280 px: persistent right pane, 420–520 px, table reflows beside it. The portfolio stays visible; inspection does not destroy context.
- < 1280 px: `PFlyout position="end"` at 90vw (existing behaviour, kept only where the split does not fit).

**Section order — first screen is inspection, not intervention:**

```
1  IDENTITY        CHG-014 · Outcome OUT-003          [Complete] [—]
                   Enforce source lifecycle contract
2  PROMISE         label "Promise"
                   Ingested sources are revalidated on every fetch…
3  ACCEPTANCE      label "Acceptance criteria" — ordered list, always shown when present
4  STATE           Stage stepper (5 steps, current marked) · 6 of 6 tasks reviewed
                   Agent activity chip when live: "Builder · 12m · TASK-004"
─── conditional, in urgency order, rendered only when present ───────────
5  NEEDS YOU       Requests (decision/action) — inline answer controls
6  BLOCKED         reason · unblock condition · expected evidence · clear controls
7  RETURNED        return_context: target stage, reason, locators
8  RECOVERY        recovery attention + guarded recover control
9  DESIGN REENTRY  briefing evidence + resume condition
10 INTEGRATION     change-integration scope ONLY — structured conflict + action
─── collapsed ───────────────────────────────────────────────────────────
11 REFERENCES      commitments, dependencies, superseded-by      <PAccordion>
12 ADMINISTRATIVE  Move backward                                  <PAccordion>
```

**Header pills fixed.** The two disconnected pills `completed` + `No action needed` become one labelled pair:
`Stage: Complete` (neutral tag) · `Needs: nobody` (neutral) — or `Needs: you` (error tone). Raw enum values never render.

**Requests section: conditional.** Renders only when `requests.length > 0`. The current "No pending requests." placeholder occupies prime real estate for a state that is almost always empty. Delete it.

**Move backward: collapsed, destructive-styled.** It is rare and it invalidates dependents. It becomes a closed `<PAccordion heading="Administrative actions">` at the very bottom; inside, a `variant="secondary"` trigger opening the existing confirm modal. The modal must name the concrete blast radius — `invalidated_outcome_ids` is already returned by the API and is currently only shown *after* the move. Show it before.

**Integration section, redesigned:**

```
⚠  Merge conflict
   The reviewed change conflicts with `dev` in 3 files.

   Conflicting files
     serve/knowledge/src/owlbear_knowledge/ingest.py
     serve/knowledge/src/owlbear_knowledge/source_registry.py
     tests/test_source_fetcher.py

   Next: an independently reviewed repair must resolve every conflicting path.

   Run in Copilot Chat:   /integration-repair CHG-014        [Copy]

   ▸ Show raw git evidence (11 lines)
```

`disposition` drives exactly one affordance: `retryable` → **Retry Integration** button; `repair-required` → copyable command, no button; `operator-required` → no control, only the retry condition; `ready` → **Integrate now**.

## 3.4 Vocabulary, colour, density, states

**Microcopy**

| Situation | Text |
|---|---|
| `needs.kind = you` | **Needs you** — with a headline: `Decision required`, `Action required`, `Design input required` |
| `needs.kind = agent` | **Agent working** — plus role and elapsed: `Builder · 12m` |
| `needs.kind = waiting` | **Waiting on OUT-002** (names the blocker; never bare "dependencies") |
| `needs.kind = repair` | **Needs repair** |
| `needs.kind = none`, not terminal | **Idle** |
| `needs.kind = none`, terminal | **—** (the stage chip already says Complete) |
| Progress, no plan | `Task plan not published` |
| Progress, integration | `5 of 5 outcomes complete` |
| Superseded | `Replaced by OUT-007` |

**Colour** (Porsche tokens; colour is never the only channel)

| Needs | Token | Second channel |
|---|---|---|
| you | `notification-error` | `✱` glyph + "Needs you" text |
| repair | `notification-warning` | `⚠` glyph + "Needs repair" text |
| waiting | `notification-info` | `⏸` glyph + named blocker |
| agent | `contrast-medium` + subtle pulse | `◐` glyph + role name |
| none | `contrast-low` | `—` or `✓` |

Stage is **always neutral** (`contrast-high` text, `contrast-low` stepper track). Stage is not a health signal and must not compete for colour.

**Density:** compact table rows at 40 px, `text-sm` titles, `text-xs` metadata. One optional density toggle is *not* worth building; pick compact and commit.

**Responsive**

| Width | Behaviour |
|---|---|
| ≥ 1600 | Table + persistent 520 px inspector |
| 1280–1599 | Table + persistent 420 px inspector; Progress column drops to `3/7` |
| 1024–1279 | Table full width; inspector as flyout; Stage column shows stepper only, word in tooltip |
| < 1024 | Rows become two-line stacked blocks: line 1 = needs + title; line 2 = stage · progress · action |

**Empty / loading / error**

| State | Treatment |
|---|---|
| No current work | Single centred message: *"No changes are in delivery. Admitted changes appear here."* + link to Completed history. No empty stage columns — five empty-column placeholders was five sentences of noise. |
| Loading portfolio | Skeleton rows (3 groups × 2 rows) preserving layout — no `role="status"` text jump |
| Portfolio error | `<PInlineNotification state="error">` with code + retry, above the table |
| Detail loading | Skeleton inside the pane; the row stays selected |
| Detail error | Inline notification inside the pane with retry; portfolio unaffected |
| Action error | Inline notification pinned directly above the section that failed — not at the top of the pane |

**Accessibility**

- Semantic `<table>` with `<caption class="sr-only">`, `scope="col"` headers, and `<tbody>` per change group preceded by a group header row using `<th scope="rowgroup">`.
- One tab stop per row via the block-link pattern; roving tabindex for `↑/↓`.
- Every glyph has a text equivalent; no icon-only meaning.
- Inspector is `<aside aria-labelledby>` in split mode, `role="dialog"` with focus trap only in flyout mode.
- Live region (`aria-live="polite"`) announces portfolio refresh deltas: *"2 items now need you."*
- Contrast: all needs tones verified ≥ 4.5:1 against `bg-surface`.
- Destructive confirmations keep `role="alertdialog"` (already correct).

## 3.5 Worked examples

**A · Ordinary outcome, agent building**
`◐ | OUT-004 Migrate ingest coordinator | ▪▪▪▫▫ Implementation | 3/7 tasks | Builder · 12m`
No action control. Row opens detail showing promise, acceptance, task progress, active claim. No requests section, no attention section, no backward-move form visible.

**B · Completed outcome, awaiting change Integration**
`— | OUT-003 Enforce source lifecycle contract | ▪▪▪▪▪ Complete | 6/6 tasks | —`
Detail shows promise + acceptance + `6 of 6 tasks reviewed`. **No Integration section** — that belongs to the change row. This is the exact contamination fixed at [portfolio_application.py](serve/delivery/src/owlbear_delivery/portfolio_application.py#L738).

**C · Waiting outcome**
`⏸ | OUT-006 Publish contract docs | ▪▪▫▫▫ Planning | Task plan not published | —`
Needs cell `aria-label`: "Waiting on OUT-004". Detail's References accordion lists dependencies with their live stages.

**D · User-requested outcome**
`✱ | OUT-005 Choose retention policy | ▪▪▪▫▫ Implementation | 2/5 tasks | [Answer]`
Action button focuses the Requests section. Detail opens with **Needs you → Decision required** as section 5, above everything conditional, with the `PSelect` + free-text control already present.

**E · Integration repair required**
`⚠ | ⧉ Integration | ▪▪▪▪▪ Complete | 5 of 5 outcomes complete | Needs repair`
Detail: identity `CHG-014 · Integration`, promise "Publish the reviewed change and completed history to the integration target", state `All outcomes complete`, then the structured conflict block from 3.3. Backward move is absent (not applicable at change scope). Requests section absent.

**F · Change design, no outcomes yet**
`✱ | ⧉ Change design | ▪▫▫▫▫ Design | No outcomes admitted yet | [Resume design]`
Detail is currently **impossible** (HTTP 409). After the fix, it shows the change title, the design reentry briefing when present, and the resume condition. This row is otherwise a dead end.

---

# Implementation sequence

Semantics and boundaries first. Every phase is independently shippable.

### Phase 1 — Data-boundary correctness (no visual change)
1. Remove change-level `integration_attention` from outcome-scope `DeliveryOperatorContext`.
2. Add `scope` to `DeliveryOperatorContext`; serve change-design and change-assembly scopes instead of raising.
3. Fix `pending_request_work_item_ids` (requests, not blocks); add `blocked_work_item_ids`.
4. Fix `dependency_ready` initialisation in `_projection`.
5. TS type gaps: `repair-authority`, `ready`.

*Proof:* existing pytest suites plus new boundary tests. No frontend churn.

### Phase 2 — Semantic completeness
6. Merge `WorkItemDetail` (acceptance, briefing) into the Cockpit detail response.
7. Resolve commitment IDs → statements; project dependencies with titles/stages.
8. `DeliveryIntegrationConflict` structured diagnostics reusing `_integration_conflict_paths`.
9. Split `AttentionCounts.none`.

### Phase 3 — View-model contract
10. Introduce `WorkItemCardView` with `lifecycle` / `activity` / `needs` / `progress` / `action`; delete `next_action: str`.
11. Introduce `ChangeGroupView` rollups.
12. Project `active_claim` onto cards.

### Phase 4 — Portfolio replacement
13. Change-grouped table replacing `WorkPortfolioBoard`.
14. Block-link row interaction, roving `↑/↓`, needs-owns-colour.
15. Totals become filter chips.

### Phase 5 — Detail replacement
16. Routed `/delivery/:changeId/:workItemId` split-pane inspector.
17. Section reorder; conditional rendering; accordions for references and administrative actions.
18. Structured Integration presentation with raw-evidence disclosure.

### Phase 6 — Polish
19. Responsive tiers, skeletons, live-region announcements, density pass.
20. Axe sweep + contrast verification.

---

# Acceptance observations

**Vitest**

| # | Scenario |
|---|---|
| V1 | Outcome detail for a change with active `merge-conflict` integration attention renders **no** Integration section |
| V2 | Change-integration detail renders the Integration section with `conflicted_paths` as a list, and raw evidence collapsed |
| V3 | Change-design row opens a detail pane (no error state) |
| V4 | Integration row progress reads `5 of 5 outcomes complete`; the string `No tasks yet` appears nowhere in the DOM |
| V5 | Outcome without a published plan reads `Task plan not published` |
| V6 | Every row exposes exactly one tab stop when no action control is present |
| V7 | Waiting row's needs `aria-label` names the specific blocking outcome ID |
| V8 | Detail with `requests: []` renders no `Requests` heading |
| V9 | Detail renders `Acceptance criteria` with every item from `semantic.acceptance` |
| V10 | Header pills render `Stage: Complete` / `Needs: nobody`; raw `completed` never appears |
| V11 | `repair-required` shows a copyable command and no Retry button; `retryable` shows Retry and no command |
| V12 | Administrative accordion is closed on mount; backward-move controls are not in the initial accessible tree |
| V13 | Backward-move confirm modal names `invalidated_outcome_ids` before submission |
| V14 | Rows group under their change; a change with 3 outcomes renders one group header and 3 rows |
| V15 | Totals chips sum to the rendered row count, with `complete` and `in_progress_idle` distinct |

**Playwright**

| # | Scenario |
|---|---|
| E1 | 1440 px: clicking anywhere on a row opens the inspector; URL becomes `/delivery/CHG-014/OUT-003` |
| E2 | Reload at that URL restores the same inspector and selected row |
| E3 | `↓` then `Enter` from the first row opens the second row's detail |
| E4 | ⌘-click on a row opens a new tab at the item URL |
| E5 | 1100 px: no horizontal scroll; no row overlap; inspector renders as flyout |
| E6 | 1280 px: inspector is a persistent pane and the table remains visible |
| E7 | Opening the completed outcome then the Integration row shows two different bodies; the conflict appears only in the second |
| E8 | Expanding raw git evidence reveals `merge-tree` lines; they are absent before expansion |
| E9 | Answering a request removes the `Needs you` state from the row without a full reload |
| E10 | Axe scan at 1440 px and 1100 px reports no serious/critical violations |
| E11 | Empty portfolio shows one message, not five empty-column placeholders |
| E12 | Scroll sweep at 640 px height: no row is occluded by the sticky header |

---

# Rejected patterns

| Pattern | Why rejected |
|---|---|
| **5-column stage kanban** | Promises drag-and-drop that engine-owned stages forbid; fragments a change across 5 columns; starves cards to ~200 px, forcing three simultaneous truncations |
| **Bare `change_id` as first card line** | Unlabeled identity competing with the title. Identity belongs to the group header, once |
| **`next_action` as free-text prose on the card** | "View result" reads as a dead command. Actions must be typed and rendered as affordances, or not rendered |
| **Unlabeled promise under the title** | Two unlabeled paragraphs of similar weight; the reader cannot tell which is the name |
| **`"2/2 reviewed"`** | No noun. `2 of 2 tasks reviewed` |
| **`"No tasks yet"` on change/Integration scopes** | Category error — tasks are not a concept at those scopes |
| **Tiny "View details" link as the only open target** | The row *is* the object. A 90-px link inside a 224-px-tall card inverts Fitts's law and adds a redundant tab stop |
| **Left border doing double duty (selection + status)** | Selection and severity fight for the same channel; neither reads reliably |
| **Raw `stage` enum in a pill (`completed`)** | Exposes an implementation token as user vocabulary |
| **`completed` column labelled "Reviewed"** | Invents a fourth vocabulary for a state already named three other ways |
| **Always-rendered Requests section with "No pending requests."** | Spends prime vertical space on the overwhelmingly common empty case |
| **Always-visible Move backward form** | A rare, dependency-invalidating operation given permanent prominence over ordinary inspection |
| **`integration.diagnostics.join(' ')`** | Collapses structured multi-line git output into one unreadable string; discards structure that the domain already computes |
| **Screen-filling flyout for routine inspection** | Destroys portfolio context for the most common interaction |
| **Detail identity in component `useState`** | Not linkable, not refresh-safe, back button does nothing |
| **`attention: none` as a single counter** | Conflates "healthy and idle" with "finished" — the two states with opposite implications for supervision |

---

# Risks and open decisions

| # | Item | Status |
|---|---|---|
| R1 | **Table vs board is a genuine reversal.** E2E tests and the `data-stage-heading` / `data-stage-empty` probes assume columns. Phase 4 must rewrite [work-portfolio.spec.ts](serve/cockpit/web/e2e/work-portfolio.spec.ts). Mitigated by keeping phases 1–3 board-compatible. | Decision made; cost acknowledged |
| R2 | **`git merge-tree` output stability.** Structured extraction depends on the `-z` record format already parsed by `_integration_conflict_paths`. Retaining `raw` guarantees no evidence is lost if parsing degrades. | Mitigated |
| R3 | **Commitment resolution cost.** Resolving IDs → statements on every detail fetch touches `TargetAuthority`. Volume is small (single change) but this is the only new read amplification. | Low risk |
| R4 | **`repair-authority` has no UI copy.** It is absent from `INTEGRATION_ATTENTION_LABELS` and from the TS union. Needs a label; I do not have enough evidence to write accurate operator guidance for it. | **Open — needs your input** |
| R5 | **`change-assembly` and `change-integration` share `work_item_id == change_id`** and the integration card overwrites the assembly card in the same dict key. Grouped rows make this collision visible; if both can ever be live simultaneously, the ID scheme needs a scope suffix. | **Open — needs domain confirmation** |
| R6 | **Split-pane threshold (1280 px).** Chosen so a 420 px inspector leaves ≥ 860 px of table. Worth verifying against your actual window size. | Low risk, easily tuned |
| R7 | **Polling/refresh.** The portfolio only refetches on mount and after mutations. A supervision tool arguably needs periodic refresh, but that is out of scope for this redesign. | Deferred, flagged |

---

# Confidence by layer

| Layer | Confidence | Basis and limits |
|---|---|---|
| **Diagnosis** | **High** | The three defects and two semantic bugs are read directly from source, not inferred |
| **User layer** | **High** | Jobs and vocabulary derive from the domain model plus your stated confusions; the one judgement call is preferring backend nouns over invented UI nouns |
| **Data layer** | **High** for reuse/leakage/progress; **Medium** for `ChangeGroupView` and typed `action` | I did not trace every `DeliveryRuntime` accessor needed to build the change rollup cheaply |
| **Design layer — portfolio** | **Medium-High** | The board→table argument is strongly supported by the truncation and grouping evidence, but I could not view the live UI or measure real rendered widths |
| **Design layer — detail** | **High** | Section ordering, conditional rendering, and structured diagnostics follow directly from the observed failures |
| **Responsive/visual specifics** | **Medium** | Breakpoints and column widths are reasoned, not measured. Browser tools were unavailable; these need verification against the running app |
| **Test scenarios** | **High** | Modelled on the existing Vitest and Playwright suites |

The weakest link is that I could not observe the live rendering. If you can re-run this with browser tools enabled, the items I would verify first are the actual card widths at 1100 px, the flyout's real occupied width, and whether the Integration row and the completed-outcome row are visually distinguishable at a glance today.