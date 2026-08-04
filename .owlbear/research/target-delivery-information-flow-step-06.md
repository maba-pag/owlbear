# Target Delivery Information Flow — Step 6: Design Architecture

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-02
> **Question:** How should confirmed intent become a coherent, source-grounded architecture whose
> exit receives independent formative critique without fixed ceremony, hidden omissions, or
> reviewer authority over product meaning?

## 1. Status Quo And Evidence

Current Design starts architecture once intent can constrain implementation. It asks the Designer to
adapt depth to novelty, coupling, irreversibility, and risk, and to cover owners, interfaces,
control/data flow, migration, compatibility, deletion, alternatives, weaknesses, and proof in
`design.md`. Material user consequences return to Step 5.

The module-design handbook supplies diagnostics for module depth, locality, effective interfaces,
deletion, seams, and dependency placement. Step 4 now supplies explicit source contexts and an owned
read-only researcher. Step 5 keeps commitment strength and evidence status with current meaning in
the two living authorities.

The current Concept Reviewer is read-only and can inspect product, workflow, authority, failure, and
module consequences, but its `pass | revise | rethink` result and dimension scores conflict with the
formative observation contracts approved in Steps 3 and 5. Current guidance also names architecture
topics without defining the minimum coherent claim or exact exit/handoff.

## 2. Decisions To Resolve

1. Define invariant architecture questions and how review depth adapts without permitting omission.
2. Define the exact Designer information and tool sequence while architecture develops.
3. Define the complete exit critique payload, lenses, response, and evidence limits.
4. Define how observations reopen evidence, user choices, or architecture and when Step 6 ends.
5. Define the exact handoff into Step 7 authority construction.

## 3. Current Boundary

Architecture remains authored current meaning in `design.md`, not a reviewer-owned record or an
admission claim. Step 6 may refine intent only through an explicit Step 5 consequence choice; it may
not silently narrow the Product Promise. Step 7 derivation, Step 8 validation, Step 9 directional
reviews and authorization, and admission
remain later boundaries.

## 4. Decision D1 — Invariant Questions, Adaptive Depth

Every architecture answers these questions:

1. Which Product Promise, preserved behavior, and commitment does the realization support?
2. What owns the behavior before and after, and where do knowledge and verification live?
3. Which caller-visible interfaces, invariants, ordering, errors, configuration, security/privacy,
	and performance constraints change?
4. How do control, data, and state move through material normal, failure, retry/re-entry,
	cancellation, and concurrency paths?
5. Which dependencies and seams are real, and who operationally owns them?
6. What migrates, is removed, remains compatible, recovers, and requires absence proof?
7. Which meaningful tradeoffs, weaknesses, assumptions, and unresolved risks remain?
8. Which assembled behavior and focused proof can establish support for intent without being
	technically complete but wrong?

A localized change may answer an item concisely as unchanged or not applicable with a source-
grounded reason. Novelty, coupling, irreversibility, user impact, uncertainty, and proof difficulty
increase depth. Do not invent alternatives, diagrams, or detail when one clear boundary suffices;
do not omit a question because a change appears small. Confidence: high.

## 5. Decision D2 — Trigger-Based Minimal Proof Depth

For each changed behavior or critical preserved behavior, architecture names the maintained or public
boundary, plausible regression, and cheapest check that would fail for the right reason. Reuse
existing coverage. Test count and line coverage never create proof obligations.

Escalate only for a named property: broad inputs or invariants use equivalence or property tests;
state and re-entry use transition tests; concurrency and atomicity use deterministic invariant tests;
public, high-fan-out, or frequently used interfaces use a focused shared-boundary contract test;
remote dependencies use contract plus the smallest real integration; severe security, privacy,
authority, migration, or data-loss consequences add adversarial failure and assembled normal proof;
cross-module user journeys use one maintained-boundary integration or E2E path; prior defects get the
smallest durable regression; performance gets a benchmark only when it is a commitment.

Prefer compiler, linter, schema, generated-contract, or structural validation for static invariants.
Agent and prompt artifacts receive structure, wiring, tool-boundary, and consequential scenario
checks, never exact prose comparisons unless literal text is itself a public contract. Do not add
durable file-existence/removal proofs, config-presence tests, implementation-detail assertions,
duplicate paths, or acceptance-criteria paraphrases.

