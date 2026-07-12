# Spec-Driven Development Framework Comparison

> **Date:** 2026-07-11
> **Question:** Which specification and broader SDD patterns should OwlBear adopt, integrate, or avoid?
> **Scope:** Specification quality first; lifecycle, tooling, orchestration, traceability, and verification second.

## Evaluation Criteria

1. Product and user-outcome clarity
2. Brownfield architecture and interface fit
3. External-contract and evidence grounding
4. Decision and uncertainty handling
5. Spec-to-task traceability and invariant ownership
6. Normal-path acceptance and verification
7. Change, migration, and completion semantics
8. Tooling, extensibility, and adoption cost
9. Multi-agent workflow fit
10. Risk of ceremony, lock-in, or false confidence

## Sources

| Repository | URL | Resolved Commit | Status |
|------------|-----|-----------------|--------|
| OpenSpec | https://github.com/Fission-AI/OpenSpec | `0a99f410457271aa773d8b106f03f637f7c6b3c0` | analyzed |
| gsd-core | https://github.com/open-gsd/gsd-core | `30feeaa8be86b71616dd7d47bbd157d4ee0d2736` | analyzed |
| spec-kit | https://github.com/github/spec-kit | `1be42992e64b08ff0dce3d7a914eaabf04284ffb` | analyzed |
| wallfacer | https://github.com/changkun/wallfacer | `fa6616e82d20901fc4e666a333da006113732bad` | analyzed |
| comet | https://github.com/rpamis/comet | `a2b804d575bc99574b245fd52b45fa42016a130c` | analyzed |

## Per-Repository Findings

### OpenSpec

**Observed:** OpenSpec models a change as proposal, requirement deltas, optional design, and tasks.
`schemas/spec-driven/schema.yaml` declares this as an artifact DAG; `src/core/artifact-graph/types.ts`
validates artifact dependencies. Requirement deltas use `ADDED`, `MODIFIED`, `REMOVED`, and
`RENAMED`, with normative requirements and `WHEN`/`THEN` scenarios. Removal requires reason and
migration. Project context and per-artifact rules are injected through `openspec/config.yaml`; a
custom version-controlled schema can replace the default. `docs/agent-contract.md` specifies one
JSON document on stdout, structured diagnostics, stable exit behavior, and command-specific null
shapes.

**Good elements to retain:**

- Delta-first requirements for brownfield changes instead of rewriting a complete system spec.
- Declarative artifact graph with custom schemas and project-level context injection.
- Explicit new/modified/removed capability inventory before detailed specs.
- Machine-readable diagnostic envelope: severity, code, message, target, fix.
- Apply/archive separation and immutable historical change directories.

**Cautions:** The default spec template is deliberately too thin for OwlBear's PRD-quality gate;
it needs a custom schema. OpenSpec tasks overlap OwlBear Kanban and must not become a second task
authority. Delta archive/parallel-change semantics are an active complexity area, visible in
`openspec/changes/add-change-stacking-awareness/` and related work. Telemetry is enabled unless
disabled. Node 20.19+ becomes an additional runtime dependency.

**Fit:** Integrate experimentally as an optional specification backend with an OwlBear-specific
schema; do not adopt its apply/task execution layer. Confidence: 0.86.

### GSD Core

**Observed:** GSD uses a deep Discuss, Plan, Execute, Verify, Ship lifecycle with filesystem state in
`.planning/`. `gsd-core/templates/spec.md` forces Current, Target, and Acceptance for each
requirement, explicit boundaries, constraints, edge coverage, must-NOT prohibitions, an ambiguity
report, and interview log. `gsd-core/templates/requirements.md` gives stable requirement IDs and a
requirement-to-phase coverage table. `gsd-core/templates/VALIDATION.md` maps task, wave,
requirement, threat, test type, command, and status. Fresh-context specialists and wave execution
are documented in `docs/explanation/multi-agent-orchestration.md` and
`docs/explanation/context-engineering.md`.

**Good elements to retain:**

