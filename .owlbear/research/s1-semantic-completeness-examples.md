# S1 Semantic Completeness Examples

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** What semantic meaning should be settled before Delivery, and what may safely emerge during repository-grounded Planning?
> **Status:** Evidence preparation for S1. No completeness policy is selected.

## 1. Context and Question

“Complete before Delivery” can mean several different things. The useful boundary is not document
size. It is which consequences are stable enough that agents can implement without silently changing
value, and which details are better decided after focused source inspection.

This note compares one ordinary feature and the current infrastructure redesign at three depths. The
depths are lenses for discussion, not a closed option list.

## 2. Sources Studied

| Source | Relevant fact |
|---|---|
| `cockpit-browser-notifications.md` | Proposes browser notifications for pending decision/action requests, permission UX, deduplication, and click-through. |
| `NativeInvalidationProvider.tsx` | Current SSE emits `native-changed` events with resource classes and a monotonic token, not the changed request record. |
| `RequestsPage.tsx` | Current UI lists pending/resolved native requests and routes to one request through query state. |
| Cockpit source search | No current Web Notifications API implementation exists. |
| `replace-delivery-pipeline/intent.md` | Defines the user-facing phase model, agent transformations, independent acceptance, and cutover promise. |
| `replace-delivery-pipeline/design.md` | Defines authority/work/evidence/Git responsibilities and detailed lifecycle/currentness semantics. |
| DN-003 plan and unpublished repair | Shows both useful source-grounded strategy and repeated inherited contracts/review prose. |

## 3. Completeness Depths

### Depth A: outcome-sealed

Before Delivery, settle the Product Promise, normal workflows, visible failures, preserved behavior,
accepted exclusions, outcome ownership, and high-level success examples. Defer architecture,
cross-boundary ownership, detailed acceptance, and implementation strategy to Planning unless already
known to affect the promise.

**Enables:** Shorter early collaboration and maximum repository-grounded flexibility.

**Takes over later:** Planning must discover interfaces, failure semantics, migration, proof, and
irreversible choices while Delivery is already active.

**Cannot guarantee:** Low interruption or low re-admission. A technically plausible plan can reveal
that the approved outcome was incomplete or impossible under unstated constraints.

### Depth B: consequence-and-strategy sealed

Before Delivery, also settle material constraints, representative success/failure/boundary acceptance,
cross-boundary ownership, important interfaces and failure semantics, irreversible or costly strategy,
migration/cutover consequences, and a feasible proof boundary. Defer packet decomposition, local code
structure, exhaustive edge matrices, exact paths/commands, and generated lifecycle records.

**Enables:** Agents can choose details later without changing reviewed consequences. Material value,
integration, and proof gaps are exposed before implementation.

**Takes over early:** Specification needs deeper repository research and consequence dialogue.

**Cannot guarantee:** No later correction. Implementation evidence may still expose a genuinely new
material consequence that returns to collaboration.

### Depth C: execution-sealed

Before Delivery, additionally settle packet boundaries, detailed scenario matrices, output inventories,
path closures, proof commands, context profiles, and much of the implementation sequence.

**Enables:** Builders receive highly explicit work and fewer local planning choices.

**Takes over early:** Specification performs work that may depend on source details better inspected in
a focused Planning context.

**Cannot guarantee:** Plan stability. Early detail may be speculative, duplicated across layers, and
invalidated by the first accepted implementation fact.

## 4. Ordinary Feature Story: Browser Notifications

### Reviewed parent intent

When a request needs attention, the user should learn promptly without repeatedly checking Cockpit,
and should reach the relevant request with little friction.

### What outcome-sealed would establish

- A newly pending decision/action request can notify the user while Cockpit is backgrounded.
- Clicking the notification opens the relevant request.
- Resolved requests do not notify.
- Denied or unavailable browser permission does not break Cockpit.

This is not yet enough to prevent divergent products. It leaves open whether request text is exposed
on the desktop, when permission is requested, whether foreground notifications appear, how duplicates
behave after reconnect, whether multiple requests group, and what non-notification fallback remains.

### What consequence-and-strategy sealed would add

- Privacy consequence: which request fields may appear outside Cockpit and on a locked/shared screen.
- Interruption policy: which request kinds notify, whether foreground Cockpit suppresses them, and how
  grouping or repeated events behave.
- Permission workflow: notifications are user-initiated/configurable rather than an unexplained prompt.
- Failure behavior: denied/unsupported permission leaves an understandable in-app pending indicator.
- Ownership: the system must identify a newly pending request, not merely “requests changed.” Current
  SSE carries a resource token, so Planning must either compare request state or introduce a more
  specific event without changing the reviewed notification behavior.