Architecture records concise proof boundaries, not a test inventory. Planner chooses cases inside
them; Builder adds the minimum distinguishing assertions; review challenges both proof gaps and
unjustified test volume. Confidence: high.

## 6. Decision D3 — Construct Directly, Review At Exit

Step 6 designs architecture; formative critique is its exit, not the phase's whole activity. First
rehydrate the session and complete intent, confirm no unresolved user consequence blocks the current
frontier, inspect explicit source contexts, and read the required and linked design sections. Map
every intent promise and commitment through D1's invariant questions.

Ground factual gaps with explicit-context search/read or one bounded `source-researcher`, then reread
decisive source. Directly edit coherent `design.md` sections with commitment strength, claim-local
evidence, tradeoffs, weaknesses, and D2 proof boundaries. Express execution-relevant constraints and
proof boundaries as readable normative blocks. Validate block shape, coverage, structure, and
references, then reread each changed slice and its dependencies.

A material user consequence returns one choice to Step 5; technical choices inside confirmed
boundaries remain Designer-owned. Stale source forces reinspection, edit ambiguity forces reread,
and unresolved evidence remains an explicit assumption or blocks its dependent claim. Add no
architecture generator, semantic mutation API, or combined context payload. Invoke a fresh formative
Concept Review only after one complete architecture claim exists. Confidence: high.

This review tests architecture-to-intent coherence while defects remain cheap to repair. It does not
re-audit Steps 1–5. Step 8 later validates deterministic derivation and graph integrity; Step 9 adds
independent forward and reverse whole-Specification perspectives without redesigning architecture.

## 7. Decision D4 — Fresh Formative Architecture Critique

Invoke a fresh `conceptual-design-reviewer` with exact intent and design paths, source-context
identities and revisions, Product Promise and commitment map, complete architecture claim, D1
answers, D2 proof boundaries, decisive evidence locators, assumptions and known limits, and any
prior observations needing recheck.

Require coverage and evidence limits, load-bearing strengths, and organized material observations
under these lenses: intent and commitment fidelity; ownership, locality, and module depth; effective
interfaces and failure semantics; control/data/state lifecycle; dependencies, seams, and operational
ownership; migration/removal/compatibility/recovery; security/privacy/performance and uncertainty;
and proof validity and proportionality. Each observation names target, evidence, consequence,
uncertainty, and bounded correction and distinguishes unsupported fact, design disagreement, and a
hidden user consequence. Return no aggregate verdict, scores, replacement architecture, approval,
or task decomposition.

Designer repairs a defect, grounds a disputed fact, returns one hidden user consequence to Step 5,
rejects conflicting feedback with concise rationale, or retains an honest known limit. Re-review
only after material architecture change or incomplete coverage. Unavailable or malformed required
critique leaves Step 6 incomplete.

Exit requires complete critique, disposition of every material observation into current meaning,
and no unresolved architecture fork or user consequence. Present a concise architecture and
consequence summary without separate architecture approval; final directional reviews and any
Delivery authorization remain Step 9.
Confidence: high.

## 8. Decision D5 — Current Authority And Lightweight Gate State

Hand Step 7 only current authority and resumable gate state. `intent.md` remains `user-confirmed`.
`design.md` is `draft`, `ready-for-review`, or `reviewed` and records checked source-context
identities plus explicit assumptions and known limits. `reviewed` means formative critique completed,
all material observations were dispositioned, and no architecture fork or user consequence remains;
it is not approval.

`show_design_session` exposes these gates. Step 7 rereads complete intent and design, validates the
package, and translates their current statements into `authority.json`. It does not consume chat,
reviewer output, or a generated architecture summary. Material architecture edits reset review;
nonsemantic corrections do not. Incomplete critique coverage remains `ready-for-review`.

Transition to `reviewed` is incomplete until Step 5's idempotent `publish_design_checkpoint`
validates the gate and expected source hashes and publishes the reviewed-design snapshot. Step 7
refuses a gate without that matching checkpoint. The snapshot excludes review output.

Add no review digest, ledger, handoff file, or semantic mutation; checkpoint publication alone owns
the package-history ref write. Confidence: high.

## 9. Step Completion

Step 6 is decided. Implementation must rename it Design Architecture, adopt D1's completeness and
D2's proof-depth policies, use the direct sequence in D3, replace the Concept Reviewer's verdict
schema with D4's formative architecture mode, and expose D5's lightweight gate state.