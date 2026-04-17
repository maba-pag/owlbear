# Data Quality Stance — The Modeler

## Position Summary

The test suite's data problem is not lack of measurement — it's lack of a **decision-grade data model** that can drive automated lifecycle actions on the existing corpus without requiring infrastructure that doesn't exist yet. The model must work in degraded mode on day one and improve with progressive instrumentation.

## Data Quality Stance

### The Measurement Trap

The natural instinct is to measure everything (per-callable coverage, failure-change correlation, survival rates, assertion analysis) and then make decisions. This is backwards. The existing corpus of ~190 task-numbered files has zero metadata, zero lifecycle markers, and zero structured AC references. Building an elaborate measurement system before you can act on ANY of it means the accumulation problem continues while you build instrumentation.

**Position: the data model must be tiered — operational at each tier, not dependent on the richest tier to function.**

### Unit of Record: Two Levels

**Measurement unit**: test callable (pytest node ID) — files are heterogeneous, containing multiple TestFromAC classes with different provenance and different AC coverage.

**Lifecycle outcome unit**: test file — the brief's success criteria are file-level ("test files map to modules, not tasks"). Callable-level data drives file-level decisions: a task-numbered file is archived when all its callables are either pruned or promoted into module-level files.

**Stable identity**: pytest node IDs change when callables move between files (promotion). Longitudinal tracking needs a stable identifier: `(original_task_id, class_name, method_name)` tuple survives the physical move.

### Primary Decision Driver: AC Scenario Lineage

The primary question for any task-scoped callable is: **is its AC proof carried by a module-level callable of equal or better quality?**

"AC item" is too coarse — the RED workflow generates multiple scenarios per AC line (happy path, edge cases, boundaries). The unit of lineage is the **AC scenario**: `(ac_item_id, scenario_type)`. A task-scoped callable is prunable when every AC scenario it proves is also proven by a module-level callable.

**Quality criterion for promotion**: the module-level replacement must be contract-level (verifies observable behavior, not implementation details) and structurally durable (not coupled to internal implementation that will change on refactor). Lineage without quality improvement just moves the noise.

### What This Means for Each Question

**How to measure test quality?**
Three dimensions, in priority order:
1. **Contract coupling** — does the test verify what the module promises to consumers, or how it internally works? Measured by assertion targets (outputs, exceptions, public API responses = contract; internal state, private methods = implementation). Mock assertions on public collaborator interfaces count as contract.
2. **AC scenario coverage** — does this callable prove AC scenarios not proven elsewhere? Unique proof = high value.
3. **Coverage contribution** — secondary, for redundancy screening only. A test can contribute unique line coverage of code nobody cares about.

**What metrics drive lifecycle decisions?**
Two tiers:
- **Tier 1 (gate criteria)**: AC scenario lineage complete (every scenario proven by another callable) AND coverage floor maintained (≥90%). Both must pass for pruning.
- **Tier 2 (prioritization)**: execution time (expensive tests get consolidated first), failure frequency (noisy tests are urgent), age (older unconsolidated tests are a worse smell).

**How to detect redundant tests?**
1. AC scenario overlap — two callables proving the same scenarios with the same quality → one is redundant.
2. Coverage overlap as screening — >80% line overlap flags pairs for AC comparison. But coverage overlap alone is NOT redundancy proof (different contract reasons for same lines).
3. Cross-module tests are never redundant just because they overlap with unit tests — they test different integration contracts.

**What data model represents test lifecycle state?**

```
# Callable-level (measurement)
TestCallable:
  stable_id: str              # (task_id, class, method) tuple hash
  node_id: str                # current pytest node ID
  file_path: str              # current file
  callable_type: class | function
  source_task_ids: list[int]  # plural — multi-provenance exists
  target_modules: list[str]   # plural — cross-component tests exist
  ac_scenarios: list[ACScenario]  # what this callable proves
  contract_level: contract | implementation | unknown
  execution_time_ms: int
  markers: list[str]
  created_at: date

# File-level (lifecycle outcome)
TestFile:
  path: str
  file_type: task-scoped | module-level | benchmark | integration
  callable_ids: list[str]
  lifecycle_stage: active | consolidating | archived

# Lineage (AC scenario is the atomic unit)
ACScenario:
  id: str                     # stable reference
  ac_item: str                # which AC line
  scenario_type: str          # happy_path | edge_case | boundary | error
  proven_by: list[str]        # stable_ids of callables that prove this
  # INVARIANT: len(proven_by) >= 1 — no orphaned proof
```

**How to measure whether the system is working?**
Segmented by file_type and marker category:
1. **Accumulation balance**: new task-scoped files per period vs archived per period (target: outflow ≥ inflow)
2. **Consolidation progress**: % of AC scenarios proven by module-level callables
3. **Trust proxy**: ratio of task-scoped to module-level callables (should decrease)
4. **Speed**: total execution time by category (target: <60s total)
5. **Coverage floor**: ≥90%
6. **Single-point-of-proof risk**: count of AC scenarios with only one proving callable
7. **Contract quality**: % of callables classified as `contract` vs `implementation` vs `unknown`

