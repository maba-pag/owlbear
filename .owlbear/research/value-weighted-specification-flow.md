# Value-Weighted Specification Flow

> **Date:** 2026-07-12
> **Question:** What should the real idea-to-delivery flow preserve, and which artifacts earn a
> permanent place?

## 1. Principle

Documentation value is not proportional to document count or process effort. Preserve information
that future work needs to answer one of these questions:

1. What outcome are we trying to create now?
2. Why did we choose this behavior or boundary?
3. What facts and contract evidence constrain us?
4. How should the system realize the outcome?
5. What must be delivered and how will its quality be proved?

Do not preserve raw deliberation merely because it occurred. Critic opinions, duplicate summaries,
interview transcripts, rejected wording, and process narration are transient inputs. Promote only
their useful conclusions into an authoritative artifact.

## 2. Recommended Artifact Set

All files live in one change directory. The names below describe responsibilities; they can be
implemented as an OpenSpec custom schema without adopting its default templates.

| Artifact | Authority | Durable content | Excluded content |
| --- | --- | --- | --- |
| `brief.md` | Current product intent | Problem, intended outcome, primary workflow, scope, non-goals, requirements, success conditions, technically-done-but-wrong cases, preserved remainder, open decisions | Architecture, task decomposition, interview transcript |
| `decisions.md` | Decision provenance | Material user choices, evidence-driven conclusions, alternatives, rationale, date, status, supersession links | Every question asked, critic opinions, routine implementation choices |
| `evidence.md` or focused `research/*.md` | External and brownfield facts | Observed current behavior, source contracts, experiments, contradictions, confidence and unknowns | Product preferences disguised as facts, copied documentation without relevance |
| `design.md` | Current technical realization | Existing-system fit, architecture, interfaces, data contracts, authorities, risks, migration/removal, rejected technical alternatives | Product rationale already owned by the Brief, file-by-file task lists |
| `delivery.md` | Delivery and proof contract | Outcome-cohesive deliverables, dependencies, requirement ownership, quality attributes, normal-boundary proof, completion conditions | Microtasks, speculative future work, repeated architecture prose |

`evidence.md` is conditional. A small feature with no external or uncertain contract should cite
repository evidence directly in `design.md`. Separate research is justified when the evidence is
large, reusable, contradictory, or likely to matter to later changes.

## 3. Real Flow

### Step 0: Route by uncertainty

- Clear, narrow work goes directly to implementation with concise acceptance criteria.
- Ambiguous work starts with `grill-me`.
- A factual or architectural unknown may use OpenSpec Explore or targeted research before the next
  user decision.

No artifact is mandatory merely because work began.

### Step 1: Reach shared understanding

Run the grilling interaction one decision at a time:

- inspect the repository instead of asking the user for discoverable facts;
- state the status quo and the actual decision;
- give a recommended answer with trade-offs;
- let the user decide product preferences; and
- stop when both sides agree that the intended outcome and meaningful boundaries are understood.

The conversation itself is scratch state. Material choices are recorded in `decisions.md`; the
agreed synthesis becomes `brief.md`.

### Step 2: Write the living Brief

The Brief is the first durable result, not an immutable contract. It is the current best product
truth and may change whenever research, design, or implementation reveals better information.

A useful Brief answers:

- who is trying to accomplish what;
- the normal user-visible workflow and result;
- what belongs in this change and what remains outside it;
- observable requirements and completion conditions;
- plausible outcomes that would be technically complete but product-wrong; and
- unresolved product decisions or assumptions.

Approval means “good enough to design,” not “frozen forever.” Git preserves prior versions.

### Step 3: Establish evidence before inventing contracts

Investigate current code, generated interfaces, external APIs, and production behavior wherever
they control feasibility or semantics. Classify claims as observed, documented, assumed, or
decided.

Evidence can revise the Brief. For the BiRRe trends example, the endpoint response shape must be
observed before defining historical-boundary calculations or fallback semantics. Those are not
user questions until the source contract proves that a product choice actually remains.

### Step 4: Design from intent and evidence

Create a rough architecture only after the outcome is understood and the controlling facts are
known well enough. “Rough” means decision-complete at important boundaries, not a speculative box
diagram.

