# Target Delivery Information Flow — Step 2: Rehydrate One Session

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-02
> **Question:** After one change identity is selected, how should the Designer recover enough exact
> context to continue without receiving the entire design and implementation history at once?

## 1. Status Quo And Evidence

The pre-redesign workflow tells the Designer to read all draft artifacts, call `show_change`
for an admitted change, inspect focused research, preserve confirmed meaning, detect contradictions,
and resume from the earliest unresolved gate. The Designer performs the joins and reading strategy.

A representative historical change contains about 163 KB across legacy `intent.md`, `design.md`, and
`decisions.yaml`; the target model retains only the two authored documents before admitted authority
or runtime evidence. The current canary authority is about
1.2 KB. A single full-session payload therefore scales with the largest change, while raw files make
the Designer repeatedly locate, join, and interpret the same information classes.

## 2. Decision D1 — Ordered Information Ladder

Rehydration drills down from purpose to implementation. It is an ordered reading strategy, not one
mandatory response and not a requirement that every layer use the same tool shape.

1. **Orientation:** identity, broad state, and why the session is open.
2. **Intent:** desired outcome, beneficiary, Product Promise, scope, preserved behavior, and accepted
   exclusions.
3. **Commitments and open choices:** governing statements from user dealbreaker through
   implementation discretion, with provenance, evidence status, unresolved choices, and useful
   changed-because rationale in their owning intent or design section.
4. **Current project reality:** existing owners, interfaces, behavior, and architecture relevant to
   the change, verified against current repository evidence rather than trusted from old prose.
5. **Proposed change design:** changed ownership, architecture, interfaces, migration, risks, and
   proof approach.
6. **Agreed delivery contract:** admitted outcomes, acceptance, dependencies, and planning scopes.
7. **Implementation state:** planned, built, reviewed, assembled, corrected, blocked, or completed,
   with evidence rather than a bare percentage.
8. **Actual artifacts:** commits, files, diffs, tests, receipts, and detailed research when inspection
   is useful.

The Designer may drill deeper or revisit an earlier layer when a contradiction appears. It must not
treat a search result, summary, stale design statement, or implementation artifact as a replacement
for its owning authority.

## 3. Tool Sequence Under Review

The provisional sequence is:

1. `open_design_session(change_id)` for orientation and navigation only.
2. Complete intent and exact design-section reads, including local commitment strength and open choices.
3. Current-project and proposed-change architecture inspection.
4. Exact admitted contract inspection.
5. Evidence-backed implementation progress.
6. Optional artifact and session-scoped search tools.
7. Designer states the recovered position and one next unresolved question or gate.

Each tool will be reviewed separately for call timing, decision served, returned information,
omissions, overdelivery risk, underdelivery risk, and handoff to the next layer.

## 4. Decision D2 — Adaptive Session Opening

Call `show_design_session(change_id)` after selecting an existing session. It always returns identity,
broad state, revision-draft presence, and the ordered available information layers. It does not load
their content.

When a persisted Design re-entry briefing exists, also return that exact briefing in full: failed
claim, affected commitments, evidence, blocked and continuing work, and resume condition. The common
correction path therefore starts with its real problem. Without a briefing, return no generated
problem summary; a manual resume proceeds to intent.

Before authority mutation, both paths continue through the governing ladder. This prevents a focused
re-entry from losing wider meaning. Confidence: 0.94.

## 5. Decision D3 — Complete Intent Layer

Call `show_design_intent(change_id)` after opening a manual resume or reading a Design re-entry brief.
It returns the complete current problem, beneficiary, intended outcome, Product Promise, workflows,
scope, preserved behavior, accepted exclusions, success conditions, assumptions, open facts, and
technically-done-but-wrong outcomes as a lossless organized view of `intent.md`.

It excludes technical architecture, admitted delivery authority, progress, implementation, and
research bodies. The source remains available for exact grep/read. Intent is loaded in one call
because omissions here can erode every lower layer; detailed technical content must remain outside
intent rather than forcing fragmented reads. Confidence: 0.93.

## 6. Decision D4 — Commitment Strength And Choices Stay Local

Do not add commitment or decision projection tools. A material statement lives in `intent.md` or
`design.md` with its provenance-based strength, evidence status when factual, and any unresolved
choice that prevents it becoming current meaning. `show_design_intent` returns all intent-owned
statements; exact design-section reads return design-owned statements.

`show_design_session` reports unresolved-choice counts and exact artifact locators. Resolved choices
update their owning statement directly; retain a concise local why or changed-because note only when
it can prevent a credible future mistake. Git owns exhaustive alternatives and prior wording. This
keeps hard versus soft authority distinct from observed versus assumed evidence without creating a
third semantic store. Confidence: high.

## 7. Decision D5 — One Semantic Owner, Explicit Source Contexts

The exact Current System section in `design.md` solely owns persisted project meaning, evidence
locators, uncertainty, and consequences. Do not add `show_design_project_context`; a structured
projection would duplicate or reinterpret that authority.

Call `inspect_design_sources(change_id)` to enumerate current integration, admitted change,
last-reviewed, failed-candidate, and other transition source contexts. It returns stable context IDs,
commit or workspace fingerprints, readable/executable roots when safe, dirty/writer state,
relationships, missing or stale declared references, and diagnostics. It never summarizes meaning.
Confidence: high.

