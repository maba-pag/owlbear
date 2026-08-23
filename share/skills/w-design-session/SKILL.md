---
name: w-design-session
description: "Workflow: Create or resume one target design session and admit only complete approved semantic authority"
user-invocable: false
---

# Target Design Session

Turn a rough idea or named change into durable OwlBear target authority. Preserve confirmed intent
and decisions across interruptions, resolve one material choice at a time, and admit only a complete
candidate that passes validation, independent challenge, baseline, and explicit approval.

This workflow owns Specification. It does not implement product code, create Delivery jobs directly,
or turn conversation history into a second authority.

## Companion Skills

Load these with `read_file` immediately before the named work:

| Skill | Load when |
| --- | --- |
| `w-idea-refinement` | `/ideate` input is too rough to state the intended outcome and Product Promise |
| `h-codebase-orientation` | Locating current owners, interfaces, tests, and normal workflows |
| `w-research` | A material external or repository claim needs durable source-grounded research |
| `h-module-design` | Reviewing proposed ownership, interfaces, locality, or dependency placement |
| `h-memory-structure` and `h-mcp-memory` | Recalling or proposing qualified institutional learning |

## Authority Boundary

One active Design session is a manifest-bound package owned by Delivery:

| Package part | Owns |
| --- | --- |
| `intent.md` | Problem, actors, Product Promise, normal workflows, scope, accepted exclusions, preserved behavior, material user decisions, success, assumptions, and technically-done-but-wrong outcomes |
| `design.md` | Current ownership, proposed architecture and interfaces, tradeoffs, weaknesses, migration, proof approach, and decision consequences |
| `authority.json` | Generated Delivery contract bytes; authored revision clears this authority |
| `manifest.json` | Delivery-owned hashes binding the exact package identity |

The Designer never writes these files directly. `create_design_session` creates one new package;
`read_design_session` returns its verified complete bytes and package ID; and
`revise_design_session` compare-and-swap replaces complete intent and design bytes while clearing
generated authority. The Designer may write focused research under `.owlbear/research/` and
diagnostics under `.owlbear/scratch/`. Product files, active package files, target runtime, jobs,
attempts, receipts, and another change are outside this workflow's direct write boundary.

Treat conversation as working context only. Confirmed meaning must be persisted in its owning
artifact before another material branch begins. Never replace confirmed authority merely because a
later session starts with less context.

## Step 1 - Select Or Create One Session

Determine the entry mode from the caller:

- `/ideate <rough idea>` enters discovery. If the input identifies an existing change, call
  `read_design_session(change_id)`. Otherwise derive one stable lowercase hyphenated `change_id`
  and call `create_design_session` once with initial complete intent and design bytes.
- `/design <change_id>` enters design directly. Require the supplied identity and call
  `read_design_session(change_id)`. If the user intends a new named change and the package is absent,
  call `create_design_session` once; otherwise preserve the missing-package diagnostic.

Do not maintain separate ideation and design records or enumerate portfolio state to infer identity.
Both entries resolve to the same `change_id` and active package. Initialize unknown content
explicitly as draft or unresolved; do not invent decisions, evidence, stable contract IDs, or
approval. Retain the returned `package_id` as the only revision token.

## Step 2 - Rehydrate Before Revision

Call `read_design_session(change_id)` and use only its verified intent bytes, design bytes, manifest,
authority bytes, and package ID. Also inspect focused research. Build private session state with:

- confirmed intent and Product Promise;
- accepted exclusions and preserved remainder;
- accepted, pending, and superseded decisions;
- observed, documented, assumed, and user-confirmed claims;
- current architecture, interfaces, migrations, risks, and proof boundaries;
- derived commitments, outcomes, task-plan scopes, ownership, and dependencies when generated
  authority is present;
- compiler, validation, or admission findings that remain unresolved.

Report contradictions instead of silently choosing a newer-looking statement. Preserve confirmed
meaning unless the user explicitly changes it through a material decision. On resume, state the
persisted current position and continue from the earliest unresolved gate; do not replay settled
questions or compute the package identity from manifest bytes.

## Step 3 - Persist Authored Revisions By Compare-And-Swap

Before each authored mutation, form complete replacement `intent_bytes` and `design_bytes` from the
verified package plus the confirmed change. Call `revise_design_session(change_id,
expected_package_id, intent_bytes, design_bytes)` and retain the returned package ID as the next
token. The call clears generated authority, so any checkpoint, derivation, validation, challenge,
baseline, or approval for the prior identity is stale.

