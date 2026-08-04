# Correction Authority Policy

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** Who may correct rejected work, how far may they change it, and when must the user rejoin?
> **Status:** S4 resolution derived from current user input and source-grounded workflow analysis.

## 1. Governing Principle

Correction returns to the earliest stage whose claim the evidence disproves. Each actor may repair
only authority it originally owns. A later actor may reject work to an earlier stage but may not
quietly rewrite that stage's contract.

The reviewer decides whether the submitted artifact is acceptable, repairable in its current scope,
untrustworthy and fit for restart, or based on a false parent claim. The reviewer remains read-only:
it identifies the contradiction and return level but does not perform the correction.

## 2. Four Authority Levels

### Level 1: Implementation attempt

The builder owns code, tests, documentation, generated outputs, and proof required by one task. It
may repair only inside that task's reviewed boundary.

The independent reviewer returns one binding disposition for the current attempt:

- **acceptable:** the exact commit and focused proof satisfy the task;
- **repair:** bounded defects can be corrected inside the same task;
- **restart:** the task remains sound, but the implementation is too far off course to trust as a
  repair base; or
- **return to task planning:** the task itself is incomplete, contradictory, or wrongly bounded.

The builder may answer a finding with source evidence but cannot overrule it or broaden the task. A
restart means the reviewer tells the current builder to stop and return a typed failed-attempt
disposition. The orchestrator preserves that attempt, abandons its isolated workspace, and dispatches
the unchanged task from the same reviewed base to a fresh builder and reviewer.

### Level 2: Task plan

The task planner owns executable tasks inside one reviewed parent outcome: the smallest plan unit
above tasks that has one coherent result and assembled acceptance. The current system approximates
this with a delivery node; the redesign should derive the hierarchy and name rather than treating
“deliverable” as a user-selected structure. The planner may revise task outcomes, boundaries,
ordering, dependencies, source ownership, and focused proof when the parent outcome's architecture
and promised result remain unchanged.

Every revised task plan receives independent review before another builder starts. The task planner
returns upward when correction requires a new interface, changed architecture, different deliverable,
changed completion guarantee, or work outside its parent plan.

### Level 3: Solution plan

The Specification/planning owner owns architecture, interfaces, deliverables, dependencies,
migration, and plan-wide proof. It may revise agent-originated implementation strategy and an agreed
agent recommendation that the user did not adopt as important, provided protected meaning remains
achievable. The revision is recorded, independently challenged, and surfaced in the next semantic
summary.

This owner may consult an ideation, architecture, research, or planning subagent. Consultation does
not transfer authority: the owning stage evaluates and writes the revision. A task planner cannot
silently use a subagent to change its parent plan.

### Level 4: User-important meaning

Resume collaborative Specification/idea refinement when the credible correction changes:

- a dealbreaker or direct user request;
- behavior, constraint, or acceptance meaning the user marked important;
- the value, exclusion, failure consequence, or workflow the change promises; or
- a completion-evidence guarantee whose alternatives expose materially different confidence, cost,
  or risk to the user.

The affected task and true dependents wait. Unrelated work continues. Prior user agreement with an
agent recommendation does not by itself require interruption when the user did not adopt that
consequence as important.

### User re-entry mechanism

The correction creates a durable design re-entry tied to the exact failed claim, authority revision,
affected important commitments, evidence, blocked dependency slice, and work that can continue.

- If one independently answerable consequence is fully understandable and one response settles it,
  the resumed designer uses one Decision Request.
- If resolution requires discovering or revising several dependent outcomes, constraints,
  acceptance meanings, or strategy effects, Cockpit offers **Resume collaborative design** and opens
  the same ideation/design session from that briefing.
- A real user-only operation remains an Action Request. Starting a design conversation must not be
  represented as evidence that the design problem is solved.

The complex re-entry remains pending until the resumed session records revised authority, obtains
the required independent review and user confirmation, and re-admits the affected plan. Clicking
Resume starts resolution; it does not unblock work.

## 3. Continuous Return Pipeline

Idea refinement, Specification, solution planning, task planning, implementation, deliverable
acceptance, and whole-plan audit form one resumable pipeline. Earlier stages are not discarded after
coding begins; they remain typed return destinations.

```text
whole-plan audit ───┐
parent-outcome review ├─> earliest false claim
task review ────────┘          │
                              ├─ implementation attempt
                              ├─ task plan
                              ├─ solution plan
                              └─ user-important meaning
```

A reviewer names the false claim and recommended return level. The lifecycle engine invalidates its
accepted result and genuine dependents. The destination owner rehydrates current parent authority,
performs the correction, and reruns review from that level forward. Unchanged accepted parents are
not rewritten or re-reviewed without an affected claim.

