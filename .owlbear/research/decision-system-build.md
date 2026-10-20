# Decision System Build Design

> **Owning task:** item 14 of [the plan](owlbear-plan.md); owner decisions TD-418, TD-419, TD-424..TD-430
> **Date:** 2026-10-20
> **Question:** How do decisions become their own system for OwlBear and every project Delivery works on?
> **Status:** design answered by the owner on 2026-10-20; not built. Made from the assistant's draft, Sol's blind
> proposal and the owner's intent, then challenged by Sol twice (decision system: REVISE 87%; read-backs and
> changes of mind: REVISE 93%); every correction is folded in below.

## 1. Why

OwlBear's decisions are one hand-edited file (C-01..C-31); a project's decisions live only inside each Change's brief
(`BriefDecision`: question, answer, origin) and its finished-Change record. Nothing carries a project's lasting
decisions from one Change to the next, agents read a long file to find what applies, and read-backs depend on the
owner remembering to ask.

## 2. What a decision is

A choice that constrains future work or materially affects behaviour, cost, safety or reversibility. Implementation
choices stay in pull request texts, except those the owner would notice on a page (TD-418).

Fields: a globally unique id, display aliases (OwlBear's rows keep `TD-n`), title, topic, statement (the in-force
line, at most two lines), rationale and consequences (unknown stays unknown), applicability, scope, origin
(`decided`, `approved`, `autonomous`), actor, source (chat, Change, pull request, question id), the owner's words
with date (decided only), lifecycle state, links (§5), read-back state, revision (content hash).

Origin and lifecycle are separate. Authority stays as today ("Prior decisions by origin"): only the owner re-decides a
`decided` row; approved and autonomous rows may be superseded with a reason; a second reversal goes to the owner.
Proposing and activating are separate operations: anyone proposes, only the artifact's owner activates, and an owner
answer or approval is referenced verifiably. A read-back acknowledgement never changes a row's origin.

## 3. Where it lives (TD-424, TD-425)

- **Authority:** every lasting decision of OwlBear and of every project is one Markdown file with validated front
  matter in `owlbear-data`: `<project folder>/decisions/` (a Change's: `<project folder>/changes/<slug>/decisions/`)
  and, for Global, `decisions/` at the repository root, where Global settings already live. Git history is the audit
  trail.
- **A running Change's drafts** stay in its database until the Change ends; then they go to `owlbear-data` with the
  finished-Change record (TD-148), whether the Change merged, was abandoned or ended unchanged. The Change's folder is
  named after its record file (`<approval second>-<slug>`). Merged or unchanged, its Change decisions are spent and
  its project decisions in force (the brief approval activated them); abandoned, the Change decisions are withdrawn
  and the project decisions drafts the owner may still activate. A decision keeps its identity across brief versions
  by its question; once approved, a changed answer is a successor that replaces it. One decision that cannot be
  written keeps all of the Change's out (the record still publishes) and is reported.
- **OwlBear's repository** keeps a generated, read-only full view (OwlBear's and the applicable Global decisions, with
  provenance, mandatory rules apart from history) so Copilot's cloud agent, Copilot code review and CodeRabbit read
  it (TD-425). It pins the data commit it came from; the lead chat regenerates it by pull request; CI checks equality
  and freshness. Data credentials stay in the generator, never in agent environments. Consumer projects get nothing
  (TD-321).
- **Index:** the machine host indexes validated snapshots into SQLite for search, with their source revision; files
  stay the truth.
- **Writes** carry an expected revision; validation refuses two active successors of one decision; a Git merge or a
  timestamp never decides authority. Receipts distinguish saved, committed, published and active. Missing,
  conflicted or invalid decisions stop the affected work; they never become an empty rule set.

## 4. Scopes (TD-426)

Change, project, Global. A Change decision's applicability ends with its Change unless promoted; its record stays.
Promotion creates a linked successor and never erases the source; lineage carries over, so second-reversal counting
cannot reset. Global rules apply to every project at once; a project departs from one only by an exception the owner
confirms. Scope is set when a decision is first made, and every widening is the owner's.

## 5. Links (TD-429)

