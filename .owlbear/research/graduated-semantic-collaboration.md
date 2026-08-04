# Graduated Semantic Collaboration

> **Owning task:** #1968 - Replace the OwlBear delivery pipeline
> **Date:** 2026-08-02
> **Question:** How should user and agent participation change from intent through implementation without creating agent autonomy, user rubber-stamping, or forced-choice ceremony?
> **Status:** Current collaboration model stated by the user and elaborated into layer-specific methods.

## 1. Context and Principle

Semantic work is collaborative, but not uniformly collaborative. The user begins with a goal, need,
or intent. The agent increasingly contributes analysis and synthesis as work becomes more technical.
The user remains involved through consequence-level guidance and review, while the agent and
independent reviewers own progressively more of the detailed completeness and technical proof.

The gradient is:

```text
Intent          Outcomes          Constraints        Acceptance        Strategy          Details
User leads  ->  shared shaping -> agent-led discovery -> agent-led translation -> agent-led design -> agent owns
Agent helps     user validates    user sets priorities user reviews meaning user reviews effects  review/audit
```

This is not a handoff from user authority to agent autonomy. It is a change in collaboration depth
and review abstraction. Later technical work remains bounded by earlier user-guided meaning.

## 2. Sources Studied

| Source | Relevant fact |
|---|---|
| Current user clarification | User participation should be deepest for intent and decrease gradually through outcomes, constraints, acceptance, and strategy. |
| `w-idea-refinement` | Uses one-question evidence-backed refinement but currently leads with a recommended answer. |
| `w-design-session` | Distinguishes intent, architecture, delivery authority, challenge, and approval but uses one material-decision method. |
| `h-ac-quality` | Detailed acceptance quality requires technical boundary, input/output, literal, and proof checks unsuitable for user-only review. |
| Current DN-003 plan | Detailed IDs, closures, commands, and scenario matrices overwhelm consequence-level review. |
| Cockpit graph view | Current projection foregrounds IDs and paths instead of meaning, consequences, and rationale. |

## 3. Collaboration Gradient

| Layer | User contribution | Agent contribution | User-facing review object | Completion gate |
|---|---|---|---|---|
| Intent | Originates goal, pain, beneficiary, priorities, unacceptable outcomes | Elicits, reflects, detects ambiguity, researches facts | Plain-language intent and Product Promise | User says the summary captures what should become true and what must not be lost |
| Outcomes | Judges value, normal workflow, priority, omissions, and accepted exclusions | Proposes observable outcome set, workflow effects, boundaries, and technically-done-but-wrong cases | Outcome map and short workflow stories | User confirms the valuable results, preserved behavior, and exclusions |
| Constraints | Supplies preferences, risk tolerance, operating limits, and consequence priorities | Discovers hard constraints, separates facts from choices, develops viable paths and dependencies | Consequence ledger: what each path enables, replaces, prevents, improves, costs, and risks | User resolves material consequences; agent validates hard technical constraints |
| Acceptance | Reviews whether representative success, failure, and exclusion examples express the intended outcome | Translates outcomes into complete high-level and detailed scenarios, traceability, negative cases, and proof strategy | Acceptance storyboard plus expandable detailed criteria | User confirms behavioral meaning and material edge priorities; agent review proves detailed completeness and testability |
| Implementation strategy | Guides priorities such as simplicity, disruption, reversibility, performance, maintenance, and delivery risk | Designs architecture, ownership, packet strategy, migration, proof, and technical tradeoffs | Architecture and delivery narrative focused on effects, irreversible choices, and important tradeoffs | User confirms consequence-level fit; independent agents validate technical coherence and detailed feasibility |
| Implementation details | Corrects newly exposed product consequences; otherwise no routine action | Chooses code structure, algorithms, schemas, commands, fixtures, and local repairs within the reviewed strategy | Optional drill-down and final observable result | Agent review, tests, acceptance, and audit pass; new material consequences return to the owning layer |

## 4. Layer-Specific Methods

### 4.1 Intent: reflective clarification

The agent asks about meaning, not solutions. It restates what appears valuable, names ambiguity, and
investigates repository facts instead of polling the user. Alternatives appear only when the user's
intent genuinely admits materially different interpretations.

The user reviews a short statement of desired change, beneficiary, normal use, preserved value, and
technically-done-but-wrong outcomes. No graph, schema, or architecture is needed at this layer.

### 4.2 Outcomes: scenario shaping

The agent turns intent into observable stories: who can do what, through which normal workflow, and
what becomes easier or reliably true. It surfaces omitted actors, failure behavior, and exclusions.

The dialogue asks whether the proposed result is useful and complete. The user edits value and
priority; the agent supplies structure, completeness checks, and repository grounding. Outcome IDs
and ownership mappings are generated after meaning is understood.

### 4.3 Constraints: consequence dialogue

The agent classifies constraints before discussion:

- **hard fact:** imposed by source, platform, law, or accepted compatibility; agent verifies it;
- **preference:** supplied by the user and preserved unless explicitly changed;
- **material tradeoff:** viable paths differ in user-visible effect, risk, cost, reversibility, or
  operating burden; discuss with the user;
- **engineering constraint:** affects implementation but not reviewed consequences; agent owns it.

