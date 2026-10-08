# Decision Origin — Decided, Approved and Autonomous Decisions

> **Owning task:** none (direct user request, 2026-10-08).
> **Date:** 2026-10-08.
> **Planned on:** `dev` `d4ce5ffa8`. Live Delivery pinned to `92073c0ce` (`.owlbear/controller/pin.json`).
> **Status:** Sol plan gate round 1 (2026-10-08): `blocked` on migration scope, which the user decided the
> same day (§1.6); five findings accepted as fix-now and applied, one narrowed to a clarification. Round 2:
> `revision-required`, no blockers; three corrections applied, one by simplification (§5).
> Product code unchanged.
> **Question:** how should agents treat prior decisions by origin, and how is origin recorded so that
> Designer, Planner, Builder, the lead chat and challengers apply the right reversal route?

## 1. Contract

### 1.1 Problem

Commit `7aefe7f00` (2026-10-08) made one rule for every prior decision: present each reversal for the user
to re-decide ([owlbear-system](../../share/instructions/owlbear-system.instructions.md), §1;
[r-challenger-protocol](../../share/skills/r-challenger-protocol/SKILL.md); both `challenge-*_sol`
prompts). Every reversal the user has been asked about so far concerned a decision the user did not make
(for example N04 D14, "lead decision 2026-10-05"). Origin is not recorded in a usable form:

- Contract commitments carry free-text `provenance` (`target_contract.py` `DeliveryCommitment`); package
  text says "user-confirmed" also for items the user only approved as part of a package.
- `intent.md` "Confirmed Decisions" lists do not separate asked questions from package content.
- Programme plans label user and lead decisions by convention only (execution plan §7).
- Planner and Builder contexts receive commitments (`application_models.py` `DeliveryPlanContext`,
  `DeliveryBuildContext`) without origin, so an unattended worker cannot tell what the user decided.

### 1.2 Result

Every agent classifies a decision by origin and follows one route per origin and role. Delivery contracts
record decisions structurally, Planner and Builder see them, revisions show a decision delta, Cockpit shows
the user's decisions, and every nonterminal Change is converted to the new contract format.

### 1.3 Decision types (user decisions 2026-10-08)

| Type | Definition | Examples |
| --- | --- | --- |
| `decided` | The user chose it directly: an `askQuestions` answer, a Cockpit request answer, or the user's own words in a prompt or chat | "A2, no A3", a `passed` confirm-check answer |
| `approved` | Part of a collection the user approved without being asked about it individually: a Design package, a plan, a plan amendment | An architecture choice inside an admitted package |
| `autonomous` | Made by an agent or the lead without user approval, including anything under "decide yourself" | "lead decision 2026-10-05", Planner task constraints |

No stakes classification: models do not judge importance to protect a decision. Instead, a decision an
agent considers important is **asked directly** (and becomes `decided`) rather than placed in a package or
plan where it would only be `approved`.

The routes below apply to **recorded decisions**: `decision` contract blocks, answered requests, and
labelled decisions in plans (§3). Choices inside a Planner task chain or a Builder implementation are not
recorded decisions; the owning worker changes them as today, without report lines or E3.

### 1.4 Reversal routes

The owner of the artifact that records a decision is the only role that changes it; another role routes the
change to that owner. No process-step field is recorded (user decision 2026-10-08).

| Role | `decided` | `approved` | `autonomous` |
| --- | --- | --- | --- |
| Designer (interactive) | Ask with `askQuestions` (Step 6 template); the new decision is `decided` | Change it; listed in the revision decision delta and the report | Change it; record the supersession; one report line |
| Planner (unattended) | Return to Design; the Designer asks the user and records a `decided` decision (for a request answer: one that supersedes that request) | Return to Design | Its own planning decisions: change freely when replanning |
| Builder (unattended) | Return | Return | Within the task: change freely |
| Lead chat (interactive) | `askQuestions` | Change it; record it in the plan (§3 label) and report it | Change it; record it and report it |
| Challenger | Report as a proposed reversal for the user | Ordinary finding; the caller decides and reports it | Ordinary finding |

- **Report:** every reversal of an `approved` or `autonomous` decision gets at least one report line naming
  the decision, its record, what changed and why. More detail is welcome when it steers the change.
