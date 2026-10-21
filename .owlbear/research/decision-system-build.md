# Decision System Build Design

> **Owning task:** item 14 of [the plan](owlbear-plan.md); owner decisions TD-418, TD-419, TD-424..TD-430
> **Date:** 2026-10-20
> **Question:** How do decisions become their own system for OwlBear and every project Delivery works on?
> **Status:** design answered by the owner on 2026-10-20; built except the migration (#538 to #547, #550); revised
> on 2026-10-21 by [decisions as confirmed intent](decision-intent-build.md) (TD-448..TD-455). Made
> from the assistant's draft, Sol's blind
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
  written keeps all of the Change's out (the record still publishes) and is reported; so does one the validator would
  find at fault together with the decisions already in the repository (two in-force successors, say), and a write
  that fails midway puts every file of the set back as it was.
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
- **Built in slice 3** (choices made while building): a save fetches and, when its checkout is behind and clean,
  rebases first, so the expected revision is checked against the remote's file; a push the remote rejects because it
  changed the same decision file takes this save's commit back and reports it not saved, and Git never rebases over a
  decision file both sides changed. When a published save's reloaded snapshot shows two in-force successors of one
  decision, the saving checkout flags every successor of it `conflict` (its own and the other checkout's) and
  publishes the flags, reloading up to three rounds until none is left unflagged, so the second writer's receipt says
  `conflict` and the first checkout sees it after its next refresh. A flagged decision is never active until the owner
  clears the flag. A save does not refuse a successor it knows competes; it records the conflict for the owner.
  A snapshot validates every project's folder and keeps Global's and its own project's decisions and every finding
  involving one of them, so a `promoted_from` link to another project's decision is not a finding but another
  project's decision replacing a Global one (`replace-scope`) keeps that Global decision out of force everywhere. A
  project folder that is missing, a folder of the root, Global or the project itself that cannot be read, or a file
  in the project's view that is not a usable decision stops loading. Another project's folder that cannot be read
  stops no one: it is an `unreadable` finding of that project's layer, outside the view, which stays complete. The
  residual risk: a conflict over a Global rule that only that unreadable folder holds (its decision replacing or
  competing with the Global one) stays unseen, and the Global rule counts as active, until the folder can be read.
  The index rebuilds a project's rows when the data commit or the digest of its decision
  files' revisions changes, so uncommitted files count; creating or replacing its file is serialized by a lock file.
- **Built in slice 6** (choices made while building): the view is `.owlbear/decisions.md`, written by
  `uv run decisions-view <owlbear-data> --project owlbear`. Its header says the record stays authoritative until the
  owner has reviewed the migration (TD-437); rules in force come Global first, then OwlBear's (its Changes' included),
  grouped by topic, each with its rationale and consequences on one line apiece, so `--check` compares them too; drafts are counted, not listed; replaced, withdrawn and spent ones are one line each in History,
  and the validator's findings are listed. Its last line is the sha256 of everything above it. Freshness means the
  rendered decisions differ: `--check` compares the view without its data commit line and hash, so new owlbear-data
  commits that leave the decisions alone never fail it, and the pinned commit names the data the view was last
  generated from. A data repository without any `decisions/` folder is an empty set; until the migration the view
  says "Data commit: none (no decisions migrated yet)", which `--commit none` allows only without decisions or
  findings. Pull-request CI checks the hash alone, through a stdlib config hook Static runs (TD-409); only
  `decisions-view.yml`, on pushes to main and daily, holds the read-only data token and runs `--check`. It never
  writes: on a failure the lead chat regenerates the view by pull request. It is not part of the required `CI` check.

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
Accepted wording is never edited: a change of intent is a successor. A `replaces` link never narrows a layer: an
approved project decision that a later approved brief version narrows to its Change is archived withdrawn, and its
Change successor relates to it (`related_to`). Nothing is deleted; replaced, withdrawn and spent
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
- **Built in slice 4** (choices made while building): a decision applies when it is in force, its scope reaches the
  Change (a Change decision only its own, by record stem) and its role, step and path selectors match; a glob and a
  scope entry overlap when either covers a path under the other, and a decision with paths stays unresolved, listed
  and marked, while the Change has no scope paths. The approval pins every decision in force in the project's view by
  revision, with the wording of those that apply, and the data commit; approved while the decisions cannot be read,
  the first readable gated step asks the owner to pin the set in force then (never a silent pin), while a Change
  approved before this gate is pinned on its first gated step. The gate runs once per step in the runner before
  any step but shaping (it waits for chat) and cleanup (an ending Change always cleans up), before a due test-copy
  preparation and before the host launches a check environment. It first catches the checkout up with its remote
  (`decision_store.refresh`: under the data repository's lock, rebasing only a clean checkout), so another
  checkout's replacement or conflict reaches an idle one; when it cannot (offline, uncommitted files, a refused
  rebase), steps go on with the local decisions, but publication and merge, which cannot be undone, stop with the
  reason. Then: an unreadable store stops with its `state` stop; an
  applying decision
  flagged `conflict` or in any finding stops naming it; a new, changed or no-longer-in-force decision that applies
  now or applied at the pin asks "Continue with the current decisions" (re-pins the set the question showed) or
  "Pause" (asks again after resume); a decision that applies to neither never stops the Change, and one that only
  starts applying because the scope grew is listed without a question. A project without a data repository runs as
  before until a Change holds a baseline, which then stops: Changes from before the gate had no rules to compare
  with. The section is held for the step's whole run, so the worker's, a challenger's and a judge's inputs carry the
  same text; above 12,000 characters of decision entries the step stops and asks for a split, never a cut. A
  statement the archive cut keeps its whole wording in the rationale, and the entry carries it whole.

## 8. Read-backs (TD-427)

- The Decisions page holds every read-back. Ignoring one leaves the rule in force as recorded; required decisions
  keep their own gates and are never "ignorable".
- An item is queued only on real ambiguity, new evidence, a conflict or changed consequences; consent already given
  ("take your recommendation", a chosen reading) is not asked again. At a work or approval checkpoint at most three
  optional topics show; the rest wait on the page. Order: imminent safety or irreversible effects, blocked work,
  consequential uncertainty, deferred improvement.
- Working chats (shaping, OwlBear's development) may read back on the same records when the topic comes up, in the
  owner's question format (C-01).
- **Built in slice 5b part 1** (choices made while building): a decision carries `read_back_why` and
  `read_back_kind` (`safety`, `blocked`, `uncertain`, `improvement`) only while its read-back is `pending`, left out
  of its content when empty so older files keep their revision. A decision flagged `conflict` is in the queue as
  `blocked` without anything written. The queue orders by kind, then by the decision's creation, oldest first. A chat
  queues one with `queue_read_back` (why and kind; the page names the revision it read); it never changes origin,
  wording or state and is refused without a reason, for a decision already waiting for the same reason and kind, and
  for one read back today on the reason it waited for (the host keeps that reason). "Still right" records the
  read-back's date and clears the reason; "ignore for now" writes nothing to the decision: the host's database keeps
  the ignored revision, which sorts the item last until the decision changes. The brief approval view (while the
  brief awaits approval) and the decisions gate's question list at most three waiting read-backs that apply to the
  Change in queue order and count the rest; the question's identity and Continue ignore them.

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
- **Built in slice 5b part 2** (choices made while building): the entry of a decision that replaced another, or was
  withdrawn, shows "Impact": the old rule, the new one, a divergence line and, per project, `confirmed` (a merged
  finished-Change record whose brief made the old decision or whose `decisions_applied`, now written into each
  record from its baseline, holds it; or a Change in the project's store whose baseline applied it), `unaffected`
  (path selectors that match no file tracked at `origin/HEAD`, else `HEAD`, and no such Change) or `unknown` with
  why: a rule without path selectors, matching files, or a project whose repository this host cannot read. A
  Change whose baseline only pinned the old decision without applying it does not count: every Change pins every
  rule in force. A Global rule covers every project the host serves and OwlBear's folder; the machine host's
  `GET /api/next/decisions/{id}/impact?folder=` covers every project it serves, a project host only its own.
  Matching files are listed up to 50, with the test files among them, and the rest counted. Replacing and
  activating take an optional `effect` (`forbids` or `wording`), written as "Effect on existing work: …" into the
  successor's rationale (an inherited mark is dropped); without one the change counts as possibly forbidding. The
  pause is the §7 gate's, unchanged. "Schedule fixes" is the owner's click on a rule in force, refused for a
  wording-only change, a withdrawal, a stale revision or when no project is due: one backlog entry per confirmed
  or unknown project, split by top-level folder above 20 files into at most five, titled "Apply decision <id>:
  <title>", with both revisions in the text and the evidence and a checklist of its Changes and files; scheduling
  again counts the same entries up. "Accept existing code" (grandfathering) is a `decided` project decision with
  the owner's reason that `refines` the new rule (`exception_to` a Global one), its source marking it; that project
  then is no longer due. Built: a Change's cleanup ticks, in the fix entries that went into it, the file items its
  merged pull request changed (`git diff` of the merge commit against its first parent; a folder item when a changed
  file lies under it, never a Change item), names itself and the PR in the text, and makes each entry done when
  nothing is left, else open again; an abandoned or unchanged Change ticks nothing and reopens them, and a failure
  only logs a notice.

## 10. The owner's view

A Decisions tab in the machine UI: project, Global and All filters; topic, origin, state, read-back; an entry shows
provenance, links, history and affected Changes. Actions: read back, replace (a successor), withdraw, promote, record
an exception. Chat tools record, find and read back against the same records; each write returns a short receipt.
Brief approval foregrounds new, changed and inherited decisions (C-14).

- **Built in slice 5a** (choices made while building): the page's writes are the owner's: the host's token admits
  them and a call marked as a chat's (`X-OwlBear-Use: chat`) is refused for activate, replace, withdraw, promote,
  exception and conflict resolution; a chat proposes and reads back only. Every write names the revision the page or
  chat read, and a changed one is refused by its receipt before anything is written. Replacing or withdrawing a
  `decided` decision, or activating a draft that replaces one, needs the owner's ticked re-decision; the owner's
  successor is `decided` in his words (the new rule when he gives none). Reversals are counted back through
  `replaces` and `promoted_from`, so a promotion never resets them; a second reversal is refused unless the
  successor is `decided` in the owner's words or he confirms re-deciding it on activation. `record_decision` always
  saves a project draft, `decided` when the owner's words are given, else `autonomous`; it never replaces a `decided`
  or Global decision, and activating an `autonomous` draft makes it `approved`. Promotion saves a linked successor
  one layer wider with the source's origin and words and marks the source `replaced` in the same commit: the
  validator counts a non-draft `promoted_from` that widens (Global from a project or Change decision, a project from
  its own Change's; any other is a `promote-scope` finding) as the source's successor, in the two-successors rule
  and conflict flagging too, so a replaced Global rule never stays in force through the
  project's copy, and the source stays readable in history. An exception is a `decided` project decision
  `exception_to` a Global one, which stays in force. Resolving a conflict keeps the chosen successor, withdraws its
  competing successors and clears the flag. A read-back sets today's date and keeps origin and wording. A
  transition's files (a successor and what it retires, a kept decision and its withdrawn rivals) are checked against
  their expected revisions together and written, committed and published as one commit, or none is; a stale take-back
  undoes every file of it. Replace, withdraw, promote, keep and activating or proposing a draft that replaces one need
  a reason, recorded in the successor's rationale ("Why it changed: …") or the withdrawn one's; a replacement keeps
  the predecessor's `exception_to`, `refines`, `depends_on` and `related_to` links.
- **Built in slice 5b part 1** (choices made while building): the read-back queue is the tab's first section (§8),
  each item with "Still right", "Replace or withdraw" (the entry's own actions) and "Ignore for now"; the owner queues
  one from an entry too. An "OwlBear" filter (`where=owlbear`) beside This project, Global and All reads
  owlbear-data's `owlbear/` folder with Global (TD-435), and every entry action takes the same `where`, so the owner
  acts on OwlBear's decisions from any project's host without OwlBear's repository being registered.

## 11. Migration

A clause-level, many-to-many concordance from today's record: origin, qualifications, dates and quotes kept; partial
replacements preserved; "Replaced" lists never read as whole-row retirement. Only genuinely unclear interpretations go
to the owner. The record file becomes the generated view of §3; the old file stays in Git history.

- **The owner's review of the preview** (2026-10-21, TD-439..TD-446): the record migrates as written, with the lines
  his answers changed in their topics; Global holds C-01's asking rules and the four agent-conduct rules TD-442 names;
  the migrator proposes per topic the roles and step kinds its rules apply to and the owner confirms one list
  (TD-446). Neither is built yet.
- **Before the switch:** chats in OwlBear's own workspace have no decision tools (§10 reaches OwlBear's decisions
  from the tab only). On 2026-10-21 the owner had decision management rethought; [decisions as confirmed
  intent](decision-intent-build.md) replaces this section's migration (TD-454, TD-455).

## 12. Slices and proof

| Slice | Content | Proof |
| --- | --- | --- |
| 1 | File contract, validator, migration preview | Every in-force clause of the record traceable to entries; invalid links and two active successors refused |
| 2 | Brief and Change decisions as entries with identity and provenance; archival at every Change end | Restart-safe, idempotent archival of merged, abandoned and unchanged Changes |
| 3 | Storage in `owlbear-data`, index, receipts | Two checkouts writing concurrently; an unreachable data repository stops affected work instead of running without rules |
| 4 | Step context, baselines, runner gate | A decision from an earlier Change reaches a later Change's worker; a relevant change stops a running Change, an irrelevant one does not |
| 5 | Decisions page, chat tools, read-back queue, impact report, grouped fix entries | Owner replacement, second reversal and promotion through the real entry points; unauthorised writes refused |
| 6 | OwlBear's generated view and its CI check | The view equals the pinned data commit; a stale view fails CI |
