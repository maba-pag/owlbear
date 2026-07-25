---
name: w-design-session
description: "Workflow: Create or resume one native change session and admit only a complete approved delivery revision"
user-invocable: false
---

# Native Design Session

Turn a rough idea or a named change into one durable OwlBear change authority. Preserve confirmed
intent and decisions across interruptions, resolve one material choice at a time, and admit only a
complete revision that passes validation, independent challenge, baseline, and explicit approval.

This workflow owns Specification. It does not implement product code, create Delivery jobs directly,
or turn conversation history into a second authority.

## Companion Skills

Load these with `read_file` immediately before the named work:

| Skill | Load when |
|-------|-----------|
| `w-idea-refinement` | `/ideate` input is too rough to state the intended outcome and Product Promise |
| `h-codebase-orientation` | Locating current owners, interfaces, tests, and normal workflows |
| `w-research` | A material external or repository claim needs durable source-grounded research |
| `h-module-design` | Reviewing proposed ownership, interfaces, locality, or dependency placement |
| `h-memory-structure` and `h-mcp-memory` | Recalling or proposing qualified institutional learning |

## Authority Boundary

One session is rooted at `.owlbear/changes/<change_id>/` and has four semantic authority parts:

| Authority | Owns |
|-----------|------|
| `intent.md` | Problem, actors, Product Promise, normal workflows, scope, accepted exclusions, preserved behavior, success, assumptions, and technically-done-but-wrong outcomes |
| `design.md` | Current ownership, proposed architecture and interfaces, tradeoffs, weaknesses, migration, and proof approach |
| `decisions.yaml` | Material user choices, status, options, tradeoffs, risks, recommendation, confidence, rationale, and decision authority |
| `delivery/{obligations,contracts,nodes}.yaml` | Stable obligations, workflows, modules, interfaces, migrations, risks, proofs, delivery nodes, dependencies, and ownership |

The designer may also write focused research under `.owlbear/research/` and diagnostics under
`.owlbear/scratch/`. Jobs, plans, receipts, tracked product files, Kanban records, and authority for
another change are outside this workflow's write boundary.

Treat conversation as working context only. Confirmed meaning must be persisted in its owning
artifact before another material branch begins. Never replace confirmed authority merely because a
later session starts with less context.

## Step 1 - Select Or Create One Session

Determine the entry mode from the caller:

- `/ideate <rough idea>` enters discovery. Use `list_changes` to find an existing matching change.
  Select it when the user identifies it or the identity is unambiguous; otherwise derive one stable
  lowercase hyphenated `change_id` and create its native authority package.
- `/design [change_id]` enters design directly. Use the supplied identity or `list_changes` to select
  one unambiguous existing change. If no matching session exists, create the named native authority
  package rather than handing off to another planning system.

Do not maintain separate ideation and design records. Both entries resolve to the same `change_id`
and authority root. If multiple existing changes plausibly match, ask one identity-selection
question and stop.

For a new package, create only the semantic authority files above using the current native schemas.
Initialize unknown content explicitly as draft or unresolved; do not invent decisions, evidence,
entity IDs, or approval. Runtime directories and artifacts are engine-owned.

## Step 2 - Rehydrate Before Writing

For an existing session, call `show_change(change_id)` and read all four authority parts before any
mutation. Also inspect focused research referenced by the authority. Build a private session state
with:

- confirmed intent and Product Promise;
- accepted exclusions and preserved remainder;
- accepted, pending, and superseded decisions;
- observed, documented, assumed, and user-confirmed claims;
- current architecture, interfaces, migrations, risks, and proof boundaries;
- declared delivery entities, ownership, and dependencies;
- validation or admission findings that remain unresolved.

Report contradictions instead of silently choosing a newer-looking statement. Preserve every
confirmed item unless the user explicitly changes it through a material decision. On resume, state
the persisted current position and continue from the earliest unresolved gate; do not replay settled
questions.

## Step 3 - Discover Intent And Preserve The Product Promise

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
accepted only through an explicit user decision recorded in `decisions.yaml`.

## Step 4 - Ground Claims And Use Qualified Memory

Investigate repository-answerable facts before asking the user. Load `h-codebase-orientation` and use
the smallest read-only source, history, runtime, or test boundary that can distinguish the claim.
Delegate focused external research, architecture review, interface audit, risk review, or proof
analysis to fresh read-only specialists when their independent context or expertise improves the
evidence.

Classify every load-bearing claim in the authority:

| State | Meaning |
|-------|---------|
| `observed` | Verified in current source, runtime output, generated contract, or test |
| `documented` | Stated by a named controlling repository or external authority |
| `assumed` | Plausible but unverified, with owner and consequence recorded |
| `confirmed` | Explicitly established by the user |

