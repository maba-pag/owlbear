# Target Delivery Information Flow — Step 7: Derive Delivery Contract

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-02
> **Question:** How should reviewed intent and architecture deterministically produce one immutable
> machine contract that Delivery can execute without semantic re-authoring or mutable prose reads?

## 1. Status Quo And Evidence

`TargetAuthority` currently contains provenance-classed commitments, user-facing outcomes with
acceptance and dependencies, outcome or change-assembly planning scopes, and later Design re-entry,
semantic-update, and completion records. Admission requires one active outcome and exactly one plan
scope per active outcome, derives the initial dependency frontier, and binds challenge coverage and
approval to the canonical authority digest.

Runtime and Cockpit projections consume outcome identity, title, promise, acceptance, commitment
links, dependencies, replacements, and scopes. Delivery planning resolves commitments through those
links. The runtime does not read draft `intent.md` or `design.md`, which is correct for immutable
execution authority.

The current schema permits empty commitments, outcomes without commitment links, and concise free-
text acceptance. It validates identity and reference mechanics more strongly than semantic coverage.
The two reviewed living documents now own complete meaning; `authority.json` must be a sufficient
immutable projection, not a third authored explanation or a pointer back to mutable prose.

## 2. Decisions To Resolve

1. Define the exact projection contents and source-revision traceability.
2. Define commitment inclusion so protected meaning is complete without serializing every design note.
3. Define outcome, dependency, acceptance, and planning-scope boundaries.
4. Define translation tools, validation, failure behavior, and resumability.
5. Define the exact candidate handed to Step 8 validation and Step 9 review.

## 3. Boundary

Designer owns translation and direct draft edits. Deterministic validation may reject structural or
coverage defects but cannot invent semantic identities or judge whether a promise is desirable.
Step 7 does not challenge, baseline, approve, admit, plan tasks, or create runtime work.

## 4. First-Principles And Adversarial Audit

Initial `Explore` reports supplied code-location evidence only; their architectural opinions carry no
decision weight. Three later independent `Claude Opus 5` critics argued against, for, and outside the
current boundary. Their source premises were checked directly. They converged that Delivery needs a
structured revision that does not require runtime to reinterpret unconstrained prose, but two found
that hand-authoring it beside reviewed documents creates an undetectable translation gap.

Its job is to define exactly what Delivery is authorized to deliver and bind every derived job,
request, review, receipt, projection, correction, and revision to that semantic identity. Designer
produces a candidate; admission validates it, derives the initial frontier, hashes and publishes it;
Planner and Builder resolve admitted work and commitments; runtime rejects stale identities; Cockpit
projects user-visible work. A later approved revision replaces it only when active work is absent and
archives the prior authority by digest. It is revision-immutable, not permanently immutable.

This does not justify the current schema wholesale. `design_reentries` duplicates runtime-owned
current briefings. `semantic_updates` and `completion_summaries` are lifecycle evidence, not semantic
definition. Source-document binding must make the execution contract self-contained while preserving
an exact way to prove translation from the reviewed documents.

The artifact is not for current-system explanation, alternatives, architecture rationale, review
transcripts, commands, task lists, test inventories, mutable progress, or exhaustive history.

## 5. Opus Challenge Synthesis

The architectural choice is not structured contract versus no contract. It is whether the structured
contract is a third authored semantic copy or a deterministic projection of normative statements in
the two living documents. Frozen unconstrained Markdown cannot enumerate stable work identities;
hand-translated JSON can silently omit or alter reviewed meaning. Both defects disappear only when
the authored documents carry explicit typed normative statements that extraction copies without
semantic summarization.

The strongest current direction is therefore: keep `intent.md` and `design.md`; give execution-
relevant commitments, outcomes, acceptance, dependencies, and proof boundaries stable typed blocks
at their semantic owner; derive the compact Delivery Contract deterministically; approve and bind
the exact derived revision plus its source hashes; and keep runtime evidence outside it. This removes
Step 7 semantic re-authoring but retains validation, stable identities, digest-pinned work, revision
archival, and focused agent reads.

The remaining falsifier is authoring quality. If atomic normative blocks cannot remain readable and
complete, extraction becomes either brittle parsing or disguised model judgment. In that case an
explicit separately reviewed contract is the honest boundary. This must be decided before fields.

## 6. Decision D1 — Derive, Do Not Re-Author

Keep `intent.md` and `design.md` as the two authored semantic authorities. Execution-relevant meaning
uses readable strict normative blocks at its owning section: stable identity, exact statement or
promise, commitment strength and provenance where relevant, observable acceptance, semantic links,
dependencies, and architecture-defined delivery or proof boundaries.

A deterministic parser validates and copies explicit block fields into the compact Delivery
Contract. It performs no model inference, summarization, classification, or semantic rewriting.
`authority.json` becomes generated output and must never be hand-edited. Admission freezes the
derived revision and binds it to exact source-document hashes; normal Delivery consumes the generated
contract, not mutable Markdown.

A dedicated transport-free derivation component owns parsing and canonical generation. Admission
composes that component and supplies exact current source bytes; no caller may submit an unrelated
generated object as proof of derivation. The readable normative-block format must be demonstrated on
representative intent and design before implementation freezes the contract schema. If that format
cannot remain readable and complete, Steps 8 and 9 reopen around the explicitly reviewed separate-
contract fallback.

This yields one authored source, stable machine identities, deterministic replay, and mechanically
detectable translation fidelity. The cost is deliberate structure inside normative document regions.
If representative blocks cannot remain readable and complete, fall back to a separately authored and
explicitly reviewed contract rather than weakening derivation. Confidence: moderately high pending
format proof.

## 7. Decision D2 — Agent-Only Compilation Boundary

Step 7 is an internal compilation step. It takes the reviewed intent and architecture, derives the
small exact Delivery Contract, validates structural consistency, and hands the candidate directly to
Step 8 deterministic validation. The user does not read, edit, confirm, or receive a summary of the
generated representation.

User-facing meaning and material consequences were resolved while they were still understandable in
Steps 3–6. As information density rises, user participation deliberately shrinks and agent plus
deterministic responsibility grows. Later work returns to the user only when evidence changes a
Product Promise, protected consequence, accepted exclusion, or other user-owned commitment.

This walkthrough decides the input, automatic derivation, faithful-mapping obligation, and machine
handoff only. File format, block syntax, field names, identity scheme, parser mechanics, and migration
from the current schema are implementation design. Confidence: high.

## 8. Decision D3 — Semantic Definition Only

The generated Delivery Contract contains only revision-immutable semantic definition and source
bindings needed by Delivery. Remove Design re-entry briefings, semantic updates, completion summaries,
and other post-admission evidence from `TargetAuthority`. Runtime owns their creation and current
state; projections join runtime evidence with the admitted contract when needed.

This removes competing writers and prevents re-admission from freezing stale execution history into
new semantic authority. Known limits remain in their owning intent or design statements and are
projected into the contract only when they constrain authorized Delivery behavior. Confidence: high.

A revision that removes accepted behavior expresses required undo or replacement as an ordinary
outcome. Prior commit bindings remain runtime evidence joined into validation and Planning context.

Every composition contract belongs to one outcome. Cross-outcome verification is represented by that
outcome's dependencies on every result it composes; no change-level outcome, status, or claim exists.

## 9. Step Completion

Step 7 is decided at the information-flow level, conditional on representative format proof. Step 8
checks source-bound derivation and deterministic contract rules; Step 9's directional reviewers test
whole-Specification meaning preservation. Neither asks the user to interpret machine representation.