- Proof boundary: real event-to-notification-to-request navigation behavior, with browser APIs replaced
  only below that assembled frontend boundary.

### What may safely remain for Planning

- Hook/component names and file placement.
- Whether new-request detection uses state comparison or a specific backend event, provided reliability,
  privacy, deduplication, and latency consequences remain equivalent.
- Exact notification tags, cache shape, test fixtures, and browser API adapter details.
- Focus/navigation implementation and detailed negative-case matrix.

### Technically done but wrong

- Notify on every generic `requests` invalidation, producing duplicates on reconnect or resolution.
- Put the full request body in a desktop notification without a reviewed privacy decision.
- Ask permission on first load before the user understands the feature.
- Show notifications, but clicking opens a stale or unrelated request.
- Treat denied permission as feature completion with no visible in-app attention state.

## 5. Infrastructure Story: Delivery Pipeline Replacement

### Reviewed parent intent

The user states desired change once, collaborates with agents to shape meaning and strategy, and then
receives dependable implementation, correction, and proof without managing mechanical workflow or
reconstructing truth from generated artifacts.

### What outcome-sealed established

- Specification, Planning, Build, Acceptance, and Audit are meaningful agent transformations.
- Product intent and decisions persist.
- Work is outcome-oriented and independently accepted.
- Cockpit exposes Specification and Delivery.
- The old pipeline is removed at cutover.

For this infrastructure change, that depth was too shallow. Authority boundaries, currentness,
reconciliation, writer safety, exact-commit proof, bootstrap, and cutover ownership materially affect
whether the promise is achievable. Discovering them during Delivery created graph expansion and
re-admission churn.

### What consequence-and-strategy sealed should add

- Graduated user/agent collaboration and enabled-review surfaces.
- Which semantics are authority, which records are generated, and how neither duplicates the other.
- Outcome and interface ownership across Specification, Planning, Build, Acceptance, Audit, and UI.
- Material currentness and correction guarantees, without fixing every diagnostic or algorithm.
- Assurance boundaries and what independence each one contributes.
- Shared-work safety, proof isolation, migration/cutover consequences, rollback expectations, and
  deletion ownership.
- Representative end-to-end proof that the system reduces rather than relocates ceremony.

### What may safely remain for Planning and implementation

- Packet boundaries inside admitted outcomes.
- Exact schemas, field names, ID allocation, receipt envelopes, store layout, and transaction classes.
- Detailed currentness algorithms and diagnostic literals after public failure semantics are stable.
- Exact test commands, fixture topology, paths, closures, and context profiles.
- Adapter and package placement when alternatives preserve reviewed ownership and operating effects.

### What execution-sealed added too early or repeated

- Exhaustive packet AC restatement for inherited obligations.
- Exact path and authority closures duplicated at packet and plan level.
- Proposed job IDs and generation identities.
- Full proof command inventories and collected-case hashes before implementation.
- Repeated six-dimension pass prose and unbounded fresh review iterations.

Some detailed lifecycle invariants were genuinely necessary because they changed safety or failure
semantics. Their necessity does not imply that all packet and evidence mechanics belonged before
Delivery.

## 6. Cross-Example Consequence

Depth A works poorly when hidden interfaces or irreversible choices can change the promised result.
Depth C works poorly when source-grounded implementation detail is uncertain or likely to churn.
Depth B attempts to stabilize consequences and strategy while leaving execution detail adaptable.

The unresolved issue is whether one adaptive boundary should apply by materiality, or whether certain
change classes need a predictably deeper seal. That choice controls early collaboration depth, later
interruptions, and the risk of either value erosion or speculative planning.

## 7. Recommendation, Confidence, And Limits

**Resolution:** See `semantic-commitment-policy.md`. The controlling boundary is graded semantic
commitment rather than one immutable completeness depth.

**Technical assessment:** The evidence favors consequence-and-strategy completeness as a baseline,
with deeper pre-Delivery detail only for cross-boundary, irreversible, destructive, security-sensitive,
or proof-enabling work. This assessment follows the comparison; it is not a selected policy.

**Confidence:** High for the ordinary notification boundary and for the diagnosis that the pipeline
redesign mixed necessary semantic depth with premature execution detail. Medium on one adaptive rule
until the user's interruption and assurance priorities are understood.

**Limits:** The notification feature is historical and its original task/DR vocabulary is stale; this
analysis maps it to current native requests and current Cockpit source. No feature or redesign decision
is authorized by this note.