Memory may suggest search terms, prior pitfalls, or candidate constraints. Before using it, load
`h-memory-structure` and `h-mcp-memory`, recall only relevant entries, assess their scope and current
applicability, and corroborate load-bearing claims against current authority or source. Record memory
as supporting provenance, never as execution or specification authority. Propose new institutional
learning only after the design work establishes a specific, non-obvious, reusable fact.

## Step 5 - Resolve One Material Decision

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
the answer, write the decision to `decisions.yaml`, update affected intent or design authority, mark
superseded decisions explicitly, and recompute dependent open questions. Ambiguous answers remain
pending and do not authorize downstream admission.

## Step 6 - Review Adaptive Architecture

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

## Step 7 - Build Complete Delivery Authority

Translate confirmed intent and design into the three modular delivery files. Use stable typed IDs and
assign every active item before admission:

- requirements, negative requirements, and preserved behaviors;
- normal workflows and user-visible failure behavior;
- modules and changed interfaces;
- ordered migrations and deletion proofs;
- material risks and mitigations;
- durable proofs at real assembled boundaries;
- outcome-cohesive delivery nodes, dependency edges, and exactly one accountable owner or explicit
  support path for each obligation.

Keep delivery authority declarative. Nodes describe outcomes and contract ownership, not mutable
claims, attempts, task prose, implementation steps, or chat history. Present the complete Product
Promise, decisions, architecture, delivery graph, known limits, and proof coverage to the user before
requesting approval.

## Step 8 - Challenge, Baseline, And Validate

Run these gates against the same immutable candidate revision and digest:

1. Call `show_change(change_id)` and capture the current semantic digest.
2. Call a fresh read-only designer challenger. Require one source-grounded
   `{disposition, evidence}` entry using `pass`, `warning`, or `error` for every declared requirement,
   workflow, interface, migration, risk, proof, and node. Free-form approval is invalid.
3. Run proportionate clean baselines: affected builds or typechecks, generated-contract checks,
   focused tests, and the cheapest existing normal-boundary smoke. Baselines establish starting
   feasibility; they do not prove unimplemented behavior.
4. Assemble `AdmissionEvidence` for exactly that digest with structured challenge, baseline,
   approval, and non-empty known limits.
5. Call `validate_change(change_id, evidence)`.

A non-pass challenge, failing baseline, digest mismatch, deterministic validation error, unresolved
material authority, or missing approval keeps the candidate draft. Record and report the exact
finding, repair its owning authority, and restart from the earliest affected step. Do not invoke
`admit_change`, publish jobs manually, or weaken evidence to force a pass.

Warnings must be visible in the complete review and represented in known limits. They do not become
silent assumptions.

## Step 9 - Obtain Explicit Approval And Admit

Ask one final admission question only after the complete candidate and all gate evidence are ready.
The approval covers product intent, accepted exclusions, material decisions, architecture, delivery
node boundaries, and known limits for the displayed digest. The user does not certify graph
mechanics.

Record approval against that digest, rebuild `AdmissionEvidence`, and call `validate_change` again.
Proceed only when the returned assessment is admitted and still names the current digest. Then call
`admit_change(change_id, evidence)` with the identical evidence.

Record and report the persisted admission receipt ID, delivery digest, generation identity, and
initial plan-job identities returned by the public tool. An identical retry must return the persisted
artifacts; it must not create another generation or job set.

If authority changes after validation or approval, the digest is stale: discard the pending approval,
keep the revision draft, and repeat challenge, baseline, validation, and approval. Admission failure
always leaves the authority available for `/design` resume and creates no jobs.

## Session Output

During work, report only the current durable state and the next unresolved gate. After admission,
return:

```markdown
## Design Session

- Change: <change_id>
- Revision: <delivery_digest>
- Product Promise: <complete promised outcome and accepted exclusions>
- Decisions: <accepted and unresolved counts; unresolved must be zero>
- Architecture: <owners, changed interfaces, migrations, and known weaknesses>
- Delivery graph: <node count, dependency frontier, obligation and proof coverage>
- Evidence: <challenge disposition, baseline commands, validation result, known limits>
- Admission: <receipt ID, generation ID, and initial plan-job IDs>
```

Before admission, replace the final line with `Draft: <blocking finding and owning authority>` and do
not imply that Delivery can begin.

## Known Pitfalls

- **Cross-command handoff:** `/ideate` and `/design` must rehydrate the same native authority.
- **Chat-only choice:** a decision is not durable until `decisions.yaml` owns it.
- **Fact polling:** inspect repository evidence before asking the user.
- **Question batching:** one material choice per `askQuestions` call.
- **Promise erosion:** require explicit acceptance for every reduction in user-stated value.
- **Memory authority:** corroborate memory; never let it decide current truth.
- **Shallow architecture:** adapt review depth to novelty and risk while preserving interface detail.
- **Partial graph:** every active obligation and boundary needs delivery ownership and proof.
- **Validator substitution:** challenge, baseline, approval, and deterministic validation are distinct.
- **Premature admission:** any unresolved gate keeps the draft and forbids `admit_change`.
