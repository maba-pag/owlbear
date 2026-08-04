# Target Delivery Information Flow — Step 3: Discover Intent

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-02
> **Question:** How should incomplete product intent become durable, complete Specification without
> duplicate interview state, repository fact polling, or chat-only handoff?

## 1. Status Quo And Evidence

`w-design-session` conditionally invokes `w-idea-refinement` when a rough idea lacks an intended
outcome and Product Promise. The refinement workflow uses a private question tree, asks one
evidence-backed question at a time, and ends with a `Refined Idea Summary` that the caller must map
into its destination. Design, however, already owns `intent.md` and must persist confirmed meaning
through interruptions. Architecture review is the only other live consumer of the generic method.

Step 1 creates a useful seed. Step 2 returns complete current intent, commitments, choices, and any
typed Design transition. Step 3 therefore discovers only missing or changed user intent; it does not
rehydrate, inspect Delivery routinely, or establish repository facts that source can answer.

## 2. Decision D1 — Designer Owns The Interview

The same Designer selects and asks each intent question. Do not add a refinement agent or a
question-selection tool. The Designer already holds the governing context, while choosing the next
gap requires semantic judgment about user value rather than deterministic lifecycle policy.

Use this loop:

1. Start from the complete intent loaded in Step 2.
2. Select the unresolved user-owned question with greatest downstream leverage.
3. Route repository-answerable uncertainty through Step 4 evidence before asking.
4. Ask exactly one question through `askQuestions`, including current understanding, consequence,
   and a recommended answer; compare options only for a genuine material choice.
5. Persist the confirmed answer immediately, then recompute dependent gaps.
6. Present one coherent intent candidate for independent review, resolve its findings, then obtain
    user confirmation of the complete intent.

Refinement remains useful as reusable interview guidance, not a nested workflow with private durable
state or a chat-summary handoff. Convert it to a handbook-level method usable by Design and
architecture review; each consuming workflow owns its persistence and final output. Confidence: high.

## 3. Decision D2 — Hybrid Semantic Write Boundary

Designer directly edits long-form authored meaning in `intent.md`, `design.md`, and focused research.
Use contextual minimal patches, preserve untouched text, and retain exact user wording when wording is
material. Write each execution-relevant promise, commitment, acceptance boundary, or exclusion as a
readable normative block in its owning section. Creation supplies stable headings; deterministic
validation checks block shape, references, and declared coverage but never authors or judges meaning.

Use purpose-built tools for transitions whose correctness depends on shared mutable state, OCC,
replay, or atomic publication: draft identity creation, admitted authority, and Delivery lifecycle
evidence. Resolved Design choices update their owning intent or design meaning directly; deterministic
structure and reference validation uses the Step 7 derivation parser in read-only dry-run mode under
single-Designer ownership. Do not add a second validator or generic semantic `add_or_update` tool. Builder likewise edits
product code directly only in its assigned worktree. Confidence: high.

## 4. Decision D3 — Independently Reviewed Discovery Exit

The Designer first judges that the intended outcome, beneficiary, valuable workflow, boundaries,
preserved behavior, accepted exclusions, and observable success form one coherent Product Promise.
An independent reviewer then audits that complete intent for omissions, contradictions, silent
narrowing, and success that cannot be meaningfully observed. The reviewer neither chooses user
intent nor repairs the artifact. Designer resolves findings with the user, and the user confirms the
reviewed result before the session advances.

Later evidence or architecture may reopen discovery with a concrete contradiction. Passing this gate
does not approve implementation or replace final whole-Specification review. Confidence: high.

## 5. Decision D4 — Three Roles, Four Fresh Reviews

Use three independent reviewer roles across Specification. A Concept Reviewer receives a fresh,
focused invocation for the complete intent claim at the Step 3 exit and another fresh invocation for
the architecture claim at the Step 6 exit. At Step 9, the Forward Specification Reviewer traces
approved intent through design into the validated Delivery Contract, while the Reverse Specification
Reviewer independently reconstructs the assembled result from that contract before reading design
and approved intent. Current replaceable model policy assigns Claude Opus 5 forward and Sol reverse;
the two roles must use different model families.

Intent and architecture remain separate review claims even though one reviewer role can judge both.
The final directional reviews do not substitute for either earlier gate. Different models and
opposite read orders add whole-Specification traceability without another per-entity verdict. Fresh
invocations preserve independence and bounded context. Confidence: high.

## 6. Decision D5 — Formative Intent Critique