- **Second reversal (E3):** superseding an `approved` or `autonomous` decision that itself superseded an
  earlier one requires asking the user; the new decision is then `decided`.
- **Unlabelled records (D3):** classify best-effort from evidence: a "user decision" label, an answered
  question, a request answer or the user's own wording means `decided`; content of an approved package or
  plan means `approved`; a "lead decision" label or no user evidence means `autonomous`. When classifying
  for a change, state the classification in the report.

### 1.5 Contract format (C2)

New authored block kind in `yaml target-contract` fences:

```yaml target-contract
kind: decision
id: DEC-001
origin: decided            # decided | approved | autonomous
basis: askQuestions 2026-10-08 "Return bound and exhaustion route"
statement: Builder hand-backs are bounded at three per task lineage and contract.
supersedes: []             # optional; earlier DEC IDs, or answered non-scoped REQ IDs, this one replaces
```

Commitments replace free-text `provenance` with `decisions: [DEC-…]` (at least one entry).

Compiler rules (`target_contract.py`, schema version 3):

- `DEC-NNN` identities are unique and never reused; `origin` is one of the three values; `basis` and
  `statement` are non-empty.
- `supersedes` references existing decisions; a referenced decision is inactive. Commitments reference
  only active decisions. Superseded decisions stay in the package as history.
- A decision that supersedes a `decided` decision must itself be `decided`.
- E3: a decision that supersedes a decision which already has a non-empty `supersedes` must be `decided`.
- No self-supersession and no supersession cycle.
- A `basis` of the form `request REQ-…` and every `REQ-…` in `supersedes` are validated at admission: the
  request exists on the Change and is resolved; a superseded request is a Decision Request without
  `applies_to`, and the superseding decision is `decided`. Other `basis` values are agent-asserted (the
  operating context trusts agents as fallible, not as forging).

Cross-revision rules (revision activation, against the admitted schema-3 contract; the compiler sees only
the candidate):

- An admitted `DEC` ID keeps its `origin`, `basis`, `statement` and `supersedes`; a change needs a new ID
  that `supersedes` it.
- No admitted decision disappears; superseded decisions stay as history.
- The supersession and E3 rules above are evaluated over the admitted and candidate decisions together.
- A schema-2 admitted contract has no decisions; its conversion revision has nothing to compare. The
  Designer's D3 classification records every evidenced earlier decision and known supersession.
- Draft revisions replace complete package bytes without this comparison; the Designer carries every
  existing `decision` block forward unchanged unless the user decides otherwise, and the comparison at
  activation catches an omission.

Requests:

- Promotion and replanning keep every answered Decision Request, not only acceptance-scoped ones
  (`runtime_models.py` `retained_requests`, used by `runtime_reads.py` promotion and
  `delivery_admission.py` replanning).
- No request supersedes another request. A non-scoped answer is replaced only by a `decided` contract
  decision that supersedes it (§1.4); Plan and Build contexts and Cockpit show that request as superseded.
- Acceptance-scoped answers (waiver, person-only confirmation) are never superseded: a Design revision
  that changes the criterion changes its version, which already ends the answer's applicability.

Readers:

- Admission and revision require schema 3.
- Schema 2 contracts stay readable as history of terminal Changes and for nonterminal Changes until
  phase M converts them (§1.6); no new schema-2 admission or revision is accepted.
- The state-format registry (`state_formats.py` `contract` kind), snapshot decoding (`delivery_state.py`)
  and completed-history readers (`completed_history.py`) accept versions 2 and 3; persisted-owner
  fingerprint fixtures (`test_state_formats.py`) follow.
- Revision invalidation (`delivery_admission.py` `_outcome_projection`) compares commitment class and
  statement plus the `statement` of each referenced active decision, ignoring `origin`, `basis` and IDs.
  Re-linking to equivalent decisions invalidates nothing; a changed decision statement invalidates its
  outcomes and their dependents. Against a schema-2 admitted contract (conversion), only commitment class
  and statement and the outcome are compared, so recording decisions alone invalidates nothing.

Consumers:

- `DeliveryPlanContext` and `DeliveryBuildContext` carry the active decisions referenced by the outcome's
  commitments, read-only.
- Revision returns a deterministic decision delta against the admitted contract: added, superseded and
  removed decisions grouped by origin, with E3 cases flagged. The Designer shows it before approval.