A fixed set, with validated targets: `replaces`, `refines` (adds detail without replacing), `exception to`,
`depends on`, `related to`, `promoted from`. A conflict is not a link that may stay: it is a flagged state the owner
resolves, because two active rules that contradict each other give agents no answer.

## 6. Lifecycle and deletion (TD-430)

Draft, in force, then replaced, withdrawn (no longer relevant, no successor) or spent (a one-off that is done).
Accepted wording is never edited: a change of intent is a successor. Nothing is deleted; replaced, withdrawn and spent
decisions are hidden by default from agents and on the page. The only exception: a decision that leaked a secret or
personal data is purged, with the owner's consent.

## 7. Applying decisions

- **Applicability** is typed: repository-relative globs, roles, step kinds; empty means the whole scope. It is
  recomputed when a Change's scope grows; unresolved applicability is shown, never silently excluded.
- **Step context:** each step gets every applicable decision in full, the ones its brief references, and a paged
  index to fetch more. Mandatory decision text has its own budget; if it cannot fit, the step stops or the work
  splits. Unlike memory recall, nothing is scored away or dropped by disuse.
- **Baselines:** a Change pins its decisions at approval. When an applicable decision changes, the runner (publication
  and merge included) stops the Change at its next step boundary and asks; until the amendment design (item 16)
  exists it never rewrites an approved brief.

## 8. Read-backs (TD-427)

- The Decisions page holds every read-back. Ignoring one leaves the rule in force as recorded; required decisions
  keep their own gates and are never "ignorable".
- An item is queued only on real ambiguity, new evidence, a conflict or changed consequences; consent already given
  ("take your recommendation", a chosen reading) is not asked again. At a work or approval checkpoint at most three
  optional topics show; the rest wait on the page. Order: imminent safety or irreversible effects, blocked work,
  consequential uncertainty, deferred improvement.
- Working chats (shaping, OwlBear's development) may read back on the same records when the topic comes up, in the
  owner's question format (C-01).

## 9. A change of mind with built effect (TD-428)

1. The page shows the old rule, the new one and an impact report per project: confirmed, unaffected or unknown, from
   the code, tests and merge history (records alone miss chat-built code and unrecorded decisions). A Global change
   covers every known project; an unavailable project stays unknown.
2. Activating the successor, stopping affected work, and scheduling fixes are three separate steps. A new rule that
   forbids existing behaviour is never silently "from now on": its divergence is stated, and affected work, publication
   and merge pause until compliance is settled; grandfathering needs the owner.
3. Fixes are ordinary backlog entries grouped by what one Change can do, carrying the exact decision revisions as
   evidence and tracking partial coverage; a Change closes only what it verified. No automatic code change, no issue
   per item, and nothing for a wording-only change.

## 10. The owner's view

A Decisions tab in the machine UI: project, Global and All filters; topic, origin, state, read-back; an entry shows
provenance, links, history and affected Changes. Actions: read back, replace (a successor), withdraw, promote, record
an exception. Chat tools record, find and read back against the same records; each write returns a short receipt.
Brief approval foregrounds new, changed and inherited decisions (C-14).

## 11. Migration

A clause-level, many-to-many concordance from today's record: origin, qualifications, dates and quotes kept; partial
replacements preserved; "Replaced" lists never read as whole-row retirement. Only genuinely unclear interpretations go
to the owner. The record file becomes the generated view of §3; the old file stays in Git history.

## 12. Slices and proof

| Slice | Content | Proof |
| --- | --- | --- |
| 1 | File contract, validator, migration preview | Every in-force clause of the record traceable to entries; invalid links and two active successors refused |
| 2 | Brief and Change decisions as entries with identity and provenance; archival at every Change end | Restart-safe, idempotent archival of merged, abandoned and unchanged Changes |
| 3 | Storage in `owlbear-data`, index, receipts | Two checkouts writing concurrently; an unreachable data repository stops affected work instead of running without rules |
| 4 | Step context, baselines, runner gate | A decision from an earlier Change reaches a later Change's worker; a relevant change stops a running Change, an irrelevant one does not |
| 5 | Decisions page, chat tools, read-back queue, impact report, grouped fix entries | Owner replacement, second reversal and promotion through the real entry points; unauthorised writes refused |
| 6 | OwlBear's generated view and its CI check | The view equals the pinned data commit; a stale view fails CI |