The design should identify:

- the existing owning surfaces and what changes;
- external and generated contract authorities;
- interfaces and data flow across real boundaries;
- architecture decisions and rejected alternatives;
- migration, replacement, or removal;
- risks and unresolved technical questions; and
- where integrated behavior can be proved.

Design work may expose a product misunderstanding. When it does, return to the Brief, record a
material decision, and then update downstream artifacts. This is normal iteration, not failure.

### Step 5: Define deliverables and qualities

Translate the Brief and design into a small set of outcome-cohesive deliverables. Each deliverable
owns a meaningful result across the necessary layers, not one file or one implementation step.

For each deliverable record:

- outcome and requirements owned;
- dependencies and named contract authorities;
- acceptance behavior;
- required quality attributes, such as fidelity, safety, completeness, determinism, performance,
  or usability;
- proof through the normal assembled boundary;
- allowed lower-level replacements in tests; and
- completion or removal conditions.

Only after this artifact is coherent should work be projected into Kanban. Kanban remains execution
state; it does not become a second product specification.

### Step 6: Build, learn, and keep artifacts coherent

Implementation may reveal contradictions. Update the owning artifact first:

- changed outcome or scope -> `brief.md` plus a material decision;
- changed fact or contract -> evidence artifact;
- changed technical approach -> `design.md`, with a decision when consequential;
- changed slice or proof -> `delivery.md`.

Then update dependent artifacts and tasks. OpenSpec's `update` action is useful here because it can
propagate a revision across planning artifacts rather than treating specification as a one-way
phase gate.

### Step 7: Close without deleting knowledge

At completion, retain the change directory as historical context. The final Brief records the
delivered intent, decisions explain material choices and supersessions, evidence remains reusable,
and design records the architecture actually built. Delivery records what was proved.

Discard or omit critic transcripts and intermediate drafts once their useful content has been
promoted. Git history is enough for ordinary wording evolution; it is not a substitute for a
decision record when future engineers need the rationale.

## 4. Change Semantics

The artifact chain is directional but iterative:

```text
conversation
    -> brief.md <-> decisions.md
         |
         v
   evidence/research
         |
         v
      design.md
         |
         v
     delivery.md
         |
         v
   Kanban -> code -> proof
```

Earlier artifacts may change at any time. A material upstream change makes downstream conclusions
suspect until reviewed. Do not add immutability, hashes, or formal stale-state machinery before a
real coordination need appears; version control plus an explicit update pass is adequate now.

## 5. Fit with Existing Tools

| Tool | Retain | Replace or avoid |
| --- | --- | --- |
| Matt Pocock skills | `grill-me` interaction; optional `grill-with-docs` when domain language or ADRs genuinely matter | Default domain-doc setup for every small change |
| OpenSpec | Change directories, custom artifact graph, Explore, incremental creation, update, archive | Default proposal/spec/design/task templates if they duplicate this authority model |
| OwlBear | Brief quality, decision records, technically-done-but-wrong, preserved remainder, Kanban execution and proof | Mandatory critic panels and retained critic output |
| Spec Kit | No required runtime role; selected template ideas may be copied | Draft-before-dialogue entry flow and parallel specification authority |
| GSD | No default role for this project class | Full project/phase artifact lifecycle |

## 6. Recommendation

Use a small OpenSpec custom schema whose durable chain is:

`brief -> design -> delivery`, with `decisions.md` as a continuously maintained sidecar and focused
research added only when evidence warrants it.

Precede Brief creation with `grill-me`. Preserve the best OwlBear Brief fields and decision format.
Use OpenSpec for artifact creation, update, dependency guidance, and archive. Import only
`delivery.md` into Kanban.

**Confidence:** High on the information boundaries; medium-high on OpenSpec custom-schema fit until
one real BiRRe change exercises creation, revision after new evidence, delivery projection, and
archive.

**Sources:** BiRRe alert Briefs and decisions; OpenSpec `0a99f410457271aa773d8b106f03f637f7c6b3c0`; Matt Pocock's `skills` repository; and the broader local SDD comparison.