- Current, Target, Acceptance triplets for brownfield requirements.
- Stable requirement IDs and explicit unmapped-requirement count.
- Negative requirements and edge-coverage disposition, not only happy-path AC.
- Validation map established before execution, with feedback latency and manual-only proof named.
- Fresh-context subagents, thin orchestration, wave summaries, and persistent verification state.
- Stale verification as a first-class state when implementation changes after proof.

**Cautions:** The template set and state model are large; adopting them wholesale would duplicate
OwlBear ideation, Kanban, agents, verification, and memory. Numeric ambiguity scores are
model-judged rather than formal proof and can create false precision. The full process is excessive
for narrow work and its many artifacts increase synchronization cost.

**Fit:** Borrow the requirement, prohibition, traceability, and validation-map patterns; do not
integrate the runtime. Confidence: 0.91.

### GitHub Spec Kit

**Observed:** Spec Kit separates constitution, specify, clarify, plan, checklist, tasks, analyze,
implement, and converge. `templates/spec-template.md` starts with prioritized, independently
testable user journeys, Given/When/Then scenarios, edge cases, functional requirement IDs,
measurable success criteria, and explicit assumptions. `templates/commands/clarify.md` scans a
broad ambiguity taxonomy, ranks questions by impact times uncertainty, asks at most five questions
one at a time, and writes answers into the spec immediately. `templates/commands/analyze.md`
non-destructively checks requirement coverage, contradictions, terminology, constitution
alignment, and unmapped tasks. `templates/tasks-template.md` groups tasks by user story so each
slice remains independently demonstrable.

**Good elements to retain:**

- Prioritized user journeys with an independent-test statement before functional requirements.
- A bounded clarification pass driven by materiality, not an unrestricted interview.
- Separate measurable outcomes, assumptions, entities, failures, and edge cases.
- Read-only cross-artifact analysis with coverage metrics and stable finding IDs.
- Project constitution as explicit authority and post-build convergence back to the spec.
- Integration registry and layered presets/extensions as mature multi-tool design examples.

**Cautions:** Default task templates are implementation- and file-oriented and can encourage the
same microtask fragmentation OwlBear is correcting. The complete framework is broad and would
replace rather than complement much of OwlBear. Requirements, plan, tasks, checklists, extensions,
presets, workflows, and hooks create substantial ceremony and multiple synchronization surfaces.

**Fit:** Borrow spec, clarify, and analyze patterns natively; do not adopt the full runtime or task
format. Confidence: 0.94.

### Wallfacer

**Observed:** Wallfacer keeps specs in `specs/` with typed frontmatter, dependencies, affected code
areas, effort, and linked task identity. `internal/spec/lifecycle.go` enforces
vague, drafted, validated, testing, complete, stale, and archived; validated cannot jump directly
to complete. Its roadmap in `specs/README.md` distinguishes complete, in-progress, not-started,
stale, and archived work and records where implementation deliberately shipped smaller than the
original spec. `specs/local/agent-graph-e2e-design.md` is a strong brownfield design example: it
documents current execution reality, disproves an intended convergence path with a spike, updates
the target, names teardown, migration, and compatibility steps, and gates code on acceptance.

**Good elements to retain:**

- Explicit spec lifecycle including stale and testing states.
- Dependency and affected-area metadata connected to implementation drift.
- Drift checking after implementation and stale propagation to dependents.
- Honest current-reality sections that distinguish shipped, dormant, experimental, and intended.
- Forward-only undo through git revert and atomic spec-to-task dispatch linking.
- Unified spec/task dependency graph as a future Cockpit visualization pattern.

**Cautions:** Drift checking and agentic execution remain experimental in important paths. The
system is a full local engineering control plane, overlapping OwlBear Kanban, Cockpit, agents,
worktrees, event history, and verification. Adopting it wholesale would be a product replacement.
Some verdict parsing depends on strict model output and can strand state.

