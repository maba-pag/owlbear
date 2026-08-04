# S2 Checkpoint Cadence Examples

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** When should work pause for user guidance, group meaning for review, notify without blocking, or continue autonomously?
> **Status:** Evidence preparation for S2. No cadence policy is selected.

## 1. Context and Current Tension

The current workflow combines one large final Specification approval with coarse Delivery halts:

- Design asks one material question at a time, then requests approval of one complete digest.
- Planning may create one blocking Decision Request for a bounded material choice.
- A builder encountering any non-local finding returns `SpecificationReentry`; orchestration halts.
- Acceptance routes technical defects mechanically but broader semantic changes can reopen work.

This protects authority but does not distinguish a new protected consequence from a harmless plan
revision. S1 now provides that distinction through C1-C5 in `semantic-commitment-policy.md`.

## 2. Checkpoint Types

| Type | User experience | Use when |
|---|---|---|
| Dialogue | One focused consequence discussion; work waits for the answer | Intent is ambiguous, or viable paths differ in a C1-C3 consequence |
| Grouped review | One understandable summary of related semantics; user corrects priorities or confirms shared understanding | A layer or coherent topic has matured enough to judge as a whole |
| Decision Request | One durable, blocking deviation request with evidence and consequences | Delivery evidence makes changing C1-C3 necessary |
| Notification | Visible non-blocking summary recorded for later inspection | C4 strategy changes while protected meaning remains intact |
| Technical trace | No user interruption; available on demand | C5 implementation changes, generated mechanics, tests, and evidence |

These types are not lifecycle phases. One phase may use several types, and no checkpoint exists merely
because an artifact was written or an agent finished.

## 3. Ordinary Feature Timeline: Browser Notifications

### Step 1: Intent dialogue

**Agent explains:** The request appears to be “tell me promptly when agent work needs my attention so
I do not have to keep checking Cockpit.” It asks whether locked/shared-screen privacy, browser support,
or “promptly” contains a priority not yet understood.

**Pause:** Yes, only if that meaning is ambiguous. The resulting direct request becomes C2; an explicit
“never expose request content” becomes C1 or C2 according to the user's wording.

### Step 2: Grouped outcome and consequence review

After source inspection, the agent presents one short workflow:

- a new pending request becomes visible while Cockpit is backgrounded;
- the notification reveals the reviewed amount of content;
- click-through opens that request;
- denied permission leaves an in-app attention path;
- reconnect and resolution do not produce duplicate or stale alerts.

It also explains that the current SSE says only “requests changed,” so reliable new-request detection
needs state comparison or a more specific event. That technical path need not be chosen by the user
unless its latency, privacy, or reliability differs materially.

**Pause:** One grouped review of outcome, privacy, interruption, and fallback consequences. Do not ask
separately about hooks, SSE payloads, tags, routes, and test structure.

### Step 3: Strategy summary before Delivery

The agent presents the consequence-level strategy: permission is user-initiated, notification content
is privacy-bounded, the system identifies only newly pending requests, and unsupported/denied browsers
retain in-app visibility. It records whether the event mechanism is C4 or C5.

**Pause:** A brief correction opportunity if this adds or changes C1-C3 meaning. No new confirmation is
needed merely because architecture details were added underneath an already reviewed workflow.

### Step 4: Planning and Build

- Planner chooses state comparison or a backend event with equivalent reviewed effects: C4/C5,
  continue and record.
- Builder changes a hook or test fixture: C5, continue silently.
- Browser behavior forces less notification detail than preferred but preserves the privacy bound and
  attention workflow: C4, notify in semantic summary.
- Browser behavior makes timely notification impossible without a service worker that changes operating
  burden or permission expectations: C2/C3 consequence, create one Decision Request.

### Step 5: Acceptance and completion

Independent acceptance proves the workflow. Technical defects route to repair. A failure showing that
click-through cannot reliably identify the request returns to a Decision Request only if credible
repairs require changing protected behavior.

**User event:** Completion summary and usable result, not another approval of test traces.

## 4. Infrastructure Timeline: Delivery Pipeline Replacement

### Step 1: Intent and outcome dialogue

