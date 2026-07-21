# Planning Workflow Root Cause and Redesign

> **Owning task:** User-directed planning-workflow forensic audit
> **Date:** 2026-07-13
> **Question:** Why did approved OpenSpec changes produce incomplete execution graphs, and how must OwlBear redesign idea-to-build planning so omitted known work cannot recur this badly?
> **Status:** Recommended problem and design authority; remove OpenSpec and prove the native implementation contract before rollout

## 1. Context and Question

Four concurrent changes reached Kanban with plausible proposals, specs, designs, and approved task graphs, yet later verification or collection discovered work that the original graphs should have contained. This was not one weak task or one agent mistake. The workflow repeatedly converted convincing prose into executable status without proving that the graph could assemble and demonstrate the promised product behavior.

This document preserves the incident evidence, root causes, healthy behavior, governing principles, target capabilities, admission contract, implementation order, regression cases, open architecture decisions, and success criteria. Subsequent changes to ideation, specification storage, shaping, task decomposition, verification, or collection MUST cite this document and state which numbered requirements they satisfy, defer, or supersede. A later approved design may replace recommendations here only by recording the conflicting evidence and explicit supersession.

This is intentionally more detailed than a normal research note. The failure crossed the complete planning pipeline, and compressing it to a short recommendation would discard the causal evidence needed to prevent superficial fixes. Concision remains valuable, but not when it erases why a control exists, what existing behavior it must preserve, or which decision is still open.

The target is not zero verifier rejection. Healthy verification must still catch implementation defects. The target is **zero late graph expansion caused by work, interfaces, migrations, or proof infrastructure that were knowable during shaping**.

## 2. Sources Studied

| Evidence | Scope | Material finding |
| --- | --- | --- |
| Four active changes under `openspec/changes/` | Browser acquisition, workspace health, memory purge, memory lifecycle | All passed document-oriented planning yet required omitted work after execution began |
| Kanban histories `#1917-#1926`, `#1937-#1960`, `#1966`, `#1967` | Original graphs, failures, repairs, aggregate outcomes | Local leaves could pass while the assembled product path remained unowned or unproved |
| Workflow remediations `#1927`, `#1928`, `#1964` | Added maps, proof guidance, decomposition constraints | Better prose and traceability help, but do not deterministically reject an invalid graph |
| `/ideate`, `/shape`, shaper and challenger definitions | Intent extraction and graph approval | Chat authority is lost; semantic review anchors on generated tasks and lacks an admission mechanism |
| OpenSpec propose skill, project config, setup, and OpenSpec 1.6 behavior | Artifact generation and readiness | Stock `spec-driven` completes proposal through tasks and equates artifact completion with apply readiness |
| `setup/openspec.py` and generated integration surface | Installation, configuration, schema policy, and operational cost | OwlBear pins and globally installs OpenSpec, generates skills/prompts, removes its former custom schema, and currently receives stock artifact orchestration rather than unique quality enforcement |
| Shaping and ideation contract tests | Current workflow safeguards | Tests mostly assert required wording and order, not rejection of defective real graphs |
| `sdd-framework-comparison.md` | External framework evidence | OpenSpec supports project-local custom artifact DAGs and configurable `apply.requires` |
| `value-weighted-specification-flow.md` | Prior OwlBear authority analysis | Durable artifacts should preserve intent, evidence, design, delivery, and proof without duplicating Kanban |

No new external source was introduced; OpenSpec provenance is already recorded in `.owlbear/sources/overview.md`.

## 3. Analysis

### 3.1 Executive Verdict

The current pipeline optimizes for **convincing documents, approved decomposition, and locally passing leaves**, not for **executable product coherence**. `/ideate` produces transient intent, `/opsx:propose` creates every planning layer in one pass and declares readiness, and `/shape` reviews an already-suggested graph. No machine-enforced boundary proves requirement coverage, interface-edge ownership, migration completeness, or executable aggregate proof before build.

The failures are therefore systemic. Builders and verifiers exposed them, but did not cause them. User approval confirmed product direction and understandable presentation; it could not substitute for technical graph validation. Adding more instructions without changing admission semantics will repeat the pattern.

### 3.2 Incident Record

