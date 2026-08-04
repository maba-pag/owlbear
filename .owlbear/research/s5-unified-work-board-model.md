# S5 Unified Work Board Model

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** How can Cockpit show the complete path from ideation through completion while dispatching only agent-executable work?
> **Status:** Approved with the existing Cockpit dashboard as the implementation's visual baseline.
## 1. User Need
Design re-entry must become visible work, not an error message or hidden request. When evidence shows
that user collaboration is needed, the board should make the item unmistakable and offer a manual
way to resume the relevant ideation/design session. The same surface should show what happens before
and after that collaboration.

The user should not need to switch between a Specification document viewer, a Delivery job board,
and raw Requests merely to understand where one outcome stands.
## 2. Current Structural Conflict
The current Kanban card is exactly one purpose-specific agent job. Its column is its immutable job
kind: `plan`, `build`, `accept`, or `audit`. That correctly prevents a design conversation from being
claimed by the orchestrator, but it also prevents Design from appearing on the board.

Adding `design` as another job kind would create the wrong behavior:

- the engine could treat user collaboration as dispatchable agent work;
- one conversation could be mistaken for an independently completable job;
- clicking Resume could be mistaken for resolving the underlying design problem; and
- a card would still expose execution mechanics instead of one continuous outcome.

## 3. Separate Work Items From Jobs

Cockpit should project two related objects:

### Visible work item

A stable, user-facing unit representing either the whole change or one coherent reviewed parent
outcome from first clarification through completed result. Its scope and parent are explicit. It owns
understandable current state, affected commitments, dependencies, and the next action. It persists
while implementation attempts and plans are superseded.

### Execution job

One engine-selected agent transformation under a work item. Planning, building, and required assembly
checks may create dispatchable jobs. Reviews remain nested assurance actions. Jobs,
attempts, claims, findings, receipts, commits, and proof are technical trace, not the board's primary
card identity.

This preserves immutable execution history while allowing work from many changes to advance or return
between stages on one portfolio board.

## 4. User-Facing Stages

| Stage | Meaning | Starts how | Completes when |
|---|---|---|---|
| **Design** | Intent or a correction needs collaborative understanding | User selects **Resume design** | Reviewed meaning and solution direction are ready |
| **Planning** | Agents turn the reviewed outcome into executable tasks | Engine dispatches planner work | Tasks and proof approach pass independent challenge |
| **Implementation** | Builders create and review the required result | Engine dispatches task attempts | Every required task has a reviewed implementation |
| **Assembly** | Multiple reviewed pieces must prove one broader parent promise | Engine dispatches only when composition creates a new claim | The assembled outcome or change passes at the exact commit |

Assembly is the only active stage after Implementation. It does not repeat task review: it checks
interactions, omissions, and parent-level behavior that no single task could prove. A one-task outcome
whose inline challenge covered the full promise skips Assembly. A multi-outcome change uses the same
stage at Change scope for its cross-outcome check; it also skips the check when no broader claim exists.

Passing the last required check closes the item and moves it mechanically to completed/archive storage.
Archive is not an agent stage. Cockpit exposes completed work through history or a filter rather than
an active-board column. Later evidence reopens the minimum affected item from its proper active stage.

Stage describes where the outcome is. Dispatchability is a separate property. Design is visible but
manual; Planning, Implementation, and Assembly are normally dispatchable when ready; any stage may
be waiting on a scoped user request, dependency, reviewer disposition, or safe execution condition.

## 5. Initial Ideation and Later Re-entry

The global board shows every unfinished change. Before decomposition, one `Change` card occupies
Design. Once reviewed outcomes exist, their cards identify the parent change; a change-level card
reappears in Assembly only for a distinct cross-outcome claim. Selecting a change opens a persistent
summary and outcome-only detail board. Grouping, change filters, and attention filters keep the
portfolio scannable without limiting how many changes may exist or progress.

Later evidence can return one affected work item to Design without moving unrelated items backward.
The item shows:

- which promised or important meaning is affected;
- what evidence made the current direction unreliable;
- what work is waiting and what continues;
- whether one bounded decision or a collaborative design session is needed; and
- the next user action.

**Resume design** opens the same persisted design session with that briefing. It does not resolve the
item. The Design stage completes only after revised authority is confirmed, independently reviewed,
and admitted.

## 6. At-a-Glance Card

The board card should lead with:

- outcome title in user language;
- current stage and whether action is needed;
- one-sentence promised result or affected commitment;
- reason for waiting or return;
- progress through reviewed tasks where meaningful; and
- one primary action: Resume design, Review decision, Inspect progress, or View result.