For a material tradeoff, explain viable paths in consequence language:

```text
We can do X. That lets A take over B and makes C stronger, but D cannot be preserved and E becomes
more expensive. Or we can do S. That keeps T and makes V much better, but U will not work and W
remains manual. The unresolved question is which consequence better matches your intent.
```

Do not start with “Do you want X? It is recommended.” Do not pad the comparison with a knowingly
inferior foil. The question concerns consequences and priorities, not solution labels.

### 4.4 Acceptance: storyboard plus technical contract

The agent first presents representative success, failure, boundary, and exclusion examples in the
user's workflow language. The user checks whether these examples mean the right thing and identifies
important edge priorities.

The agent then owns the detailed scenario matrix, obligation mapping, literal verification, proof
boundary, and testability analysis. Independent review checks completeness and non-weakening. The
user may inspect detailed criteria, but meaningful review never depends on auditing the full matrix.

### 4.5 Strategy: consequence-level architecture review

The agent develops implementation strategy from the reviewed intent, outcomes, constraints, and
acceptance. It explains architecture through ownership and effects:

- what component or phase takes responsibility from what;
- what becomes simpler, safer, faster, or more expensive;
- what cannot coexist with the strategy;
- what is irreversible or difficult to migrate;
- what the user will experience differently; and
- where technical uncertainty remains.

The user reviews this abstraction and steers priorities. Agent reviewers inspect module boundaries,
interfaces, dependencies, files, schemas, commands, and proof mechanics. A large technical appendix
does not substitute for an understandable strategy narrative.

### 4.6 Details: delegated execution inside reviewed bounds

Builders choose detailed implementation without presenting routine choices to the user. They return
to collaboration when evidence exposes a new outcome, material constraint, acceptance meaning,
irreversible strategy change, or loss of promised value. Otherwise, review and validation remain
agent- and code-owned.

## 5. Enabled Review

User review is meaningful only when the user can understand the decision surface. Before requesting
review, the agent provides:

1. the current goal or reviewed parent meaning;
2. what is newly proposed or changed;
3. why the question exists now;
4. what each viable path enables and improves;
5. what each path replaces, prevents, weakens, or makes impossible;
6. material cost, risk, uncertainty, and reversibility;
7. the agent's technical assessment after the consequence comparison; and
8. one precise request for correction, priority, or confirmation at the layer's abstraction level.

The review surface uses progressive disclosure:

| View | Primary audience | Content |
|---|---|---|
| Meaning | User and agent | Intent, outcomes, consequence summaries, workflow examples, exclusions |
| Semantic contract | User when useful; planning and review agents | Constraints, acceptance, architecture, delivery outcomes, rationale |
| Technical trace | Builders, reviewers, acceptors, auditors | IDs, interfaces, paths, closures, commands, evidence, receipts |

The user can inspect the technical trace, but approval does not require reconstructing meaning from it.

## 6. Routing and Depth Rules

Increase user-dialogue depth when a proposal has greater effect on value, workflow, compatibility,
irreversibility, operating burden, risk, or uncertainty. Increase agent autonomy when a choice is
local, reversible, technically compelled, and invisible at reviewed semantic boundaries.

Ask the user only when their priorities distinguish viable consequences. Investigate facts directly.
Do not ask for confirmation of a document merely because it exists. Review is required when the
semantic meaning changed or reached a layer-completion gate.

One conversation may revisit an earlier layer when later evidence changes its consequences. That is
not planning failure; silently absorbing the change at a technical layer is.

## 7. Workflow Integration

- Specification persists the confirmed intent and outcome summaries, material consequence choices,
  high-level acceptance, and consequence-level strategy.
- Detailed constraints, acceptance, architecture, and proof remain durable semantic authority, but
  Cockpit presents their enabled-review projections first.
- Planning uses reviewed constraints and strategy, then presents packet consequences and acceptance
  deltas at the appropriate abstraction before publication.
- Build, acceptance, and audit operate autonomously inside reviewed meaning and return only material
  semantic changes to collaboration.
- Decision records distinguish user-originated priorities, collaboratively resolved consequences,
  delegated engineering judgment, and generated mechanics.

## 8. Completion Checks

- [ ] Each semantic layer names a different user action, agent action, review object, and gate.
- [ ] Later layers increase agent responsibility without erasing user-guided parent meaning.
- [ ] Material alternatives are explained through comparable consequences before recommendation.
- [ ] User review can succeed from high-level abstractions without reading technical traces.
- [ ] Detailed acceptance and strategy remain available for inspection and agent review.
- [ ] Routine engineering details do not create user ceremony.
- [ ] New material consequences route back to the layer that owns their meaning.

## 9. Recommendation, Confidence, And Limits

**Recommendation:** Use this graduated model as the collaboration contract for the redesign. Replace
generic “user approval” and “agent-driven” language with the layer-specific methods and gates above.

**Confidence:** High in the gradient and review-abstraction principles because they directly reflect
the user's clarification. Medium in exact UI and persistence fields until the model is exercised on
an ordinary feature and DN-003.

**Limits:** This model defines collaboration responsibilities and review depth. It does not yet choose
the final plan schema, Cockpit layout, review budget, or acceptance-storage model.