| Change | What the original graph missed | Discovery point | Required late expansion |
| --- | --- | --- | --- |
| Complete browser content acquisition | Authentication lifecycle and retained-page ownership across acquisition composition | `#1920` failed during implementation | `#1925` repaired lifecycle composition; `#1926` added assembled proof |
| Redesign workspace health | Final cleanup API deletion; the real transport, repair, shell, and mutation-callback path; complete destructive safety semantics | Build/verify loops; `#1944` remains unresolved and aggregate `#1945` cannot close | `#1959` added final deletion; repair semantics were revised repeatedly |
| Purge deleted memories | Any executable path crossing MemoryTab -> FastAPI -> MemoryEngine | Collector rejected individually passing `#1946-#1950` | Build-owned harness/proof `#1966` |
| Expose memory lifecycle in Cockpit | Executable aggregate proof owner and a complete frontend API seven-state/resolve contract | Aggregate `#1958`, then clean-checkout work in `#1960` | `#1960` exposed 20 TypeScript errors; corrective contract task `#1967` |

The common signature is decisive: **the graph expanded after local work passed because integration obligations had no original owner**.

### 3.3 Detailed Failure Mechanisms

#### F1. The idea authority disappears

`/ideate` ends with a chat-only Refined Idea Summary and explicitly creates no handoff artifact. The original confirmed idea therefore cannot be mechanically compared with the later planning package. The pipeline cannot prove whether proposal generation preserved an outcome, silently narrowed the Product Promise, promoted an assumption into a decision, or still solves the initiating problem. A planning pipeline whose first authority evaporates cannot provide end-to-end traceability.

#### F2. `/opsx:propose` manufactures false confidence

The command creates proposal, specs, design, and tasks in one pass. Repository grounding is an instruction inside generation, not a required evidence input or separately admitted stage. “Strict OpenSpec validation passed” sounds like plan validation, but the observed validator did not detect missing module ownership, broken dependencies, non-executable completion proof, unsafe repair semantics, a missing client contract, or a committed frontend that did not compile. It validates artifact structure and normative formatting, not technical completeness or delivery coherence.

#### F3. Advisory tasks anchor shaping

OpenSpec tasks are formally advisory, but `/shape` receives a polished decomposition after intent, requirements, and design were generated in the same context. The shaper is then biased toward merging, splitting, or repairing those suggested nodes instead of independently deriving obligations from source, interfaces, migration, and the normal user journey. This creates duplicate planning authority without genuinely independent analysis.

#### F4. Coverage maps verify nodes, not edges

Product Promise, module, and invariant maps can assign each named outcome to a task while omitting the interfaces between tasks. Memory lifecycle had backend contract ownership, frontend UI ownership, and resolve-interaction ownership, but no owner for the TypeScript client joining them. Workspace health named state ownership while omitting the transport and callback chain. Browser acquisition split authenticated-page ownership from the consumer that needed the page to remain alive. The plans covered boxes but not arrows.

#### F5. Aggregate completion was not executable

Several graphs assigned assembled completion to collect parents even though completion required writing a harness, starting a production server, constructing fixture stores, running real MCP operations, driving a browser, or recording evidence at a committed SHA. Collectors can audit such evidence; they cannot create missing production wiring or proof infrastructure. Memory purge proved MemoryTab, FastAPI, and MemoryEngine separately, then needed `#1966` after collector rejection because no executable path crossed all three.

#### F6. Proof became delayed architecture discovery

`#1960` was intended to prove a finished product. Instead it discovered that the committed application did not compile and that the required frontend client contract had never been delivered. Proof should falsify behavior and expose implementation defects. It should not be the first stage to discover an entire missing production owner or module that the design implied.

#### F7. Module maps were narrower than acceptance

Workspace-health task `#1943` mapped the state hook and provider while its acceptance required repair-result merging, receipt retention and dismissal, mutation-triggered refresh, and stale-response ordering through real callers. The transport, repair hook, panel, Shell, and mutation callbacks were omitted, leaving the new methods unreachable through production flow. A map that does not cover the full acceptance surface creates a misleading completeness signal.

#### F8. AC line limits did not control complexity

A task with three AC lines can hide many state combinations and failure cases. The destructive Kanban repair task fit its numerical budget while omitting no-overwrite destination safety, concurrent destination appearance, and complete-set classification before mutation. Those defects could cause data loss and required two verifier rejections. Text length is a useful readability tripwire, not a risk model.

#### F9. User approval was misused as technical certification