## 8. Decision D6 — One Source Search, Two Explicit Kinds

Use `search_project_source(source_context_id, query, kind, scope?, content_types?, limit?)` against
one explicit context. `kind="exact"` performs an exhaustive literal or
regex scan and returns total count, bounded matches, and truncation; it may support reference and
absence claims. `kind="conceptual"` returns bounded ranked source locators and cannot prove absence.

Both kinds return context identity and exact source locations, not conclusions. Use
`read_project_source(source_context_id, path, start_line, end_line)` for path-safe exact current or
pinned content with file hash and truncation. Shared search output justifies one search tool;
different evidence semantics require an explicit mode. Confidence: high.

## 9. Decision D7 — Exact Design Outline And Sections

Call `list_change_design_sections(change_id)` for the exact heading tree, size, status, linked
commitment classifications, open choices, and declared section dependencies. Then call
`show_change_design_section(change_id, section_id)` for lossless section content.

Always read Design Goals, System Model, Risks, and Rejected Directions. Also read sections linked to
the re-entry brief, unresolved choice, affected commitment, or changed project-context claim. Before
editing, read the full target section and its dependencies. Broad redesign reads every section;
focused correction need not preload unrelated subsystem detail. Confidence: 0.89; incomplete links
must cause broader reading when live source exposes coupling.

## 10. Decision D8 — Designer-Specific Delivery Contract

Use `show_design_delivery_contract(change_id)` after proposed design. It returns admitted/proposed
contract identity and every outcome's title, promise, acceptance, dependencies, status, commitment
links, planning scope, outcome-owned composition contract, and derived `has_accepted_results`. Draft-only output
is unadmitted; revision output includes bounded semantic differences from admitted authority.

Exclude commitment bodies, choice histories, re-entry, progress, receipts, and completion summaries because
the Designer already read or will read those layers elsewhere. Rename the broad exact-model query to
`show_admitted_authority` and expose it only to callers that need the whole model. Final validation
still consumes complete authority. Confidence: 0.94.

## 11. Decision D9 — Loop-Separated Design Transitions

This supersedes the earlier outcome-aligned Designer delivery-state decision. Specification,
Delivery, and Correction are separate loops joined by typed transitions. The Designer does not
monitor Delivery or join jobs, attempts, reviews, receipts, and progress during routine rehydration.
Outcome-wide operational state belongs to Orchestration and Cockpit.
When Delivery returns protected meaning to Design, the runtime provides one validated Design
transition context containing the failed semantic claim, affected authority, preserved, blocked,
and continuing work, decisive evidence, exact relevant revision locators, and resume condition. A
user-requested revision uses the same context through an entry that marks the change revision-pending
in `design`; acquisition skips it while any current claim closes normally. User/Cockpit may abandon
by restoring the admitted authored snapshot and clearing the mark when the admitted contract digest
is unchanged. Exact source inspection follows a locator only when relevant.

Design remains manually user-started. The Orchestrator operates only after admission as a pure
dispatcher: acquire recoverable ready launch packages, launch their named agents in parallel,
detect invocation failure, and report typed stop conditions. Workers record their own claim-scoped
transitions. The Orchestrator neither receives the Design context nor starts
the Designer; pending collaboration remains visible through session inventory and Cockpit.

The transition must be complete before return; missing affected authority, work impact, evidence,
revision identity, or resume condition is a handoff defect. Confidence: high.

## 12. Decision D10 — Automatic Design Return

The worker alone issues `return(target="design")` with affected commitment and outcome IDs, the
semantic defect, and condition revised authority must satisfy. Runtime combines that instruction with
the claim-scoped candidate, authority digest, graph, results, and workspace state. It closes the claim,
derives work impact, and persists one exact Design context with evidence, locators, and resume condition.

No agent relays the handoff. On later manual entry, `show_design_session` returns the complete pending
context. Designer may broaden affected authority but cannot reconstruct or narrow away runtime facts.
Confidence: high.

## 13. Decision D11 — Selective Revision Carry-Forward
Do not add a separate manual revision lifecycle merely to enter Design. A Delivery-triggered Design
return already blocks its affected semantic slice; a user-requested redesign opens the same current
Specification while runtime state remains authoritative about active work. Revised admission must
refuse active claims and publish one coherent new semantic revision.

Replace current whole-change reset with deterministic selective carry-forward. Preserve an outcome's
accepted task chain and results only when its canonical contract projection is byte-identical in the
new revision. That projection closes over the canonical bodies of every linked commitment, so changed
commitment meaning invalidates linked outcomes and their dependent closure. Replan each invalidated
retained outcome. When a removed outcome has accepted code, revised Specification must either preserve
that behavior explicitly or add an ordinary removal/replacement outcome with acceptance and proof;
validation exposes the prior result bindings and fails closed when neither mapping exists. Prior
commits remain evidence, never semantic authority. Preserve unrelated work.
Runtime computes equivalence and closure; Designer and user do not classify carry-forward. Revised
admission atomically archives the prior revision, publishes the new contract, rebinds
preserved task chains and result evidence to its digest, and creates only the required Planning
frontier. Rebind a block, request, and answer only when owner, source claim, unblock condition, and
required evidence remain equivalent; otherwise supersede them and expose normal Plan or Design
context. Uncertain equivalence invalidates. Active claims still block revised admission.
Step 2 is decided. Step 3 reviews intent discovery inside the Specification loop.