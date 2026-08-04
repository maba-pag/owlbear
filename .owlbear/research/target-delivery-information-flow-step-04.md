# Target Delivery Information Flow — Step 4: Ground Claims

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-02
> **Question:** How should Specification obtain trustworthy repository and external facts without a
> monolithic research phase, user fact polling, or transferring semantic authority to researchers?

## 1. Status Quo And Evidence

Current Design guidance tells the Designer to investigate repository-answerable facts, classify
load-bearing claims, and use read-only specialists or durable research when useful. Codebase
orientation uses a smallest-adequate ladder from known source through exact and conceptual search;
discovery results are locators, while direct source and executable behavior are evidence.

Claims arise throughout intent discovery, decisions, architecture, reverse review, and correction.
A single completed research phase would either speculate about later questions or falsely imply that
new claims no longer need grounding.

## 2. Decision D1 — Continuous Grounding With An Orientation Pass

Grounding is a continuous Specification responsibility. Immediately after reviewed intent, perform
one deliberate orientation pass over current owners, workflows, interfaces, constraints, and proof
surfaces relevant to the Product Promise. Later decisions and architecture trigger focused checks
whenever they introduce or depend on a new factual claim.

Designer owns deciding which facts matter and incorporating evidence into Specification. Read-only
specialists may answer bounded questions but do not own a parallel research state or choose product
meaning. Independent intent and architecture critique challenges unsupported claims at their
respective gates. Confidence: high.

## 3. Decision D2 — Necessity-Based Bounded Delegation

Designer investigates directly when the likely owner, source, interface, or cheapest discriminating
check is already known. Delegate one bounded read-only question when the surface is broad or
unfamiliar, independent interpretation could challenge a consequential assumption, or specialist
domain knowledge materially improves the answer.

The specialist receives the exact question, relevant Product Promise or design claim, permitted
scope, expected evidence, and explicit limits. It returns sources, observations, contradictions, and
uncertainty rather than a design decision or synthesized authority. Designer reads decisive source
before relying on the result. Confidence: high.

## 4. Decision D3 — Retain Only Load-Bearing Evidence

Persist evidence only when it materially shapes or constrains intent, a user decision, architecture,
migration, risk, or proof boundary. Preserve the conclusion, evidence class, exact source locator and
checked revision, consequence for Specification, and uncertainty or condition that could make it
stale.

Exploratory searches, rejected candidate locations, routine navigation, and facts cheaply
recoverable from obvious current source remain transient. Create focused durable research only when
the analysis itself has lasting value or depends on multiple or external sources. Independent review
flags unsupported load-bearing claims. Confidence: high.

## 5. Decision D4 — Review Evidence Through Its Claim

Do not add a separate grounding approval gate. The Concept Reviewer verifies the load-bearing
evidence behind complete intent and architecture during those critiques; the Specification
Challenger later verifies that final authority remains grounded. A read-only specialist may
independently investigate a disputed fact, but its result is evidence rather than approval.

This keeps evidence attached to the consequence being judged. Designer rechecks a claim when its
source revision, scope, or applicability changes. Confidence: high.

## 6. Step Boundary

Grounding continues throughout Specification. Its deliberate post-intent pass yields current project
orientation and durable load-bearing evidence; later stages reopen focused investigation whenever a
new consequential claim requires it.

## 7. Decision D5 — Exact Meaning And Explicit Source Contexts

Use four boundaries: exact Current System section for semantic meaning;
`inspect_design_sources(change_id)` for every relevant repository context and reference health;
`search_project_source(source_context_id, ...)` for exact or conceptual location; and
`read_project_source(source_context_id, path, range)` for path-safe exact current or pinned content.
Run focused behavioral probes only in a safe executable root returned by inspection.

Remove `show_design_project_context` and replace `inspect_design_workspace`. The removed projection
has no unique job: semantic claims belong to `design.md`, while staleness and source-state joins
belong to inspection. Explicit context IDs prevent search or reads against an accidental baseline.
Confidence: high.

## 8. Decision D6 — Two Living Authorities, Claim-Local Evidence

Use two authored Specification authorities. `intent.md` owns current Product Promise, workflow,
boundaries, exclusions, success, and user commitments. `design.md` owns current-system facts,
proposed architecture, interfaces, migration, risks, proof, and technical commitments. Remove
`decisions.yaml`; deciding is a conversation operation that updates the owning current meaning.
`authority.json` remains the later machine-readable admission projection.

Commitment strength and evidence status are orthogonal attributes, not artifact categories. Attach
dealbreaker-through-discretion strength to the governing statement. Attach observed, documented,
assumed, or confirmed status, locator, checked source context, consequence, and staleness condition
to a load-bearing factual claim. Cross-artifact uses link to one semantic owner. Focused research
owns durable multi-source analysis, while the governing claim retains its conclusion and consequence.
Add no central evidence ledger. Confidence: high.

## 9. Decision D7 — OwlBear-Owned Source Researcher

Add an owned `source-researcher` ND3 agent with an explicit, replaceable OwlBear model, initially
`Claude Sonnet 5 (copilot)`. Give it source-context inspect/search/read, ordinary file/search/web,
and read-only terminal tools under the deny-write hook. It has no mutation, lifecycle, approval, or
nested-agent authority.

One request supplies a falsifiable question, exact intent or design claim and consequence, permitted
source-context IDs and scope, known evidence or contradictions, expected evidence, stop condition,
and exclusions. Return `supported`, `contradicted`, or `inconclusive`; observations separated from
inference; exact context/revision and locators; checks performed; contradictions; uncertainty and
staleness; evidence limits; and at most one narrower next check. Do not choose product meaning,
recommend architecture, edit authority, approve a claim, or broaden the investigation.

Designer or Planner rereads decisive evidence. Persist only the resulting load-bearing claim or
justified focused research; keep the agent response transient. Unavailable or malformed delegation
falls back to direct investigation. An unestablished load-bearing fact remains assumed with its
consequence or keeps the dependent choice unresolved.

Replace built-in `Explore` wiring in Designer and Planner. Remove it from Orchestrator because a pure
dispatcher does not investigate source. VS Code-defined agents may remain manual development aids
but are not required OwlBear dependencies. Confidence: high.

## 10. Step Completion

Step 4 is decided. Implementation must provide the source-context tools from D5, adopt the two-
authority model from D6, add and wire `source-researcher`, and remove required built-in-agent
dependencies.