The user should approve outcomes, exclusions, trade-offs, consequential architecture choices, and material graph boundaries. The user cannot reasonably certify that a detailed task graph includes each callback, generated type, migration step, lifecycle owner, and proof harness. Presenting a polished graph does not transfer technical completeness responsibility from the planning system to the user.

#### F10. Operational failures produced prose rather than controls

Tasks `#1927`, `#1928`, and `#1964` added staged review, challenge, repair re-entry, mapping, and proof guidance. These are useful improvements. Their tests, however, primarily assert that required sentences appear in Markdown and in the prescribed order. They do not run a shaping scenario, inspect a structured plan, or prove that an invalid graph is rejected before board mutation. The response made the manual stronger without making the boundary enforceable.

### 3.4 Root-Cause Hierarchy

**Primary root cause:** OwlBear has no authoritative, machine-admitted execution contract between design and Kanban. “Ready” is a narrative judgment attached to document completion.

**Enabling causes:**

- Product intent, architecture, task graph, and proof ownership do not have explicit handoff contracts.
- The stock OpenSpec schema makes tasks the terminal prerequisite even though OwlBear Kanban is the execution authority.
- Shape combines semantic review, decomposition, approval, and board mutation without an independent compiler output and admission result.
- Coverage is represented as task membership, not a graph of requirements, interfaces, migrations, risks, and proofs.
- Aggregate proof is treated as a final check instead of build-owned infrastructure planned with the feature.
- Test suites validate instruction text rather than exercising defective planning fixtures end to end.

**Incentive cause:** the pipeline rewards visible forward motion: artifacts exist, the user approved, tasks moved, leaves passed. Late discovery is repaired as another task, masking that the planning system admitted an incomplete program.

### 3.5 What Is Healthy and Must Be Preserved

The incidents do not justify replacing the pipeline wholesale or encoding every recent defect into permanent ceremony. The following capabilities are already valuable and MUST survive the redesign:

| Healthy capability | Why it matters | Preserve without overfitting |
| --- | --- | --- |
| One-question interactive ideation | Separates product preference from discoverable repository facts and prevents uncontrolled question dumps | Persist the accepted synthesis; do not preserve the whole transcript by default |
| Full Product Promise and preserved remainder | Resists silent scope reduction and “small first slice” reinterpretation | Keep active outcomes and accepted exclusions traceable into delivery |
| Technically-done-but-wrong examples | Captures product failure modes ordinary happy-path AC misses | Keep as intent constraints, not a fixed taxonomy of the four incidents |
| Explicit material user decisions | Correctly reserves product, scope, compatibility, and consequential trade-offs for the user | Do not ask the user to validate mechanical graph completeness |
| Repository and contract grounding | Prevents invented symbols, aliases, schemas, and external behavior | Keep authority ranking and observed/documented/assumed distinctions |
| Staged implementation review | Gives the user an understandable product, architecture, and completion review | Retain adaptive depth; do not turn it into artifact recital |
| Product Promise, module, and invariant maps | Exposes named ownership and normal proof better than unstructured task lists | Generate compatible views from one structured model and add edge coverage |
| Outcome-cohesive decomposition | Avoids file-level task fragmentation and final “wire it together” tasks | Keep domain/failure/proof boundaries as heuristics, not blind hard counts |
| Boundary-valid AC | Prevents mocks from replacing the public path whose behavior is claimed | Retain semantic AC review and canonical literal checks |
| Shaper challenger | Supplies adversarial semantic review that deterministic checks cannot replace | Give it inspectable structured rows and run it after mechanical validation |
| Repair re-entry | Correctly distinguishes local repair from material product or architecture change | Preserve earliest-affected-stage routing and renewed approval for material changes |
| Independent builder/verifier/collector roles | The observed verifier rejections caught real defects: secret leakage, selector confusion, unsafe replacement, missing boundary tests, and incomplete UI behavior | Keep independent falsification; clarify that collectors audit rather than construct missing proof |
| Kanban lifecycle and history | Provides execution state, dependencies, ownership, rejection history, and durable evidence | Keep Kanban as the sole execution-state authority |
| Proportional narrow-work shortcut | Not every bug fix needs a multi-artifact planning process | Route by uncertainty, interface count, risk, migration, and proof needs |

The redesign MUST NOT preserve chat-only authority, all-at-once synthesis as readiness, user approval as technical certification, collector-owned proof construction, duplicate task authorities, or tests that only search workflow files for prescribed sentences.