The Concept Reviewer returns comprehensive, organized feedback rather than a typed pass/fail verdict.
It examines every agreed intent dimension, names strengths, omissions, contradictions, silent
narrowing, ambiguity, observability problems, and useful improvements, and explains the consequence
of each observation. It distinguishes evidence from interpretation and does not rewrite intent or
make user-owned choices.

Designer evaluates every material observation: repair a clear defect, bring a genuine product choice
to the user, reject conflicting feedback, or carry a known concern forward. Persist only feedback,
rationale, rejected direction, or uncertainty that changes current meaning or could affect a later
decision. Invoke another independent review only after material change or incomplete review
coverage. The exit condition is completed critique and user confirmation of the resulting Product
Promise, not a reviewer-issued verdict. Confidence: high.

## 7. Decision D6 — Stable Review Lenses With An Open Lane

Every complete intent critique examines six lenses: problem and user value; fidelity to every
user-stated desired effect; normal workflow, visible result, failure, re-entry, and user control;
scope, preserved behavior, accepted exclusions, and their lost value; observable assembled success
and technically-complete-but-wrong outcomes; and coherence, assumptions, unresolved facts, and
consequences.

The reviewer may add any consequential observation outside these lenses. The lenses ensure complete
and comparable coverage without suppressing insight or turning the review into a closed checklist.
Technical architecture remains outside this intent review and receives its own later critique.
Confidence: high.

## 8. Decision D7 — Complete Intent Confirmation

Designer presents one compact but complete current intent: problem and beneficiary, full Product
Promise, normal workflow and visible result, boundaries and preserved behavior, every accepted
exclusion with lost value, observable success, technically-complete-but-wrong outcomes, and remaining
assumptions or open facts. Include review feedback only when its resolution, rejection, or remaining
uncertainty materially helps the user understand the current result.

Do not show only recent changes or the full critique transcript. The user confirms only that this is
the desired result; architecture, Delivery scope, and admission remain undecided. Confidence: high.

## 9. Step Boundary

Step 3 ends with one independently critiqued, explicitly dispositioned, and user-confirmed intent.
Step 4 grounds the repository and external claims needed to design that result.

## 10. Decision D8 — Agent-Based Formative Review Interface

After updating `intent.md` and its load-bearing evidence links, Designer invokes a fresh
`conceptual-design-reviewer` through the existing `agent` tool. Supply change identity, intent path,
current Product Promise, relevant evidence paths, the six review lenses, and prior observations that
need recheck. The reviewer reads the artifact and decisive sources with read, search, and web tools.

Return coverage and evidence limits plus organized observations under every lens. Each material
observation names its target, evidence, consequence, uncertainty, and bounded direction; return
user-owned questions and an open lane for other consequential observations. Do not return an
aggregate verdict. Independent model judgment belongs in an agent invocation, not an MCP wrapper.

Implementation must give the Concept Reviewer a formative protocol distinct from the shared typed
Delivery challenger protocol. Confidence: high.

## 11. Decision D9 — No Review Ledger

Keep the Concept Review response in the active conversation. Designer incorporates useful findings
into current intent or design, useful rejected-direction rationale, assumptions, or known limits. Do not add review
record, disposition, or review-history tools. Package-scoped Git snapshots preserve confirmed
semantic checkpoints, not every edit or conversation; working Specification preserves only critique
and rationale that can affect later decisions. Confidence: high.

## 12. Decision D10 — No New Intent Domain Tool

Use this exact sequence: load session, intent, commitments, and any Design transition through Step 2;
ground repository facts through source tools or Step 4 delegation; ask one question with
`askQuestions`; update `intent.md` directly; invoke the Concept Reviewer through `agent`; incorporate
useful critique through intent edits or Step 5 decisions; re-review only after material change or
incomplete coverage; then present and confirm the complete intent through `askQuestions`.

Keep a simple current intent state in the artifact: `draft`, `ready-for-review`, or
`user-confirmed`. `show_design_session` surfaces that state and the unresolved gate. Ambiguous answers
remain unresolved; an edit failure requires reread before retry; unavailable or malformed review
leaves `ready-for-review`; user absence leaves the draft resumable. Transition to `user-confirmed`
is incomplete until idempotent `publish_design_checkpoint(change_id, gate, expected_source_hashes)`
validates that authored gate and publishes the exact package-scoped semantic snapshot. Rehydration
replays a missing matching checkpoint before any later phase may consume the gate.

Keep `askQuestions`, file read/edit, search, and `agent`. Change the Concept Reviewer contract and
make refinement reusable guidance. Add no semantic mutation; checkpoint publication is the sole
shared-state write at this gate. Confidence: high.