One predicate controls every attention signal: a card either needs the user now or it does not. The
same predicate drives badge, change-level count, ordering, and notification. Agent review in progress
uses a separate treatment and never resembles a user request.

Do not show node ID, job ID, digest, claim, receipt, finding code, or agent name on the card by
default. Those belong in technical trace.

## 7. One Drill-Down Away

Inspecting a work item reveals:

- reviewed intent and commitment provenance;
- current architecture or plan consequence summary;
- acceptance meaning in observable terms;
- correction history and reviewer disposition;
- blocked and continuing dependencies;
- task list with current execution state; and
- links to technical evidence.

This is where the user can understand why work returned to Design or how an autonomous correction
preserved protected meaning.

## 8. Technical Trace

The deepest view preserves exact jobs, attempts, reviewer evidence, commits, changed paths, commands,
receipts, invalidation closure, authority digests, and full history. It supports audit and diagnosis
without becoming the normal oversight interface.

Priority and per-job Cancel are not target requirements. Removing an outcome is an intent change:
reopen its parent change in Design, rethink the outcome and dependency structure, and let the revised
plan supersede obsolete work while preserving history.
There is no direct outcome Cancel, Delete, or Withdraw control.

Orchestration is an on-demand VS Code Copilot chat loop, not a background daemon. Stopping that chat
stops further dispatch, so the board needs no Pause or Stop control. Re-entering Design is a separate
semantic action and does not secretly control an orchestration session.

When a prior session is known dead after a VS Code crash or GitHub failure, orchestration may **Recover
interrupted task** before expiry. It records interruption, clears the claim, preserves partial work and
trace, and replans fresh work. Expiry remains the fallback; the board has no **Release claim** control.

Each change uses one warm writable worktree and permits one writer at a time; different changes may
build concurrently. Tasks commit directly onto the change branch in dependency order, preserving the
rule that the reviewed commit is the integrated commit. The project's own integration target is
configured or discovered, never assumed to be OwlBear's `dev`. Per-task worktrees remain deferred
until measured same-change queueing justifies their merge, proof, and environment costs.

## 9. Consequences

**Benefits:**

- The complete ideation-to-completion path is visible in one place.
- Manual collaboration and autonomous execution are distinct without splitting the user's mental
  model across products.
- A design re-entry becomes actionable work rather than a terminal error.
- Board language can express consequences while preserving exact technical evidence below it.
- Removing priority eliminates a control that implies sequencing authority while independent work can
  run concurrently and dependent work already has hard ordering.

**Costs and risks:**

- The runtime needs a durable work-item projection above immutable jobs.
- Stage transitions and return paths must be derived from authority and evidence, not manually dragged.
- A portfolio board must remain scannable across many changes and outcomes.
- The UI must not imply that starting a design session resolves its blocker.
- “Design” must remain user-started even if agents perform research and synthesis inside the session.
- Assembly must disappear when no broader composition claim exists, or it becomes duplicate ceremony.

## 10. Technical Assessment

Adopt the unified work board. Keep exact engine transformations as technical trace rather than primary
card identity. Use a global tagged portfolio and selected-change detail view across Design, Planning,
Implementation, and conditional Assembly. Passing the last distinct claim moves the item to
completed/archive storage. Treat dispatchability, readiness, waiting, review, and failure as
properties rather than columns.

Remove priority from the target job schema, runtime administration, Cockpit API, and board. Dispatch
all independent ready work in parallel within the execution limit; use dependency topology followed
by creation order when ready work exceeds that limit.

This supersedes the earlier assumption that Specification and Delivery require separate primary
surfaces. They remain distinct authority and execution phases internally, while Cockpit presents one
continuous visible workflow.

The compact PDS prototype establishes the accepted work-card hierarchy and approximate density, not
a replacement page composition. Implementation preserves the current Cockpit dashboard shell,
navigation, workspace-header rhythm, responsive behavior, and established PDS styling. It replaces
the job-centric projection inside that product frame rather than rebuilding the frame around the
prototype.

## 11. Confidence and Limits

**Confidence:** High that separating visible work items from jobs and changes from their execution
workspaces resolves the identified conflicts. The user accepted the compact prototype at roughly 80%
as a hierarchy and density reference, conditional on the real implementation remaining oriented to
the pre-redesign Cockpit dashboard.

**Limits:** This proposal does not select schema names, stage transition events, board virtualization,
or project-specific integration branch names. High-volume portfolio behavior still needs proof beyond
the prototype's representative cards during implementation.