The four incidents are a regression floor, not the ontology of future planning. New controls SHOULD model general concepts such as authority, requirement, interface, state transition, migration, risk, ownership, dependency, and proof. They SHOULD NOT add special-case fields for browsers, memory, workspace health, or the exact modules that failed here.

### 3.6 Governing Design Principles

**P1. Durable intent before synthesis.** The approved Product Intent is a versioned artifact and every downstream requirement is traceable to it.

**P2. Design before decomposition.** Repository-grounded interfaces, authorities, data flow, lifecycle, migration, destructive semantics, and proof boundaries are decided before tasks are generated.

**P3. Derive, do not repair.** Shape derives obligations from intent and design without treating generated tasks as an authoritative starting graph.

**P4. Edges are first-class.** Coverage includes producer, consumer, contract, owner, failure semantics, and proof for every changed interface edge.

**P5. Proof is build work.** Harnesses, fixtures, assembled paths, and clean-checkout build requirements have build-capable owners and precede aggregate verification.

**P6. Admission is layered.** Build cannot start until a structured plan passes deterministic consistency checks, repository-grounded semantic challenge, proportionate executable baselines, and the required user decisions. No one layer claims completeness it cannot prove.

**P7. One authority per concern.** One durable change package owns intent, behavior, design, and delivery projection; Kanban alone owns execution state. The storage/tool implementation is an open decision, and no second task list competes with Kanban.

**P8. Revision is normal and visible.** Material discoveries update the owning upstream artifact, invalidate affected downstream admission, and are not hidden in follow-up tasks.

### 3.7 Target Workflow

1. **`/ideate` -> Product Intent.** Interview one material decision at a time; inspect discoverable facts; write problem, actors, normal workflow, outcomes, scope, non-goals, success, wrong-but-plausible outcomes, preserved remainder, assumptions, and open decisions. Approval means ready for design.
2. **`/design` -> Implementation Contract.** Ground the intent in current code and source contracts. Define normative behavior, owning modules, interfaces, state/data flow, authority, lifecycle, migration/removal, safety, risks, and normal assembled proof boundary. Unresolved material questions return upstream.
3. **`/shape` -> Execution Plan.** Compile intent, behavior, and design obligations into outcome-cohesive work, dependencies, interface ownership, migration order, proof infrastructure, verification, and collection. Run layered admission, semantic challenge, then user approval of material decisions and graph shape before Kanban mutation.
4. **Build/verify/collect.** Builders create product and planned proof infrastructure; verifiers falsify task claims; collectors audit admitted aggregate evidence. Any material plan expansion invalidates admission and returns to shape.

Stock `/opsx:propose` MUST leave the trusted OwlBear path because its all-at-once generation and “Ready for implementation” claim conflict with P1-P6. Whether the command remains available outside that path is a later product decision; “quick lane” must not become a euphemism for bypassing proportionate admission.

### 3.8 Decision: Remove OpenSpec

OpenSpec was selected as a lightweight artifact backend with medium-high confidence pending a real proposal run. The four audited changes are that experiment, and the result is negative. OwlBear supplies the substantive quality model: ideation, Product Promise, decision handling, repository grounding, staged review, task decomposition, AC quality, challenger behavior, Kanban projection, verification, and collection. OpenSpec contributes change directories, templates, artifact ordering/status, delta-spec conventions, structural CLI validation, generated commands, and archive/update concepts.

Those contributions do not justify the operational and conceptual cost: a pinned global npm dependency, generated skills and prompts, setup and upgrade code, stock schema semantics that conflict with OwlBear, advisory tasks that duplicate planning authority, an apply/readiness vocabulary OwlBear does not use, and the demonstrated risk that structural validation is mistaken for technical validation. `setup/openspec.py` currently removes OwlBear's former custom schema and configures stock `spec-driven`; building another custom schema would reverse that simplification while retaining the same external machinery.

The evaluated options were:

| Option | What it retains | Main benefit | Main cost/risk |
| --- | --- | --- | --- |
| **O1: Keep OpenSpec with a custom OwlBear schema** | CLI, change directories, artifact DAG, delta specs, status/update/archive | Reuses an external artifact engine and standard change layout | Rejected: retains dependency and vocabulary mismatch while OwlBear owns the meaningful semantics and validation |
| **O2: Replace OpenSpec with a native OwlBear change package** | Versioned Markdown/YAML under one change directory, Git history, native validator | Selected: one authority and exact fit; removes generated command and setup coupling | OwlBear must own a small lifecycle, path-resolution, validation, and archive surface |
| **O3: Use Kanban plus a minimal pre-build artifact set** | Durable intent/design/delivery files linked from aggregate work | Smallest mechanism and least new infrastructure | Rejected: overloads execution state and weakens change-level history, revision, and requirement traceability |