**Fit:** Borrow lifecycle, drift, reality-audit, and graph concepts; do not integrate the runtime.
Confidence: 0.89.

### Comet

**Observed:** Comet composes OpenSpec for WHAT with Superpowers for HOW and adds a typed phase/state
runtime. `domains/comet-classic/classic-state.ts` separates user-settable and machine-owned state;
`classic-transitions.ts`, `classic-guard.ts`, and `classic-validate-command.ts` separate transition,
guard, and validation concerns. `classic-evidence.ts` returns evidence codes with satisfied,
source, and detail. Runtime state, append-only trajectories, checkpoints, hashes, and recovery are
separate artifacts. `assets/skills/comet/SKILL.md` defines explicit user decision points and small
hotfix/tweak/full profiles.

**Good elements to retain:**

- Typed user state separate from machine runtime state and append-only event history.
- Evidence codes decoupled from evidence source paths.
- Pure transition guards before side effects and explicit phase recovery.
- Workflow profiles selected by qualitative risk, with file count only as a tripwire.
- Mandatory user decision points that automatic phase transitions cannot bypass.
- Snapshot/hash linkage for reproducible resume and stale handoff detection.

**Cautions:** Many evidence checks establish file existence or checked boxes, not semantic quality;
presence must not be confused with proof. Comet combines two external frameworks plus its own state
machine, creating high operational and conceptual coupling. The core skill is large, state fields
are numerous, and recovery correctness depends on synchronized generated runtime assets.

**Fit:** Borrow typed evidence, transition, recovery, and profile-selection patterns. Do not adopt
the combined framework. Confidence: 0.90.

## Cross-Repository Synthesis

| Criterion | OpenSpec | GSD | Spec Kit | Wallfacer | Comet |
|-----------|----------|-----|----------|------------|-------|
| Best contribution | Delta specs | Traceability and validation maps | Spec/clarify/analyze | Lifecycle and drift | Typed guards and evidence |
| Brownfield fit | Strong | Strong but heavy | Moderate-strong | Strong | Strong but coupled |
| Spec quality default | Thin | Very high | High | Free-form/variable | Delegated to OpenSpec |
| OwlBear overlap | Medium | Very high | High | Very high | Very high |
| Component integration value | High | Medium | High | Medium | Medium-high |
| Wholesale adoption fit | Low | Low | Low | Very low | Very low |

The repositories converge on five principles: specs are versioned artifacts; ambiguity is resolved
before tasking; requirements remain traceable into proof; lifecycle state must distinguish planned,
implemented, verified, stale, and archived; and deterministic tooling should validate structure
while semantic approval remains agent/human work.

### OwlBear Current-State Delta Audit

The comparison must distinguish useful external confirmation from missing OwlBear capability.

| External Pattern | OwlBear Current Capability | Actual Delta |
|------------------|----------------------------|--------------|
| Bounded interactive clarification | `w-task-decomposition` Brief Readiness Gate and one-at-a-time user decision gate | Add a reusable ambiguity taxonomy only if repeated shaping sessions miss the same categories |
| User outcome and independently testable journey | `h-ideation` Expectation Signal plus readiness requirement for concrete invocation | Optionally make journey priority/independent-test fields explicit in a future Brief template |
| Current / Target / Acceptance | Product promise, brownfield source read, task AC, and Product Invariant Map | A compact requirement-level form could improve large Briefs; not needed for every task |
| Must-NOT and edge coverage | “Technically done but wrong,” explicit non-goals, B4 boundary proof, and AC | A structured negative-requirement table is still missing for high-risk features |
| Requirement-to-task traceability | Product Invariant Map gives invariant, owner, boundary, and proof | Stable requirement IDs and an automated unmapped count are still missing |
| Validation map | Invariant map, Proof Guidance, named authorities, Verify Notes, SHA-linked aggregate proof | One inspectable requirement-to-command matrix is still missing for large aggregate work |
| Typed evidence | Kanban AC, proof guidance, Verify Notes, and shared evidence rules | Evidence is prose; structured fields such as code, source, boundary, tested SHA, and result are not modeled |
| Spec lifecycle and stale propagation | Brief authority plus task lifecycle; verification can reject stale tests | No persistent spec state or dependency-driven stale propagation exists |
| Delta requirements | Brief and decisions preserve current direction and trade-offs | No canonical requirement-delta store exists; current need is unproven |
| Cross-artifact analysis | Shaper-challenger checks concrete task layout and fidelity | No deterministic coverage report or stable finding IDs exist |