- Cockpit shows a Change's decisions with origin, filterable to `decided`.

### 1.6 User decisions

All `[decided 2026-10-08]` in this chat: three types A2 without A3; important decisions are asked
directly; routes B; at least one report line per reversal; E3; D3 best effort; structured recording C2; no
process-step field; big-bang implementation with phases as review points; conversion as the last step;
conversion covers **nonterminal Changes only** (terminal contracts stay immutable schema-2 history); a
Change that cannot be revised yet keeps running on schema 2 and is converted as soon as the refusal clears;
phase M is complete only when every nonterminal Change is converted, completed or abandoned.

## 2. Phases

Big bang: one branch and one PR. Phases are review and commit points, not separate deliveries.
Process per the [execution plan](delivery-redesign-execution-plan.md) §1 (lane worktree from `origin/dev`,
Sol gates, proof, user merge, `/upgrade-delivery`).

| Phase | Content | Editable paths | Proof |
| --- | --- | --- | --- |
| **R — Rules** | Replace the single rule with §1.3–1.4; challenger classifies reversals by origin; Designer Step 6 asks important decisions directly, writes `decision` blocks and carries existing ones forward in drafts; Step 10 and revision show the decision delta; Planner, Builder and `h-decision-requests`: return routes, and answered requests are superseded only by a `decided` contract decision; programme Markdown label convention (§3) | `share/instructions/owlbear-system.instructions.md`, `share/skills/{r-challenger-protocol,w-design-session,w-idea-refinement,w-frontier-planning,w-packet-building,h-decision-requests}/SKILL.md`, `.github/prompts/challenge-*_sol.prompt.md` | Agent-ecosystem tests |
| **C — Compiler and authority** | Schema 3, `decision` block, commitment `decisions`, diagnostics; cross-revision rules; admission `request` basis check; invalidation projection; answered-request retention and `supersedes_request_id`; format registry, snapshot and history readers | `serve/delivery/src/owlbear_delivery/{target_contract,delivery_admission,runtime_models,runtime_reads,state_formats,delivery_state,completed_history}.py`, other readers that pin the contract `schema_version` | Compiler tests per rule (valid, unknown origin, missing basis, dangling, reused or cyclic ID, `decided` superseded by non-`decided`, E3 chain, request basis absent or unresolved); revision refusals for same-ID mutation (including `supersedes`), dropped decision, unasked second reversal and the three-revision omission sequence, each before publication; paired revisions: 3→3 re-link only invalidates nothing, changed decision statement invalidates the outcome and dependents, metadata-only 2→3 conversion keeps populated bindings; answered Decision Request survives promotion and replanning into a fresh Plan and Build context; a `decided` decision superseding a request marks it superseded in contexts; state-format fingerprint tests |
| **X — Contexts and delta** | Decisions in Plan and Build contexts; decision delta in the revision path and the Designer-facing tool output | `application_models.py`, `portfolio_application.py`, `evidence.py`, Delivery MCP tool output | Assembled MCP test (`assemble_target_server`): revise a schema-3 package and read the delta; Plan and Build contexts list the outcome's active decisions |
| **K — Cockpit** | Work-item projection of decisions, API mirror, decision list with origin and `decided` filter, component test, parity assertion | `serve/delivery/src/owlbear_delivery/work_items.py`, `serve/cockpit/src/owlbear_cockpit/routes/`, `serve/cockpit/web/src/api/workItems.ts`, `workItemPresentation.ts`, `WorkItemDetail.tsx`, `tests/test_cockpit_boundary.py` | Assembled payload test, `npm test`, `npm run build`, parity test |
| **G — Gates** | `uv run test --changed`, scoped ruff and Biome; Sol implementation challenge on the exact head; LC full form on an isolated copy of live state: schema-2 contracts and snapshots load with unchanged bytes and digests; a conversion revision of one quiescent Change succeeds, survives restart and replays; terminal history reads; an unsupported contract version is refused before any write. Pre-existing unavailable diagnostics are recorded as baseline, not as results | — | Recorded on the PR |
| **M — Conversion** (after merge and `/upgrade-delivery`) | Convert every nonterminal Change to schema 3 through the normal revision route: Pause, Designer revision with D3 classification into `decision` blocks, gates, approval, activation | Live Design packages through Delivery tools only | Each Change reloads available with an unchanged frontier apart from the revision; no outcome invalidated by re-linking alone |