## Schema and Validation Reasoning

### Progressive Enrichment (The Bootstrap Problem)

The ~190 existing task-numbered files have none of this metadata. The model MUST be operational without full enrichment.

**Tier 1 — Works today, no new infrastructure:**
- Classify files by naming pattern (task-numbered vs module-level)
- Extract task IDs from filenames
- Infer target modules from import graph
- Measure execution time (pytest --durations)
- Aggregate coverage baseline
- Decision capability: identify task-numbered files whose target module already has module-level test file → flag for manual review (NOT auto-prune — file existence ≠ AC proof equivalence)

**Tier 2 — Moderate infrastructure (structured annotations):**
- AC scenario tracking via structured docstrings or a sidecar registry
- Contract-level classification (heuristic from assertion patterns + manual annotation for ambiguous cases)
- Decision capability: AC-lineage-based pruning and promotion

**Tier 3 — Significant infrastructure:**
- Per-callable coverage attribution (coverage.py --contexts or pytest-testmon, likely without xdist)
- Failure history with commit context
- Decision capability: fine-grained redundancy detection, automated prioritization

**Each tier is independently useful.** Tier 1 provides triage. Tier 2 enables lifecycle automation. Tier 3 refines it.

### Validation at Lifecycle Boundaries

- **Pre-prune**: AC scenario invariant (every scenario proven elsewhere) AND coverage floor ≥90%. The AC check is the decision; coverage is the safety net.
- **Pre-promote**: promoted callable covers ≥ the AC scenarios of the callables it replaces, AND is classified as `contract` level (not `implementation`).
- **Pre-archive file**: all callables in the file are pruned or promoted. File removal is a consequence, not a decision.

### Schema Invariants (Non-Negotiable)

1. **No orphaned AC proof**: `len(proven_by) >= 1` for every ACScenario, always.
2. **No pruning below floor**: suite coverage ≥ 90% after any removal.
3. **No promotion without quality improvement**: promoted callable must be contract-level.
4. **Stable identity survives moves**: longitudinal tracking doesn't break on file reorganization.

## Key Trade-offs

| Trade-off | Position | Rationale |
|-----------|----------|-----------|
| Callable vs file granularity | Both (two-level) | Files are heterogeneous; outcomes are file-level |
| AC lineage vs coverage delta as primary | AC lineage | Coverage can't distinguish contract from implementation |
| Rich metrics vs operational now | Progressive tiers | Elaborate model that can't run is worse than coarse model that can |
| Automated vs manual classification | Semi-automated | Contract-level classification needs human judgment for edge cases |
| Per-callable coverage vs aggregate | Aggregate now, per-callable later | Per-callable needs infrastructure; aggregate is free |

## Warnings

1. **Authority is a blocking dependency.** The data model enables lifecycle decisions but current pipeline rules PROHIBIT the transitions it describes. Reviewers cannot weaken TestFromAC tests (automatic FAIL). Builders cannot modify them. Until a lifecycle agent or amended rules create legal authority for prune/promote/archive, this model is descriptive, not operative. This is not a "future concern" — it blocks everything.

2. **AC scenario tracking is the critical path for Tier 2.** Without structured AC references in tests, the primary decision driver doesn't function. The bootstrap must extract or annotate AC scenarios for the existing corpus. Where extraction fails, tests sit in an "unknown" state and cannot be lifecycle-managed.

3. **"Unknown" is the dangerous state.** Callables with `contract_level: unknown` or empty `ac_scenarios` cannot be safely pruned or promoted. If bootstrapping leaves >50% of callables in unknown state, the model is not operational and the accumulation problem continues. Need a stopping condition: if automated extraction achieves <50% coverage of the corpus, escalate to manual triage.

4. **Coverage floor is necessary but not sufficient.** A suite can maintain 90% coverage with entirely implementation-coupled tests. The coverage check prevents making things worse; it does not prove things are good. AC lineage + contract quality are the actual quality signals.

5. **Failure-change correlation is aspirational.** It requires per-failure commit context that the pipeline doesn't capture, and full-suite runs happen only at the auditor stage. Don't design core lifecycle gates around it. Use it for prioritization if/when the data becomes available.

## Confidence

**0.72** — The progressive enrichment strategy and two-level model address the bootstrapping and granularity problems from prior rounds. The AC-scenario-as-atomic-unit framing is sound but untested against real corpus complexity. The authority dependency is acknowledged as blocking. Main residual risk: AC scenario extraction from the existing corpus may be harder than projected, leaving too many callables in "unknown" state.