Most external patterns confirm the direction already implemented in this change. The genuine gaps
are narrower: stable requirement identifiers for large Briefs, negative requirement coverage,
deterministic unmapped-requirement analysis, structured evidence metadata, and eventually stale
verification semantics if OwlBear gains a persistent spec graph.

### Authority Model

OwlBear keeps one specification authority:

1. `brief.md` is the approved product promise.
2. `decisions.md` may explicitly amend or supersede Brief decisions.
3. Kanban AC is a traceable implementation projection, not an independent product specification.
4. Shape Notes record authorities, invariant ownership, and proof without becoming another spec.

No OpenSpec delta file, GSD phase spec, Spec Kit feature spec, Wallfacer spec node, or Comet state
file is introduced as a parallel authority. If a future need for reusable requirement deltas is
observed, OwlBear should first define reconciliation and ownership semantics, then reconsider an
external backend or a native format.

## Reassessment: Replacement Value Versus Preservation Bias

The first recommendation overweighted compatibility with OwlBear's current architecture. Measured
directly, the custom pre-build framework contains 11 ideation agents, about 2,025 lines of ideation
skills and agent definitions, 18 possible blackboard artifact types, and roughly 845 additional
lines of shaper, challenger, decomposition, and AC machinery. That is a framework, not thin glue.

The BitSight alert incident is the only strong end-to-end outcome evidence available. Despite
multiple panels, Critic loops, expectation-fidelity checks, twelve shaped tasks, builder and
verifier challengers, and aggregate collection, the result failed through the production command
path and encoded invented external contracts. The custom machinery therefore has not demonstrated
outcome quality proportional to its human, model, and maintenance cost.

The actual valuable OwlBear-specific outcomes are smaller:

1. Preserve the promised outcome and identify the version that is technically done but wrong.
2. Ground brownfield architecture and external contracts in named authorities.
3. Map implementation work to normal-path proof and run it through Kanban build/verify/collect.
4. Record material user decisions and block rather than guess.

### Replacement Fitness

| Criterion | Spec Kit | OpenSpec | GSD | Wallfacer | Comet |
|-----------|----------|----------|-----|------------|-------|
| Intent and user-outcome specification | Strong | Moderate | Strong | Variable | Delegated to OpenSpec |
| Bounded clarification | Strong, explicit command | Explore/update but less systematic | Strong, interview-heavy | Chat-driven | Strong decision points |
| Architecture and implementation planning | Strong plan/research/contracts phases | Moderate optional design | Very strong but heavy | Strong design records | Strong via Superpowers |
| Brownfield grounding | Strong when plan is customized | Strong delta-first model | Strong mapper/onboarding | Strong code-grounded specs | Strong but layered |
| Pre-build consistency analysis | Strong built-in analyze | Structural validation | Strong checkers | Lifecycle/drift | Guards/evidence, less semantic |
| Human/model effort | Moderate and reducible with presets | Low | High | High | High |
| Customization without fork | Strong presets/extensions | Strong custom schemas | Limited relative to size | Requires product modification | Skill/bundle customization |
| Copilot fit | Native skills or agent/prompt generation | Native generated commands | Supported command ecosystem | External harness model | Multi-platform skills |
| Execution overlap with OwlBear | Moderate; implement can be omitted | Moderate; apply can be omitted | Very high | Near-total | Very high |
| Migration bridge difficulty | Moderate | Moderate | High | Very high | High |
| Actual OwlBear value lost | Expectation-fidelity wording and mandatory panels | Architecture/clarification depth | Little, but replaces execution too | Little, but replaces product | Little, but creates layered runtime |

