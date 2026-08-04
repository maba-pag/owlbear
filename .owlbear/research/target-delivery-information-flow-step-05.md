# Target Delivery Information Flow — Step 5: Resolve Decisions

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-02
> **Question:** Which Specification choices belong to the user, how should they be resolved, and how
> does confirmed rationale remain durable without turning the user into the implementation designer?

## 1. Status Quo And Evidence

Current Design asks one material question at a time and records accepted, pending, and superseded
choices. The existing rule names broad product and architecture categories, but the consequential
boundary matters more than a choice's technical vocabulary. A technical mechanism can change user
control, migration risk, or proof confidence; a product-facing choice can be harmless discretion.

Intent and architecture receive independent formative critique. Reviewers may expose a hidden
consequence, but only the user can choose among materially different outcomes they own.

## 2. Decision D1 — Consequence-Based Decision Authority

Bring a choice to the user when alternatives materially change the Product Promise, workflow or user
control, scope or preserved behavior, accepted exclusions, public contract, migration consequence,
security or privacy posture, irreversible commitment, or the cost and confidence of completion
evidence. Also ask about any architecture consequence the user explicitly marked important.

Designer decides evidence-backed technical choices inside confirmed boundaries, records
consequential rationale, and exposes them to architecture review. Reviewers may identify a hidden
user consequence but do not make the choice. Confidence: high.

## 3. Decision D2 — Adaptive One-Choice Conversation

Ask exactly one user-owned decision at a time through `askQuestions`. State confirmed context and why
the choice matters now. When genuine alternatives exist, compare two to four options by their effect
on value, workflow, scope, risk, cost, and evidence confidence, then give the Designer's evidence-
backed recommendation and uncertainty. Use lighter clarification when no real alternative exists.

The user may select, modify, reject the framing, or defer. Ambiguous and deferred answers remain
unresolved. After a clear answer, Designer records the selected consequence and rationale before
opening another material branch. Confidence: high.

## 4. Decision D3 — Risk-Triggered Focused Review

Invoke the Concept Reviewer before a user decision only when the choice is hard to reverse,
introduces a new product or operating model, has broad cross-cutting consequences, rests on disputed
evidence, or the Designer cannot confidently expose the real trade-off. The reviewer critiques the
framing, missing alternatives, consequences, and evidence without choosing for the user or replacing
the Designer's recommendation.

Ordinary choices proceed directly and remain covered by complete intent or architecture critique.
Later review may reopen a choice whose hidden consequence was missed. Confidence: high.

## 5. Decision D4 — Living Meaning, Selective Rationale

Write the selected meaning into its owning intent or design section with commitment strength,
consequence, decision-driving rationale and evidence, and unresolved uncertainty. Preserve user
wording when wording matters and retain a rejected direction only when its grounded reason could
prevent a later mistake or explain the current shape.

Exploratory wording, routine alternatives, repeated clarification, reviewer comments, and general
conversation remain transient. Current intent and design express active meaning directly; concise
rationale explains consequential shape rather than serving as an audit log. When interpretation could diverge
from the user's answer, show the consequence before resolving it. Confidence: high.

## 6. Decision D5 — Practical In-Place Revision

Reopen a resolved decision only when the user requests reconsideration, new evidence contradicts a
premise, later critique exposes an unconsidered consequence, or the selected direction can no longer
preserve confirmed intent. Show what changed and which downstream meaning may be affected.

Update the owning intent or design meaning and affected commitments in place. Add a concise changed-
because note and prior direction only when that history helps later work interpret the current choice.
Semantic gate snapshots preserve approved prior meaning; transient edits do not. Revisit only dependent choices and review gates; minor implementation
discoveries do not qualify without a changed premise or material consequence. Confidence: high.

## 7. Step Boundary

Step 5 ends when no user-owned material choice required for the current intent and architecture
frontier remains unresolved. Decisions continue to reopen through explicit supersession when later
evidence changes a premise or consequence.

## 8. Decision D6 — Direct Owning-Document Edits

Add no Step 5 mutation tool or decision file. After one clear answer, Designer makes one minimal
coordinated patch across every affected `intent.md` or `design.md` section. Replace the unresolved
choice with current meaning, material consequence, commitment strength, concise decision-driving
rationale and evidence, only useful changed-because history, and updated normative blocks for every
execution-relevant consequence.

Run the Step 7 derivation parser in read-only dry-run mode for required sections, commitment
classifications, unresolved markers, normative-block shape and coverage, cross-references, and
evidence locators, then reread changed meaning before another question. Validation neither authors
nor judges semantics. A failed or uncertain edit requires rehydration of every affected file; any
mismatch stays explicitly unresolved. Single-Designer ownership, mandatory rehydration, and Git make
OCC and a decision-application lifecycle disproportionate. Reconsider a mutation service only if
concurrent Design writers become real. Confidence: high.

Create package-scoped semantic snapshots only at user-confirmed intent and reviewed design. Each
idempotent `publish_design_checkpoint` validates the authored gate and expected source hashes, then
writes Specification and source-reference metadata to the dedicated package-history ref, never the
product branch, mutable runtime state, review output, or conversation. A gate without its matching
checkpoint is incomplete; coordinated edits between gates remain resumable but are not exhaustive history.

## 9. Decision D7 — Focused Formative Concept Review

When D3's risk trigger fires, invoke a fresh `conceptual-design-reviewer` agent with artifact paths,
one exact unresolved choice, confirmed boundaries, genuine options and consequences, decisive
evidence locators, Designer recommendation and confidence, unknowns, and the review trigger. The
reviewer may read exact sources needed to challenge the framing.

Return coverage and evidence limits plus material observations about framing fidelity, missing
genuine alternatives, unsupported consequences, hidden user-owned consequences, and disproportionate
ceremony. Each observation names target, evidence, consequence, uncertainty, and bounded correction.
Do not return an aggregate verdict, dimension scores, replacement design, or reviewer recommendation.

Designer repairs clear framing or evidence defects, researches challenged facts, adds a genuine
missing option, and reshapes the same single decision around any hidden user consequence before
calling `askQuestions`. Keep review in conversation; persist only changed current meaning,
consequential rationale, or unresolved uncertainty. If required review is unavailable or lacks
coverage, leave the choice unresolved and expose the limit. Add no MCP tool or review ledger.
Confidence: high.

## 10. Step Completion

Step 5 is decided. Implementation must replace the Concept Reviewer's current verdict-shaped output
with the formative contracts required by Steps 3, 5, and 6 without creating separate reviewer roles.