If revision reports a stale package identity, call `read_design_session` again, compare the returned
complete bytes with the proposed revision, and reconcile without overwriting another writer. Do not
edit intent, design, authority, or manifest files directly and do not calculate package hashes.

## Step 4 - Discover Intent And Preserve The Product Promise

When discovery is needed, follow `w-idea-refinement` until the intended outcome, beneficiary, normal
workflow, observable result, boundaries, and success are concrete. Persist confirmed understanding
incrementally in `intent.md`.

Maintain a Product Promise ledger in that authority:

- each behavior or effect that makes the change worth using;
- accepted exclusions, including the value each exclusion removes;
- preserved existing behavior and remainder;
- normal-workflow success evidence;
- technically-correct-but-wrong outcomes.

Do not reduce the requested outcome to make delivery easier. An omission from the Product Promise is
accepted only through an explicit user decision persisted in the complete package intent and design.

## Step 5 - Ground Claims And Use Qualified Memory

Investigate repository-answerable facts before asking the user. Load `h-codebase-orientation` and use
the smallest read-only source, history, runtime, or test boundary that can distinguish the claim.
Delegate focused external research, architecture review, interface audit, risk review, or proof
analysis to fresh read-only specialists when their independent context or expertise improves the
evidence.

Classify every load-bearing claim in the authority:

| State | Meaning |
| --- | --- |
| `observed` | Verified in current source, runtime output, generated contract, or test |
| `documented` | Stated by a named controlling repository or external authority |
| `assumed` | Plausible but unverified, with owner and consequence recorded |
| `confirmed` | Explicitly established by the user |

Memory may suggest search terms, prior pitfalls, or candidate constraints. Before using it, load
`h-memory-structure` and `h-mcp-memory`, recall only relevant entries, assess their scope and current
applicability, and corroborate load-bearing claims against current authority or source. Record memory
as supporting provenance, never as execution or specification authority. Propose new institutional
learning only after the design work establishes a specific, non-obvious, reusable fact.

## Step 6 - Resolve One Material Decision

A material decision changes product behavior, Product Promise, scope, architecture, public
interface, migration, compatibility, security, delivery ownership, or proof meaning. Choose the
unresolved decision with the greatest downstream leverage.

Use `askQuestions` for exactly one material decision and then stop for the user's answer. Include:

```markdown
### Decision: <one precise choice>

**Status quo:** <persisted authority and source-grounded evidence>
**Why now:** <what this choice controls or blocks>
**Options:** <two to four genuine choices, each with benefits and costs>
**Tradeoffs:** <consequential differences, including lost Product Promise>
**Risks:** <material failure or irreversibility by option>
**Recommendation:** <one evidence-based choice and expected result>
**Confidence:** <calibrated confidence and remaining uncertainty>
```

Do not bundle a second choice into the prompt. Do not ask for facts discoverable from source. After
the answer, persist the decision and affected intent or design through Step 3, mark superseded
decisions explicitly in authored bytes, and recompute dependent open questions. Ambiguous answers
remain pending and do not authorize downstream admission.

## Step 7 - Review Adaptive Architecture

Once product intent is stable enough to constrain implementation, load `h-module-design` and review
architecture at depth proportional to novelty, coupling, irreversibility, and risk. Persist in
`design.md`:

- current behavioral owners and public interfaces;
- proposed ownership, modules, control flow, and data flow;
- each changed or new interface and its failure semantics;
- migrations, compatibility stance, deletion ownership, and absence proof;
- meaningful alternatives, tradeoffs, weaknesses, and known limits;
- the normal assembled proof boundary and completion conditions.

Take an evidence-based position. Do not invent alternatives when one boundary is clearly adequate,
and do not hide a material weakness to preserve momentum. Any unresolved material architecture fork
returns to Step 5.

## Step 8 - Build Complete Delivery Contract

Encode confirmed intent and design in the compiler-owned target-contract blocks consumed by
`derive_delivery_contract`. Use stable uppercase typed IDs and complete each active semantic
identity before admission:

- provenance-classed commitments for dealbreakers, protected requests, important reviewed meaning,
  agreed paths, and implementation discretion;
- user-facing outcomes with promises, observable acceptance, commitment links, and dependency IDs;
- exactly one outcome task-plan scope for every active outcome;
- persisted Design re-entry briefings, semantic updates, and completion summaries only when they
  already exist as durable authority.

Keep contract source semantic. It does not contain claims, attempts, mutable task prose,
implementation steps, or chat history. Call `derive_delivery_contract(change_id)` and retain the
returned canonical contract bytes and digest. Compiler diagnostics return to the owning intent or
design revision. Present the complete Product Promise, decisions, architecture, commitments,
outcomes, dependencies, known limits, and proof coverage before approval.