Spec Kit is the best replacement because it covers the missing structure while allowing OwlBear to
retain its execution system. OpenSpec is simpler but would require more custom clarification and
technical-planning behavior. GSD is arguably stronger end to end, but adopting it while retaining
OwlBear execution produces two orchestration systems; replacing OwlBear execution with GSD is a
larger product decision than the specification problem requires. Wallfacer and Comet are complete
engineering control planes, not specification components.

Spec Kit can own the rest: specification structure, bounded clarification, architecture/research,
contracts, task derivation, cross-artifact analysis, and convergence. Its preset system supports
project-local template and command replacement; its extension system supports hooks and scripts;
its Copilot integration generates either skills or agent/prompt pairs. It uses Python 3.11+ and can
be pinned in OwlBear's `uv` toolchain.

## Adoption Options

### Option A — Replace Ideation and Shaping with Spec Kit

**Approach:** Spec Kit owns constitution, specification, clarification, technical planning,
contracts, tasks, and analysis. OwlBear retains Kanban build/verify/collect, MCP, memory, decision
requests, and a deterministic Spec Kit-to-Kanban importer. One small OwlBear preset replaces the
default spec, plan, and task templates where needed.

**Pros:** Deletes most custom pre-build orchestration; mature upstream templates and tooling;
bounded user interaction; native Copilot support; project-local customization without a fork;
clear phases for intent, architecture, implementation planning, and consistency analysis.

**Cons:** Requires a real importer, not a prompt-only bridge; the default task template must be
replaced because it is too file-oriented; upstream version pinning and upgrade tests become part of
maintenance.

**Risks:** Preset drift after Spec Kit upgrades, accidental reintroduction of a second task
authority, and loss of useful expectation-fidelity language if migration is careless. Mitigate with
one authority chain, pinned versions, fixture-based importer tests, and no OwlBear task generation
outside the importer.

**Confidence:** Medium-high. Spec Kit demonstrably covers the structural workflow; importer and
preset fit require a pilot before destructive removal.

### Option B — Restructure OwlBear In Place

**Approach:** Collapse panels and phase agents into a smaller native workflow while retaining
OwlBear Briefs, shaping, and custom task generation.

**Pros:** Full control, no upstream workflow dependency, easier compatibility with current Kanban
task model.

**Cons:** Continues owning a specification framework; requires redesigning and testing phases,
templates, clarification, architecture analysis, task generation, and consistency checks already
available upstream.

**Risks:** Sunk-cost preservation, continued prompt growth, and gradual ceremony accumulation. The
recent safeguards improve correctness but increase the already-large custom surface.

**Confidence:** High that this costs more over time than a Spec Kit replacement.

### Option C — Adopt a Full External SDD and Execution Framework

**Approach:** Replace OwlBear ideation/shaping or the full pipeline with OpenSpec, GSD, Spec Kit,
Wallfacer, or Comet.

**Pros:** Mature templates and tooling arrive together; less local framework design in the short
term.

**Cons:** Every candidate overlaps core OwlBear capabilities. GSD, Wallfacer, and Comet replace the
execution/control plane; Spec Kit replaces artifact and task workflow; OpenSpec is narrower but
still duplicates change/task authority.

**Risks:** Migration loss, duplicated state, tool lock-in, and abandoning OwlBear-specific Kanban,
memory, MCP, and agent governance strengths.

**Confidence:** High that GSD, Wallfacer, and Comet replace too much actual OwlBear execution value.
OpenSpec is lighter but weaker than Spec Kit at clarification and architecture planning.

## Recommendation

Choose **Option A: replace OwlBear ideation and shaping with customized Spec Kit**. Validate the
replacement by using it on one genuinely rough, not-yet-specified product idea. The input must state
the user's problem and desired outcome without naming the command, API operation, module design,
task split, or proof strategy that the specification process is supposed to discover.

