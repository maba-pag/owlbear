# Target Delivery Information Flow — Step 1: Select Or Create Session

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-02
> **Question:** How should the Designer identify or create exactly one useful design session without
> loading full authority, missing conceptual matches, or persisting an empty shell?

## 1. Status Quo And Evidence

- `/ideate <idea>` and `/design [change_id]` enter one `w-design-session` in discovery or direct mode.
- The Designer has explicit file search/read tools, terminal access, and `Explore`; tool exposure is
  role-scoped, so another role need not receive Design discovery tools.
- The legacy workflow expects a separate `.owlbear/design/` draft store and calls `list_changes` for
   admitted changes; the target instead uses Step 14's change-owned package from session creation.
- This workspace currently has no target package-backed draft loader, scaffold, or creation test.
- `list_changes` returns every complete admitted `TargetAuthority`, without pagination. It is named
  as inventory but returns authority depth, so payload grows with portfolio and change complexity.
- Semble supports a scoped path, content classes, result count, and snippet-line limit. A probe over
  `.owlbear/research/` returned several chunks from one file, showing that raw semantic chunks need
  session-level aggregation before they are useful for identity selection.
- `WorkItemProjector` already derives exact design, planning, implementation, assembly, and completed
  stages from admitted authority and runtime evidence.

## 2. Approved Call Flow

```text
exact change_id ───────────────────────────────────────────────┐
empty /design → list_design_sessions ── choose ───────────────┤
rough /ideate → search_design_sessions ─ choose/no match ─────┤
                                                               ├─ existing → Step 2 rehydrate
no match → clarify + focused evidence → seed-readiness gate ───┤
                                                               └─ create_design_session → Step 3 discovery
```

Ambiguous results produce one identity-selection question. Search ranks candidates but never selects
one. Discovery output is not authority. Exact IDs bypass portfolio discovery. A newly created session
does not need immediate rehydration because the current Designer supplied the persisted seed; resumed
or existing sessions always enter Step 2.

## 3. Decision D1 — Separate Browse And Search

Use two tools because browse and relevance retrieval have different intent, ranking, empty-result,
and evidence semantics.

- `list_design_sessions`: paginated Designer inventory when `/design` has no identity.
- `search_design_sessions`: bounded relevance retrieval for rough or descriptive input.

Do not combine them into one parameter-heavy operation. Expose them only to session-selecting roles.

## 4. Decision D2 — Automatic Observable Hybrid Search

The caller states search intent; it does not choose lexical versus semantic retrieval. Run both,
give exact ID/title matches deterministic precedence, fuse ranks, and deduplicate by session.

Return at most five sessions. Each result includes identity, lifecycle state, retrieval channels,
source locator, and at most two short source snippets. Return rank evidence rather than an
uncalibrated confidence score. Report degraded channels explicitly and never silently fall back.
Exclude runtime, receipts, prior revisions, scratch, and legacy; search only the current semantic
artifacts in each active package plus the bounded semantic fields in Step 14's completed-history
index. This Designer-only identity search is the exception to active-only default search. Never
return synthesized conclusions or complete authority.

Benefits: lexical precision plus semantic recall, one intent-level call, and lower duplicate-session
risk. Costs: semantic indexing, latency, and less deterministic ranking. Controls: strict corpus and
response bounds, exact-match precedence, visible degradation, and session-level aggregation.
Confidence: 0.84; ranking quality and latency require implementation proof.

## 5. Decision D3 — Designer-Specific Browse Projection

`list_design_sessions` is custom-designed for a Designer deciding what to inspect, not reused as a
generic change card. Each item returns:

- `change_id` and `title` for recognition and the Step 2 call;
- lifecycle `status`: design, active-delivery, integration, completed, or unavailable;
- distinct unfinished `active_stages` so mixed-outcome changes are not flattened inaccurately;
- completed active outcomes over total active outcomes;
- `has_revision_draft`;
- at most three exact outcome titles plus `remaining_outcome_count`.

Exclude attention, next-action advice, commitments, acceptance, requests, activity, snippets, full
authority, and generated summaries. A later role may receive a different list tool over the same
change store. Confidence: 0.91; strict outcome-title bounds control wide-change payloads.

## 6. Decision D4 — Seeded Atomic Creation

Do not create an empty draft immediately. After search finds no plausible match, clarify and inspect
only enough to establish a useful seed, then call `create_design_session(seed)`.

Required seed:

- stable `change_id` and working title;
- rough idea/source statement and concrete intended outcome;
- apparent beneficiary or explicit unknown;
- prompt or reason for the change;
- observed facts and assumptions known so far;
- expected breadth: localized, cross-cutting, systemic, or unknown, with basis;
- highest-value unresolved question.

Breadth and uncertainty replace an early effort/time estimate: they calibrate design depth without
anchoring delivery before repository grounding. The tool stages the initial files, then atomically
publishes the untracked package directory as the sole session visibility point. Identical retry
returns that package; divergent authored bytes fail closed. The dedicated package-history ref begins
only with the first semantic checkpoint. The product branch is created later and never carries
mutable package state. The tool cannot invent outcomes, commitments, resolved choices, acceptance,
proof, or architecture. It returns identity, relative locators, and created/existing disposition.

Default one change to one independently integratable product increment. Split systemic ideas into
multiple changes when they can deliver and revise independently; keep one systemic change when
splitting would create false boundaries or require incomplete intermediate states. This is a Design
judgment, not an admission limit or runtime state.

Benefits: useful resumability, typed omission checks, replay-safe package creation, path safety, and replay.
Costs: a maintained public seed schema and a short pre-persistence window. Confidence: 0.88.

## 7. Required Implementation Changes

1. Add a transport-free Design-session owner over the change-owned package root, with lifecycle-aware
   projections over current Specification and admitted authority rather than separate stores.
2. Add paginated `list_design_sessions` with the D3 projection and filters appropriate to Designer
   browsing.
3. Add bounded `search_design_sessions` with exact-match precedence, hybrid rank fusion, session
   aggregation, source locators, channel diagnostics, and corpus exclusions.
4. Add replay-safe `create_design_session` with the D4 seed schema, identity validation, staged
   two-file creation, and atomic package-directory publication.
5. Slim `list_changes` to paginated admitted-change summaries; keep `show_change` as exact admitted
   authority retrieval unless Step 2 chooses a replacement.
6. Update Designer grants, `/ideate`, `/design`, and `w-design-session` only after runtime contracts
   exist; preserve file search/read and scoped semantic code search for later evidence work.
7. Prove exact-ID bypass, list pagination and payload bounds, mixed stages, revision drafts, hybrid
   aggregation/degradation, corpus exclusion, ambiguity, no-match creation, publication interruption,
   replay, divergent-package refusal, exact two-file creation, and no generated semantic content.

## 8. Limits And Next Boundary

Step 1 ends with one existing or usefully seeded `change_id`. It does not establish complete intent,
interpret all session authority, choose the next design gate, or traverse references. Step 2 must
decide the exact detail/read interface for rehydration before Step 1 implementation is finalized.