Phase M notes:

- Nonterminal Changes on 2026-10-08: `cockpit-abandon-feedback`, `interactive-browser-tools`,
  `macos-managed-browser-authentication`, `memory-revision-binding`, `pr-feedback-replay-safe-resume`,
  `static-website-knowledge-ingestion-v2`. Terminal Changes keep their schema-2 contracts as history.
- Three routes by state:
  - **Draft** (unadmitted package, such as `interactive-browser-tools`): the Designer revises the package
    with `decision` blocks before its first admission.
  - **Admitted and revisable:** Pause, revision, gates, approval, activation.
  - **Custody refused** (for example a retained Builder handoff): the Change keeps running on schema 2
    and is converted as soon as the refusal clears.
- Approval: one `askQuestions` call with one approval question per gate-ready candidate, each showing its
  decision delta and D3 classification. A candidate that changes after that approval is approved again.
- Phase M is complete only when every nonterminal Change is converted, completed or abandoned (§1.6).

## 3. Programme Markdown labels

Plans and research documents that are not compiled label decisions inline: `[decided YYYY-MM-DD]`,
`[approved YYYY-MM-DD]` or `[autonomous: <role> YYYY-MM-DD]`, and a reversal adds
`[supersedes <locator>: <reason>]`. Existing "user decision" and "lead decision" texts map to `decided` and
`autonomous` under D3 without rewriting.

## 4. Verification gaps

| Gap | Reason | Owner | Blocks |
| --- | --- | --- | --- |
| `decided` with a non-request basis is agent-asserted | No machine record of `askQuestions` answers | Accepted limit (operating context) | none |
| Agents follow the routes in §1.4 | Instruction compliance is not testable deterministically | Challenger checks during reviews | none |
| Phase M needs one user approval interaction per batch | Revision requires explicit approval | User | phase M completion |
| Custody-refused Changes convert late | Revision refuses retained handoffs | Owning Change's continuation | phase M completion |

## 5. Plan gate record

Sol round 1 on plan SHA-256 `533e3bd7…` (2026-10-08), recommendation `blocked` (migration scope):

| Finding | Disposition |
| --- | --- |
| F1 Protection lost between revisions (compiler sees only the candidate) | fix-now: cross-revision rules (§1.5) |
| F2 Answered Decision Requests dropped on promotion and replanning (`retained_requests` keeps only acceptance-scoped answers) | fix-now: retention and `supersedes_request_id` (§1.5) |
| F3 Ignoring decision links hides real meaning changes | fix-now: projection includes referenced decision statements (§1.5) |
| F4 Phase M mixed draft, admitted and custody-refused states; scope unclear | fix-now: three routes; scope decided by the user (§1.6, §2) |
| F5 Format registry, snapshots, history readers and LC full form missing | fix-now: phase C and G scope (§2) |
| F6 No report channel for worker reversals | Finding narrowed: worker-internal choices are not recorded decisions (§1.3); proposed channel rejected because workers cannot reverse recorded decisions, only return or raise a request |

Sol round 2 on plan SHA-256 `4fbd2443…` (2026-10-08), recommendation `revision-required`, no blockers:

| Finding | Disposition |
| --- | --- |
| R2-1 Request supersession lacked creation authority, waiting and effectiveness semantics | fix-now by simplification: requests never supersede requests; only a `decided` contract decision supersedes a non-scoped answer; acceptance-scoped answers end through criterion versions (§1.5). The proposed request-lineage semantics are rejected as unnecessary machinery |
| R2-2 Optional `supersedes` could be dropped and reset E3 | fix-now: `supersedes` immutable; Designer carries decisions forward in drafts; D3 records known lineage (§1.5) |
| R2-3 Statement-sensitive projection would invalidate everything on 2→3 conversion | fix-now: conversion compares without decision statements (§1.5) |

## 6. Progress

| Phase | PR | Head | Proof | Challenge | Status |
| --- | --- | --- | --- | --- | --- |
| Plan | — | — | — | Sol round 1 `blocked` → resolved; round 2 `revision-required`, corrections applied | revised |