### Target Workflow

**Trivial path:** bug fixes, renames, docs, and narrow config changes enter Kanban `build` directly
with concrete AC. They do not invoke Spec Kit or a planning agent.

**Feature path:**

1. `constitution` — project-wide principles and non-negotiable engineering constraints, created
   once and amended explicitly.
2. `specify` — intent, prioritized user journeys, measurable outcomes, boundaries, assumptions,
   preserved remainder, and technically-done-but-wrong cases.
3. `clarify` — up to five material questions, one at a time, written directly into the spec.
4. Human spec approval gate.
5. `plan` — brownfield current state, architecture, contract authorities, research decisions,
   data/interface contracts, migration, and normal-path validation guide.
6. Human plan approval gate.
7. `tasks` — outcome-cohesive work mapped to requirements, dependencies, AC, and proof boundaries
   using an OwlBear replacement template and command.
8. `analyze` — read-only consistency and coverage check across spec, plan, and tasks.
9. `owlbear-handoff` — deterministic importer creates Kanban leaves and one aggregate parent.
10. OwlBear `build -> verify -> collect`, followed by Spec Kit convergence against code where useful.

### Single Authority Chain

`constitution -> spec.md -> plan/research/contracts -> tasks.md -> Kanban projection -> evidence`

Kanban is an execution projection. A decision request that changes intent must update the relevant
Spec Kit artifact before re-import. No OwlBear Brief or Shape Notes remains as a competing product
specification for new work.

### Minimal OwlBear Customization

- One Spec Kit preset replacing or wrapping the spec, plan, and tasks templates/commands.
- One deterministic Python handoff command that validates and imports structured tasks into Kanban
  idempotently, preserving requirement IDs, dependencies, AC, proof boundary, and aggregate intent.
- Existing builder, verifier, collector, challengers, decision requests, MCP servers, memory, and
  Kanban execution.

Do not reproduce the panel system in Spec Kit. Expectation fidelity is retained as explicit spec
fields and analysis rules; contract authority and normal-boundary proof are retained in plan/task
fields. Independent subagents remain available for targeted research or verification, but they are
not a mandatory topology.

### First Deliverable: Shape One Rough BiRRe Product Idea

The alert-repair statement is not a valid test input because it already embeds the intended command,
generated operation, data model direction, output semantics, and proof boundary. A builder could act
on it directly. It may later test planning or Kanban import, but it cannot test intent extraction.

The first replacement use therefore starts only after the user provides one real rough idea in this
form:

> I have this problem or repeated work: {plain-language problem}. I want BiRRe to help me reach
> {plain-language outcome}. I have not decided the interface or implementation.

The input should be one short paragraph. It must not be rewritten into requirements before Spec Kit
receives it.

Existing OwlBear Briefs, decisions, and the alert-workflow root-cause analysis are evaluation
references, not input context. The implementing agent does not feed them to Spec Kit and does not
allow the generated commands to treat `.owlbear/briefs/` as feature requirements. Brownfield source
code and normal project instructions remain available because discovering existing-system fit is
part of the work.

#### Work Performed by the Implementing Agent

1. Pin Spec Kit `v0.12.0` and invoke it through:

  ```text
  uv tool run --from git+https://github.com/github/spec-kit.git@v0.12.0 specify
  ```

  No global install and no OwlBear runtime dependency are required for this first deliverable.
2. Create `share/spec-kit/owlbear/` with:
  - a preset manifest;
  - OwlBear spec, plan, and task template overrides;
  - command overrides only where the template cannot express the required behavior;
  - a deterministic `owlbear-handoff` Python command and tests.
3. Initialize Spec Kit in the target workspace in Copilot skills mode and install the local OwlBear
  preset.
4. Pass the user's rough paragraph unchanged to Spec Kit. Do not pre-populate product decisions,
  command names, API operations, architecture, task boundaries, or proof choices.