The decision follows these criteria:

- information fidelity across idea, design, execution, revision, and closure;
- one unambiguous authority for each claim and no duplicate task truth;
- deterministic validation and stable diagnostics without framework workarounds;
- incremental update and downstream invalidation after material discoveries;
- archive/history quality and ease of locating active versus delivered intent;
- setup, dependency, generated-file, maintenance, and agent-context cost;
- portability to consumer repositories and behavior when optional tooling is unavailable;
- measured contribution that OwlBear would otherwise have to implement.

O2 wins. There are four active change packages but no canonical files under `openspec/specs/`, no observed trusted use of apply/update/sync/archive, and only two workflow integrations that call `openspec status` to resolve paths. The one recorded strict validation passed while material product-path work remained absent. Removing `/opsx:propose` also removes OpenSpec's largest visible contribution. What remains is filesystem convention and structural validation, both of which the native execution contract needs to own regardless.

The native change package retains the valuable information model:

```text
product-intent -> normative-specs -> implementation-contract -> execution-plan
```

Removal does not mean flattening the documents into Kanban or discarding delta requirements. Preserve the four current change directories and their Git history during migration; map proposal, specs, design, and accepted decisions into the native package; stop generating advisory `tasks.md`; and generate Kanban only from the admitted Execution Plan. Archive, revision, path resolution, and stale-admission behavior should be implemented only to the depth required by the native contract.

Do not build a generic specification framework to replace OpenSpec. The minimum native surface is a documented directory contract, metadata and stable IDs, a loader/path resolver, the admission validator already required by this redesign, and a preservation-first migration command or script. Ordinary file editing and Git provide artifact creation and history.

### 3.9 Tool-Neutral Structured Execution Plan

The plan MUST be parseable structured data or rigorously parseable Markdown and contain stable IDs for requirements, design obligations, deliverables, interfaces, migrations, proofs, and tasks. Each item records authority links, owner, dependencies, affected surfaces, acceptance behavior, risk class, and proof command or proof-construction task.

Required views are: Requirement Coverage Map, Design Obligation Map, Interface Coverage Map, Migration/Removal Sequence, Product Invariant Map, Proof Ownership Map, and projected Kanban dependency graph. These are views of one model, not independently maintained prose tables.

The first model SHOULD be the minimum structure required to express and reject known invalid plans. It MUST remain extensible through general concepts rather than attempting to encode every semantic judgment. Human-readable Markdown may carry rationale; structured fields carry identities, links, owners, graph relations, risk dispositions, and proof contracts.

A provisional tool-neutral shape is:

```yaml
change:
	intent: [promise-id]
	requirements: [requirement-id]
	design_obligations: [design-id]
normal_workflows:
	- id: workflow-id
		entry: public invocation or user action
		result: observable outcome
interfaces:
	- id: interface-id
		producer: owner-id
		consumer: owner-id
		contract_authority: source reference
		implementation_owner: task-key
		migration_owner: task-key-or-null
		failure_semantics: requirement-id
		proof_owner: task-key
migrations:
	- id: migration-id
		from: current state
		to: target state
		ordered_steps: [task-key]
		consumer_inventory: [owner-id]
risks:
	- id: risk-id
		class: destructive | concurrent | security | lifecycle | compatibility
		scenarios: [scenario-id]
		owner: task-key
tasks:
	- key: stable-task-key
		outcome: observable delivery outcome
		owns: [promise-id, requirement-id, design-id]
		modules: [module-id]
		produces: [interface-id]
		consumes: [interface-id]
		depends_on: [stable-task-key]
		acceptance: [scenario-id]
		proof:
			boundary: public or assembled boundary
			method: command or observation
			replacements_allowed_below: [boundary-id]
		risk_dispositions: [risk-id]
aggregate_proofs:
	- id: proof-id
		workflow: workflow-id
		owner: task-key
		prerequisites: [stable-task-key]
```

This is a discussion anchor, not the final schema. Fields earn permanence only when they support an invariant, a preserved healthy capability, or a general planning query. For example, `interfaces` supports edge completeness, while browser-page lifetime is represented as a lifecycle risk or contract obligation rather than a browser-specific field.