The user and agent establish the collaboration promise, reduced ceremony, durable meaning, dependable
delivery, and unacceptable technically-done-but-wrong results.

**Pause:** Focused dialogue while intent remains ambiguous. Do not present architecture choices before
the desired working relationship is understandable.

### Step 2: Topic-grouped consequence reviews

Repository research develops several coupled topics. Review them as coherent consequence groups rather
than one question per field or one giant final document:

1. collaboration, semantic commitments, and what may adapt;
2. authority, generated work/evidence, and user-facing transparency;
3. assurance, correction, and interruption economics; and
4. migration, cutover, rollback, and retained history.

Within a topic, ask one consequence question at a time when the previous answer controls the next.
Close the topic with a short integrated recap. Do not request confirmation after every requirement,
interface, risk, or proof entry.

### Step 3: Enabled readiness review

Before Delivery, present the Product Promise, outcome graph, protected commitments, consequence-level
strategy, representative acceptance, unresolved limits, and what remains adaptable. Detailed IDs,
schemas, paths, and proof matrices remain drill-down.

**Pause:** Yes. This is correction of shared meaning, not certification of graph mechanics. If the user
spots a missing promise or wrong tradeoff, revise the owning topic and refresh the integrated view.

### Step 4: Planning

- Packet boundaries, exact paths, commands, and IDs: C5, continue.
- A more economical implementation preserves C1-C3 but revises C4: continue, independently review,
  and include in a non-blocking semantic delta.
- Planning finds that a protected workflow, safety property, or important assurance boundary must
  change: group related evidence into one Decision Request; do not create one per affected node.
- Several independent protected consequences change: separate requests only when resolving one does
  not resolve the others or combining them would obscure tradeoffs.

### Step 5: Build, acceptance, and audit

- Implementation defects and equivalent technical repairs proceed through agent review and proof.
- A planning omission that can be repaired without changing C1-C3 returns to Planning without user
  interruption.
- A discovery that changes C1-C3 pauses only the affected semantic frontier; unrelated work may
  continue when dependency and writer safety permit.
- Acceptance and audit failures create user requests only when all credible corrective routes alter a
  protected commitment. Otherwise, the engine creates corrective work and reports progress.

### Step 6: Completion

Present what now works, protected commitments satisfied, approved deviations, known limits, and where
evidence can be inspected. Completion is not another design approval unless audit exposes unresolved
meaning.

## 5. Cadence Consequences

### Frequent approval cadence

**Improves:** Immediate user control and small semantic deltas.

**Costs:** Context switching, approval fatigue, accidental elevation of technical detail, and request
storms. The user may approve without understanding because each fragment lacks the whole.

### Phase-only approval cadence

**Improves:** Few interruptions and coherent phase summaries.

**Costs:** Important tradeoffs may remain hidden until a large final gate; later evidence can halt the
whole system because there is no graded correction route.

### Semantic-event cadence

**Improves:** Discussion occurs when meaning or protected consequences change; technical work remains
autonomous; related effects can be grouped into understandable review objects.

**Costs:** Requires reliable C1-C5 classification, semantic deltas, request grouping, and selective
frontier blocking. Misclassification can either hide change or create excess interruption.

## 6. Technical Assessment

The evidence favors semantic-event cadence with three deliberate user surfaces:

1. focused dialogue while shaping ambiguous or materially divergent consequences;
2. grouped review when a coherent semantic layer/topic is understandable; and
3. blocking Decision Requests only for necessary C1-C3 deviation during Delivery.

C4 changes become non-blocking semantic deltas; C5 remains technical trace. Final readiness and
completion summaries preserve the whole without becoming requests to approve mechanics.

This assessment is not a selected policy. S2 still needs the user's tolerance for asynchronous
progress, grouped deviations, and the possibility that unrelated work continues while one semantic
frontier waits.

## 7. Limits

**Resolution:** See `checkpoint-cadence-policy.md`. User Requests block the affected task and its true
dependents while unrelated ready work continues; user-facing discussion names commitment meaning
rather than internal C1-C5 codes.

This note does not define notification channels, response deadlines, request grouping algorithms,
parallel writer policy, or UI. It assumes the engine can eventually block an affected frontier rather
than always halting the entire change; feasibility remains to be designed and reviewed.