5. Prepare a short `clarification-answers.md` next to the feature spec containing:
  - the expected Spec Kit clarification question;
  - the recommended answer derived from existing evidence;
  - the source artifact supporting that answer.
6. Generate and inspect `spec.md`, `plan.md`, `research.md`, interface contracts, `quickstart.md`, and
  `tasks.md`.
7. Run Spec Kit analysis and repair critical/high findings before handoff.
8. Run the deterministic importer in dry-run mode, inspect the exact proposed Kanban tasks, then
  import only after the task graph is coherent.

#### User Work

The user provides the rough idea and performs one interactive Spec Kit run in VS Code. For each
question, the user may paste the full chat back to the implementing agent. The implementing agent
may research the codebase and external facts, explain the decision, and recommend an answer, but it
must not answer a product-preference question from hidden historical artifacts. The user confirms
material product choices.

The user then answers one final question: does the generated specification and technical plan match
the intended BiRRe repair? If no, the implementing agent corrects the preset or artifacts and the
same deliverable continues. No scoring rubric or repeated trial is required.

#### Required Output

- A pinned, reproducible Spec Kit invocation.
- OwlBear preset and deterministic importer with tests.
- One Spec Kit feature directory containing the authoritative spec, plan, research, contracts,
  validation guide, tasks, and analysis result.
- One prepared clarification-answer sheet grounded in the existing BiRRe artifacts.
- One dry-run importer report and, after approval, one Kanban aggregate with dependency-linked leaves.
- A short replacement report listing what Spec Kit handled well, what required OwlBear
  customization, and what would block removal of the old workflow.

#### Pass / Fail

The first deliverable passes when:

- the user confirms the resulting spec describes the outcome they meant from the rough paragraph;
- the specification adds necessary detail without silently choosing material product preferences;
- the technical plan derives its interface and architecture from repository evidence rather than
  from hints embedded in the initial prompt;
- Spec Kit analysis has no unresolved critical or high findings;
- every approved requirement maps to one imported task or aggregate criterion;
- cross-boundary invariants have one owner and proof through the actual boundary;
- no Kanban task requires the builder to invent product, architecture, or external-contract choices.

It fails when any of those statements is false after one correction pass. Failure means stop and
identify the concrete missing capability. It does not mean adding another permanent planning layer.

#### Decision After the Deliverable

- If it passes, remove OwlBear ideation and shaping and make Spec Kit the only feature-specification
  path.
- If it fails because of a bounded preset or importer defect, fix that defect and finish the same
  deliverable.
- If it fails because Spec Kit cannot represent or maintain the intended outcome without rebuilding
  OwlBear's orchestration, do not adopt it; redesign the replacement decision from that concrete
  limitation.

**Recommendation confidence:** Medium-high. Replacement has a bounded proof path and much lower
expected maintenance cost. The main uncertainty is deterministic Kanban import quality, not Spec
Kit's specification capability.

## 2026-07-12 Reassessment: Proportional Tool Selection

The prior reassessment optimized for enforceable interview structure and therefore selected GSD
Explore. That was the wrong objective. GSD's complete lifecycle is designed for sustained project
planning: project context, requirements, roadmaps, phase specifications, discussion context, and
execution artifacts. Even using only its Explore command imports the conventions and routing of
that larger system. This is disproportionate for weekend projects and minor work changes.

The actual problem is narrower: prevent an agent from drafting a plausible specification before
it has reached shared understanding with the user and checked repository-answerable facts.

### Cost-First Comparison