## 4. Worked Pipeline Cases

| Evidence | Owner and correction | User input |
|---|---|---|
| DN-003 public-boundary tests encode persisted receipt order incorrectly | Builder repairs tests; reviewer checks changed commit and proof | No |
| A builder's implementation is pervasive, unrelated, or no longer trustworthy, while the task is sound | Reviewer rejects attempt; engine preserves history; fresh builder restarts task | No |
| Runner cannot execute 283 cases in one process, but bounded partitions prove the identical case set | Task planner revises proof procedure; no cases or strength are removed | No |
| Work was assigned to DN-001 although source shows the missing capability belongs to DN-003 | Task/solution planner changes ownership and invalidates affected dependents | No, while promised behavior is unchanged |
| Runtime and query need one causal accepted-dependency resolver rather than independent logic | Solution plan changes internal architecture and affected tasks; challenger checks interfaces and proof | No, unless the user marked that architecture important |
| `shape` after admission actually grants the wrong authority and must become `plan` | Collaborative Specification revisits phase behavior, then replans affected runtime, MCP, agents, UI, and tests | Yes |
| Receipt reuse across descendant commits changes proof cost and stale-evidence risk | Collaborative Specification compares guarantees and records the user's consequence preference | Yes |
| Accepted tasks work alone but not together | Return to the lowest parent outcome whose composition claim failed; add or revise integration tasks | No, unless credible repair weakens protected meaning |

## 5. Reviewer Disagreement and Repair Loops

Reviewer rejection blocks acceptance of the current artifact. The owner may make one focused
evidence response showing that the challenged claim still holds. The reviewer must then withdraw the
finding or state the exact unresolved contradiction; it cannot restart a broad review as a substitute
for answering.

Repair keeps the same independent reviewer long enough to verify its own finding against the changed
immutable artifact. This preserves issue context while the builder remains ready to repair. A new
reviewer is required after restart, task-plan replacement, or return to an earlier stage because the
review object and assumptions changed materially.

If owner and reviewer remain divided on the same concrete claim, one isolated arbiter judges that
claim and the governing authority, not the whole artifact. The arbiter selects pass, repair, restart,
or the return level. Persistent failure after that disposition routes backward; it does not start an
unlimited sequence of fresh full reviews.

## 6. Isolated Implementation Workspaces

One warm Git branch/worktree per change is the preferred initial implementation mechanism:

- different changes may build concurrently while tasks within one change serialize;
- each task starts from the reviewed change-branch revision required by its dependencies;
- repair remains in the same workspace and preserves the cumulative diff for review;
- restart archives the failed attempt's evidence and abandons its workspace without contaminating
  another change; and
- each task commits directly to the change branch, so reviewed and integrated commits stay identical.

Per-task worktrees are deferred until measured same-change queueing justifies a separate integration
owner, merge-conflict routing, proof re-anchoring, and repeated environment setup. Consumer projects
define their own integration target; OwlBear does not prescribe this repository's `dev` convention.

## 7. Current-System Gap

The current model already contains precise runtime routes for build repair, node-plan revision,
design re-entry, node integration, and whole-change correction. Node acceptance uses those routes.
The builder workflow is less precise: every non-local finding becomes `SpecificationReentry`, even
when a task planner could revise the node plan.

The redesign should make builder, task review, deliverable acceptance, and whole-plan audit emit the
same return-level vocabulary. Finding class describes what went wrong; return level identifies who
may correct it. “Planning omission” alone is not a return destination.

## 8. S4 Resolution

- Actors repair only their owned stage.
- Reviewer dispositions are binding for the submitted artifact; reviewers never edit.
- Builders repair implementation or abandon it, but never change a task plan.
- Task planners revise tasks inside one reviewed parent outcome; the exact hierarchy name remains an
  engineering result, not a user decision.
- Solution-plan owners revise agent-originated architecture autonomously when protected meaning stays
  intact, with independent challenge and visible summary.
- One bounded consequence uses a Decision Request; a multi-question semantic correction resumes the
  same collaborative design session and remains blocked until revised authority is admitted.
- Corrections invalidate the smallest affected dependency closure and repeat review from the changed
  level forward.

## 9. Confidence and Limits

**Confidence:** High in the authority ladder because it directly reflects the user's role boundary
and reuses existing typed corrective routes. High in distinguishing autonomous architecture revision
from protected meaning because S1 already records that provenance rule.

**Limits:** Exact retry counts, arbiter model configuration, worktree lifecycle, and mapping the four
levels onto engine job kinds remain implementation work. S5 must show this return path understandably
without exposing internal finding or lifecycle codes.