## Step 9 - Challenge, Baseline, Checkpoint, And Validate

Run these gates against one unchanged package ID:

1. Call `derive_delivery_contract(change_id)` and require a contract with no compiler diagnostics.
2. Call a fresh read-only designer challenger. Require one source-grounded
  `{disposition, evidence}` entry using `pass`, `warning`, or `error` for the change identity and
  every commitment, outcome, and task-plan scope. Free-form approval is invalid.
3. Run proportionate clean baselines: affected builds or typechecks, generated-contract checks,
   focused tests, and the cheapest existing normal-boundary smoke. Baselines establish starting
   feasibility; they do not prove unimplemented behavior.
4. Call `publish_design_checkpoint(change_id)` and require its returned package ID to equal the
  unchanged current package ID.
5. Call `validate_delivery_contract(change_id)` and require its contract bytes and digest to equal
  the derivation from step 1 with no diagnostics.

An `error` or malformed challenge, failing baseline, package-ID mismatch, derivation mismatch,
compiler diagnostic, or unresolved material authority keeps the package unadmitted. Record and
report the exact finding, repair its owning authority through Step 3, and restart from the earliest
affected step. Do not invoke `admit_delivery_change`, publish target files manually, or weaken
evidence to force a pass.

Warnings must be visible in the complete review and represented in known limits. They do not become
silent assumptions.

## Step 10 - Obtain Explicit Approval And Admit

Ask one final admission question only after the complete candidate and all gate evidence are ready.
The approval covers product intent, accepted exclusions, material decisions, architecture,
commitments, outcomes, planning scopes, and known limits for the displayed digest. The user does not
certify dependency mechanics.

Record approval against the unchanged package ID and derived contract digest. Call
`read_design_session(change_id)` again and proceed only when its package ID and complete authored
bytes match the approved package. Call `validate_delivery_contract(change_id)` again and require the
same canonical contract bytes and digest, then call `admit_delivery_change` with
`DeliveryAdmissionRequest(change_id=change_id, active_claim_ids=())`.

Require the admission result contract bytes and digest to match the approved derivation. Record and
report its persisted receipt ID, contract digest, frontier IDs, checkpoint commit, and carry-forward
result. An identical retry must return `replayed: true` with the same contract, frontier, and receipt.
Active target work blocks a semantic revision.

Admission is also the first remote recovery boundary for the package. Delivery snapshots the
verified `authority.json`, `design.md`, `intent.md`, and `manifest.json` into the managed Change
branch before its initial publication checkpoint. Do not promise remote recovery for unadmitted
draft revisions, and do not revise the admitted package in place; a semantic change requires a new
or superseding Design Change.

If the package changes after checkpoint, validation, or approval, discard pending approval and repeat
challenge, baseline, checkpoint, validation, and approval against the new identity. Admission failure
leaves the active package available for `/design` resume and publishes no partial target authority.

## Session Output

During work, report only the current durable state and the next unresolved gate. After admission,
return:

```markdown
## Design Session

- Change: <change_id>
- Package: <package_id>
- Contract: <contract_digest>
- Product Promise: <complete promised outcome and accepted exclusions>
- Decisions: <accepted and unresolved counts; unresolved must be zero>
- Architecture: <owners, changed interfaces, migrations, and known weaknesses>
- Delivery contract: <commitment and outcome counts, dependency frontier, scope coverage>
- Evidence: <challenge disposition, baseline commands, validation result, known limits>
- Admission: <receipt ID, frontier IDs, checkpoint commit, and carry-forward result>
```

Before admission, replace the final line with `Draft: <blocking finding and owning authority>` and do
not imply that Delivery can begin.

## Known Pitfalls

- **Cross-command handoff:** `/ideate` and `/design` must rehydrate the same target authority.
- **Chat-only choice:** a decision is not durable until a package revision owns it.
- **Fact polling:** inspect repository evidence before asking the user.
- **Question batching:** one material choice per `askQuestions` call.
- **Promise erosion:** require explicit acceptance for every reduction in user-stated value.
- **Memory authority:** corroborate memory; never let it decide current truth.
- **Shallow architecture:** adapt review depth to novelty and risk while preserving interface detail.
- **Partial authority:** each active outcome needs commitments, acceptance, dependencies, and one plan scope.
- **Validator substitution:** challenge, baseline, checkpoint, approval, and deterministic validation are distinct.
- **Stale compare-and-swap:** read and reconcile current complete bytes instead of overwriting another writer.
- **Premature admission:** any unresolved gate keeps the package unadmitted and forbids `admit_delivery_change`.