| Option | Dialogue | Required output | Setup and coupling | Appropriate use |
| --- | --- | --- | --- | --- |
| Matt Pocock `grill-me` | One decision at a time; recommendation with every question; repository facts researched instead of asked | None | One tiny skill; no project state | Default clarification for ambiguous small and medium work |
| OpenSpec `opsx:explore` | Adaptive, code-aware conversation; deliberately no fixed sequence | None | OpenSpec CLI and generated skill | Open-ended investigation and option comparison |
| `grill-me` then OpenSpec | Explicit shared-understanding gate, followed by user-triggered proposal | Zero during discovery; four change-local artifacts on the default full path | Two composable commands; OpenSpec is the sole artifact authority | Best feature path |
| Matt Pocock `grill-with-docs` | Same grilling loop plus active domain modeling | `CONTEXT.md` and ADR updates when decisions emerge | Requires domain-document conventions and setup | Repeated domain terminology or durable architecture decisions only |
| GSD | Strong interviews within a complete planning lifecycle | Multiple project and phase artifacts | Highest process and state coupling | Large, sustained, coordinated programs |
| Spec Kit `specify` + `clarify` | Draft first, clarify later | Full feature spec before dialogue completes | Moderate runtime and template coupling | Downstream artifact tooling, not discovery |

### Source Findings

Matt Pocock's current `grilling` skill is the missing interaction contract in a few lines:

- ask one question at a time and wait for the answer;
- provide a recommended answer for every question;
- research codebase facts instead of asking the user;
- leave decisions to the user; and
- do not enact the plan until the user confirms shared understanding.

It creates no files and has no duration or question-count floor. Its cost therefore scales with the
actual ambiguity. `grill-with-docs` composes the same loop with domain modeling, while `to-spec`
explicitly performs no interview and synthesizes the existing conversation. That separation is
cleaner than a specification command trying to discover and draft simultaneously.

OpenSpec remains the closest artifact system to the desired scale. Its default core profile is an
action-oriented `explore -> propose -> apply -> sync -> archive` loop. Explore is explicitly a
conversation with no mandatory output. The default specification schema does define proposal,
delta specs, design, and tasks for its full implementation path, so OpenSpec is not free of
ceremony. Its expanded workflow can create them incrementally, but the default schema ultimately
requires all four before `apply`. The advantage is that discovery remains artifact-free and the
artifacts are change-local and iterative. This is still substantially smaller than GSD or the
customized Spec Kit replacement.

OpenSpec Explore alone does not guarantee a thorough interview because it intentionally has no
fixed steps. That is a feature for casual investigation but a weakness when a rough idea must be
made specification-ready. Composing it with `grill-me` is unnecessary: use OpenSpec Explore for
investigation, and use `grill-me` when decision-tree closure is required.

### BiRRe Discriminating Case

The generated BiRRe spec demonstrates exactly why the two concerns must be separate. A grilling
session should not ask the user to define historical-boundary semantics for
`/v1/companies/trends`. Whether the endpoint returns observations, precomputed period changes, or
another structure is a repository/external-contract fact to investigate. Until that fact is known,
the only product decision is that BiRRe should expose source-faithful structured extraction. The
current spec's comparison rule and fallback semantics are inventions caused by drafting too early.

### Decision

Adopt this proportional path:

1. **Trivial or already-clear work:** work directly; no discovery or specification framework.
2. **Ambiguous work of any size:** run `grill-me`; create no artifacts during the interview.
3. **Open-ended technical investigation:** use OpenSpec Explore; switch to `grill-me` if material
   user decisions emerge.
4. **Feature worth preserving as a change contract:** after explicit shared-understanding
  confirmation, enter OpenSpec's four-artifact change path, preferably incrementally.
5. **Durable domain or architecture knowledge:** use `grill-with-docs` selectively, never by
   default.

OpenSpec should replace Spec Kit as the candidate specification/change system. `grill-me` should
replace both Spec Kit `specify` and GSD Explore as the intent-extraction interaction. Do not adopt
GSD, do not reproduce its artifact lifecycle, and do not build a custom multi-agent discovery
system.

The next validation is one real BiRRe run: start from the original rough paragraph, use
`grill-me`, investigate the trends contract rather than asking the user to invent it, obtain the
user's shared-understanding confirmation, then create an OpenSpec proposal. Judge the resulting
change contract directly; do not add process metrics.

**Confidence:** High on the proportional workflow and rejection of GSD for this use case;
medium-high on OpenSpec as the artifact system pending one real proposal run.