### 3.10 Admission Invariants

A deterministic validator MUST reject the plan when any of these is true:

- **A1:** a requirement, negative requirement, design obligation, or preserved behavior has no delivery owner and proof.
- **A2:** a changed interface lacks producer, consumer, contract authority, implementing owner, failure semantics, or boundary proof.
- **A3:** a migration/removal step lacks ordering, compatibility disposition, final deletion owner, or proof of absence.
- **A4:** destructive or concurrent behavior lacks no-overwrite, complete-set, idempotency, race, and failure-path disposition as applicable.
- **A5:** aggregate proof depends on a harness, fixture, generated client, clean build, or composition path with no build-capable predecessor.
- **A6:** a collector or verifier is the first owner capable of creating required product wiring or proof infrastructure.
- **A7:** task dependencies do not permit a complete requirement path to be assembled before aggregate verification.
- **A8:** a task's acceptance surface exceeds its declared modules/interfaces, or its risk exceeds the permitted task complexity profile.
- **A9:** one concern has conflicting authorities, or a planning artifact and Kanban both act as execution-task truth.
- **A10:** material upstream artifacts changed after validation and the plan has not been readmitted.

Diagnostics SHOULD use stable codes, severity, target IDs, evidence, and remediation. Semantic challenge remains required, but cannot waive an error-level invariant without a recorded user decision and explicit schema-supported exception.

These checks prove internal consistency and explicit coverage, not that the design is wise or that the planner identified every real-world interface. Admission therefore has five layers:

1. **Artifact readiness:** required intent, behavior, design, decision, and plan fields exist.
2. **Deterministic consistency:** identities, references, ownership, dependencies, coverage, risk dispositions, and proof authorization satisfy A1-A10.
3. **Repository-grounded semantic challenge:** an independent reviewer compares the model with current source, canonical contracts, normal workflows, and plausible omissions.
4. **Executable baseline:** affected package builds, type/contract generation, and the cheapest relevant normal-boundary smoke pass from a clean committed state when the change class requires them.
5. **User decision gate:** the user approves product outcomes, accepted exclusions, consequential architecture decisions, and material graph trade-offs, without certifying mechanical completeness.

### 3.11 Why Current Safeguards Are Insufficient

`#1927`, `#1928`, and `#1964` improve maps, proof guidance, and decomposition language. They should be retained as semantic guidance, but they cannot detect a missing edge they never model, prove that a command crosses the assembled product boundary, or prevent board writes. Static interaction tests establish prompt order, not operational rejection. The missing control is an executable artifact contract plus an admission gate tested against known-bad plans.

### 3.12 Required Operational Changes

1. **Restrict trust immediately.** Until layered admission exists, treat the current path as unsuitable for cross-package, multi-interface, destructive, concurrent, migration-heavy, or aggregate-workflow changes without an explicit manual architecture and proof audit.
2. **Persist confirmed intent.** The durable Product Intent includes the original promise, normal workflow, material decisions and alternatives, assumptions and evidence state, accepted exclusions, wrong-but-plausible outcomes, and measurable completion.
3. **Separate design from decomposition.** No trusted upstream command generates implementation tasks before repository-grounded design is reviewed.
4. **Use one graph authority.** Generate Kanban from one admitted model; do not synchronize advisory tasks with a separately invented board graph.
5. **Cover interface edges.** Every changed boundary names producer, consumer, contract authority, implementation owner, migration/removal disposition, failure semantics, and assembled proof owner when applicable.
6. **Assign executable completion.** Code, fixtures, harnesses, server setup, generated clients, and browser/runtime proof have build-authorized owners in the initial graph.
7. **Verify committed baselines.** Cross-module plans name affected-package build, type/contract generation, focused tests, and normal-path smoke requirements appropriate to risk.
8. **Admit before mutation.** Invalid plans cannot create Kanban tasks or transition work to build.
9. **Replace count-only complexity with risk disposition.** Changed interfaces, failure domains, proof modes, concurrency, destructive operations, migrations, and scenario families influence task boundaries and required challenge.
10. **Make challenge inspectable.** Challenger output records one disposition per requirement, Promise item, changed edge, migration step, material risk, and normal-path proof; free-form `pass` is insufficient.

## 4. Recommendation, Confidence, and Limits

### 4.1 Backward Implementation Plan

Implement from the build boundary backward:

1. Define the minimal typed `ExecutionPlan` and admission diagnostic contract from what a builder-ready graph must prove.
2. Encode the four incidents below as failing validator fixtures before changing prompts.
3. Implement admission invariants A1-A10 and require a pass before Kanban creation or build transition.
4. Refactor `/shape`, the shaper, decomposition workflow, and challenger to emit and review that contract; make board projection deterministic and idempotent.
5. Define the Implementation Contract fields `/shape` requires, then create `/design` and its repository-grounding checks.
6. Define the Product Intent fields `/design` requires, then change `/ideate` to write the durable artifact and decision links.
7. Introduce the minimal native change package around the proven contracts; support read-only import of the four current OpenSpec packages during migration.
8. Update routing, setup, generated assets, tests, and documentation; remove stock `/opsx:*`, the global OpenSpec installer, advisory task generation, and OpenSpec-specific validation after migration proof passes.
9. Migrate one real change end to end, compare admitted projection with actual build discoveries, then roll out and retire superseded prose paths.

Do not begin by rewriting `/ideate`. The downstream admission contract determines which upstream information is actually necessary; backward construction prevents another attractive document flow with no executable guarantee.

### 4.2 Mandatory Regression Fixtures

- **R1 Browser lifecycle:** reject a plan where acquisition consumes authenticated pages but no task owns retained-page lifetime and composition proof.
- **R2 Workspace repair/removal:** reject missing transport/callback edges, final API deletion, no-overwrite, or complete-set safety.
- **R3 Memory purge integration:** reject individually testable frontend/API/engine tasks when no proof traverses the real assembled path.
- **R4 Memory lifecycle clean build:** reject aggregate proof without generated/frontend API contract ownership and a clean-checkout typecheck/build predecessor.

Each fixture MUST fail for the original defect, pass only when the omitted obligation is assigned, and assert a stable diagnostic code. At least one end-to-end shaping test MUST demonstrate that a defective plan cannot mutate Kanban or enter build.

These fixtures are necessary but not sufficient. Add generative or table-driven tests for generic missing references, cycles, disconnected paths, authority conflicts, stale admission, proof authorization, risk dispositions, and unsupported exceptions so the validator does not merely memorize four historical plans.

### 4.3 Rollout and Migration

Start in shadow mode: generate plans and diagnostics without blocking one pilot change. Compare predicted obligations with builder/verifier discoveries. Then enforce admission for newly shaped multi-surface, destructive, concurrent, migration, and aggregate-proof work. Existing in-flight graphs are not silently grandfathered: run read-only admission and return material omissions to shape. Retire duplicate maps only after they are generated reliably from the structured plan.

### 4.4 Success Measures and Stop Conditions

Track: late graph-expansion rate; unowned requirement/interface/proof count at admission; post-admission material-plan invalidations; collector rejections caused by absent harnesses; clean-build failures first discovered after aggregate work; and false-positive/waived diagnostics. The principal target is zero late expansion for obligations knowable at shape time across three consecutive representative changes.

Stop rollout and revise the model if admission routinely passes plans that later need known-work expansion, blocks narrow work without identifying a concrete missing obligation, requires parallel manual maps to remain trustworthy, or turns exceptions into the normal path. Do not optimize for zero implementation defects or zero verifier rejection.

### 4.5 Alignment Checklist for Every Follow-up Change

Every follow-up MUST state: principles P1-P8 addressed; healthy capabilities preserved; invariants A1-A10 implemented or intentionally deferred; regression and generic fixtures added; authority created, changed, or retired; OpenSpec dependency and artifact migration affected; build transition affected; migration/rollback behavior; and metric expected to improve. A change that only adds prompt prose or static wording tests MUST explain why deterministic enforcement is impossible; otherwise it is not aligned.

### 4.6 Confidence and Limits

**Confidence:** High that the root cause is missing execution-contract admission and edge/proof ownership; high that backward design, layered admission, and incident fixtures address the observed class; high that OpenSpec should be removed; medium-high on the exact native package shape until the first migrated change exercises revision and closure.

This is a recommended problem and target-capability authority grounded in the four incidents and the healthy current workflow. It selects a native OwlBear change package over OpenSpec but is not an approved implementation change, final field schema, or command naming decision. New evidence may revise it, but silent divergence is prohibited: record the conflict, rationale, and superseding authority.