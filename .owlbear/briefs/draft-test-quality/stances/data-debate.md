# Data Stance — Critic Debate Log

## Round 1

### Position Submitted
- Primary signal: coverage delta if removed
- Unit of record: test file
- Metrics: coverage delta, execution time, age, last true/false positive dates
- Redundancy: coverage overlap matrix, strict subset detection
- Data model: per-file record with single task_id, single lifecycle stage
- Suite health: execution time trend, test/module ratio, coverage floor, false positive rate

### Critic Challenges (Confidence: 0.31, Recommendation: Reject)

1. **CRITICAL — Coverage delta can't distinguish contract from implementation tests.** A brittle implementation-detail test and a durable contract test can cover the same lines. Coverage-first ranking preserves exactly the tests the brief says are harmful.
2. **CRITICAL — File-level granularity is wrong.** Files contain multiple independent TestFromAC classes with different provenance. Single task_id per file is semantically meaningless after promotion.
3. **CRITICAL — True/false positive distinction is non-observable.** Pipeline doesn't emit ground truth. Catch-history is a bad proxy — a regression guard may go years without firing and still be essential.
4. **CRITICAL — Missing authority dimension.** Metadata record doesn't create legal transition paths. Review rules make TestFromAC removal automatic FAIL. Lifecycle stages are descriptive, not operative.
5. **MODERATE — Performance cost hand-waved.** Coverage delta computation is expensive; brief wants <60s suite. Adding per-test coverage analysis threatens the main outcome.
6. **MODERATE — Coverage overlap ≠ redundancy proof.** Task files may cover same lines for different contract reasons (different AC items).

### Blind Spots Identified
- No AC lineage after archival
- No marker-aware runtime cost model
- No governance/authority model for lifecycle transitions

### Response
Accepted all six challenges. Major restructuring: shifted primary signal to contract coupling, changed unit to test class, made target_modules plural, added AC lineage many-to-many graph, acknowledged authority as architectural dependency.

---

## Round 2

### Position Submitted
- Primary signal: contract coupling (failure-change correlation, survival rate, assertion analysis)
- Unit of record: test class
- Target modules: list (cross-component)
- Source task IDs: plural (multi-provenance)
- AC lineage: many-to-many via superseded_by/supersedes
- Coverage: secondary signal for redundancy screening
- Cold-start protection: grace period before pruning eligibility
- Coverage map: acknowledged as infrastructure prerequisite
- Mock assertions on public collaborator interfaces treated as contract tests

### Critic Challenges (Confidence: 0.34, Recommendation: Reject)

1. **CRITICAL — Unit still wrong.** Test classes aren't universal either — standalone functions, mixed-provenance classes exist. Also: brief's success is file-level, but record is class-level. Callable-level ledger can classify while leaving artifact sprawl unchanged.
2. **CRITICAL — Failure-change correlation dominated by change frequency and run cadence, not contract quality.** Full-suite runs happen only at auditor stage. Cross-component union widening makes accidental correlation easier.
3. **CRITICAL — Model depends on metadata that doesn't exist.** Source task IDs, target modules, AC items, changed_files per failure, supersession graph — all are the gate, none exist. Heuristic inference means deletion decisions rest on speculation.
4. **MODERATE — Collaborator interface rule is circular.** "What the module promises vs how it internally works" restates the distinction without making it mechanically decidable.
5. **MODERATE — Coverage internally inconsistent.** Demoted to "secondary" but pruning gate still requires coverage floor. Coverage is simultaneously non-decisive and decisive.
6. **MODERATE — Position built on unratified constraint.** Published w-tdd-red conventions still prescribe module-level tests. The "task-scoped tests are correct" constraint diverges from the system's own rules.

### Blind Spots Identified
- No bootstrap strategy for existing 190 task-numbered files
- Authority model still deferred
- No statistical standard for when correlation evidence is "enough"

### Response
Accepted challenges 1, 2, 3 as fundamental. Restructured: two-level model (callable measurement, file outcomes), shifted primary driver to AC lineage (deterministic, not statistical), added bootstrap strategy, acknowledged authority as blocking dependency.

---

## Round 3

### Position Submitted
- Two-level model: callable measurement, file lifecycle outcomes
- Primary driver: AC lineage ("does module-level callable prove same AC items?")
- Statistical metrics demoted to prioritization only
- AC lineage per-callable with superseded_by/supersedes
- Bootstrap: static classification → AC extraction → coverage baseline → triage
- Progressive enrichment: Tier 1 (now), Tier 2 (moderate), Tier 3 (significant)
- Coverage as safety net, not decision driver

### Critic Challenges (Confidence: 0.34, Recommendation: Reject)

1. **CRITICAL — AC item is too coarse.** RED workflow generates multiple scenarios per AC line (happy path, edge, boundary). Collapsing scenarios under one AC label loses the proof. [Architect debate already rejected this compression.]
2. **CRITICAL — Primary gate unavailable on existing corpus.** AC tracking is the critical path but ~190 files have no metadata. Model is a schema, not an operational lifecycle, until the hardest data problem is solved.
3. **CRITICAL — Bootstrap triage contradicts primary driver.** "Target module has module-level test file" ≠ "module-level callable proves same AC items." File existence is far weaker than proof equivalence.
4. **CRITICAL — Authority is a precondition, not separable.** Current rules make TestFromAC removal illegal. Model can't postpone actor/phase question.
5. **CRITICAL — Model can improve lineage while leaving trust failure intact.** AC lineage metrics can improve while the suite still trains agents to distrust failures — if surviving tests are equally implementation-coupled.
6. **MODERATE — Node ID instability at promotion.** Moving a callable changes its pytest node ID, breaking longitudinal tracking.

### Blind Spots Identified
- No canonical namespace for AC items (wording drift, synonymous phrasing)
- No definition of equivalence for same-AC-different-scenario callables
- No stopping condition for when too much corpus is "undecidable"

### Response
Accepted all. Refined: AC scenario as atomic unit (not AC item), quality criterion for promotion (contract-level required), stable identity surviving moves, stopping condition for bootstrap, authority flagged as blocking dependency.

---

## Round 4

### Position Submitted
- AC scenario `(ac_item_id, scenario_type)` as atomic lineage unit
- Quality criterion: promoted callable must be contract-level
- Stable identity: `(task_id, class, method)` tuple
- Bootstrap with stopping condition: escalate if <50% automated extraction
- Three-tier progressive enrichment
- Authority explicitly flagged as blocking dependency

### Critic Challenges (Confidence: 0.34, Recommendation: Reject)

1. **CRITICAL — AC scenario still compresses.** Different preconditions, mocks, boundary values under same scenario_type are not equivalent proofs. False-prune risk concentrates here.
2. **CRITICAL — Primary gate still unavailable on existing corpus.** Acknowledged but not resolved — the hardest problem is deferred to bootstrap.
3. **CRITICAL — Bootstrap triage still inconsistent.** Tier 1 flags "files whose target module has module-level file" which ≠ AC proof equivalence.
4. **CRITICAL — Authority still blocking.** Acknowledged more explicitly but still deferred.
5. **CRITICAL — Lineage improvement doesn't guarantee trust improvement.** Gate doesn't ask whether surviving proof is less implementation-coupled.
6. **MODERATE — Stable identity brittle at promotion.** Class/method names change during consolidation.

### Blind Spots
- No canonical namespace for ac_items
- No equivalence definition for same-AC-different-precondition callables
- No stopping condition quantified for when model is operational vs not

### Response
Incorporated into final stance: quality criterion for promotion (contract-level required, addressing #5), Tier 1 triage as flagging not auto-pruning (addressing #3), authority as blocking warning (addressing #4). Accepted that AC scenario granularity has residual compression risk but this is irreducible without full test-level semantic analysis — the model is the best tractable approximation. Bootstrap availability problem (#2) is real and addressed through progressive tiers with explicit degraded-mode operations.

## Hardening Summary

| Round | Key Structural Change |
|-------|----------------------|
| 1→2 | File → class granularity; coverage → contract coupling as primary |
| 2→3 | Class → callable; statistical → AC lineage as primary; bootstrap strategy added |
| 3→4 | AC item → AC scenario; quality criterion for promotion; stable identity; stopping condition |
| 4→final | Progressive tiers with degraded-mode ops; Tier 1 flags not prunes; authority as blocking |

**Residual risks accepted in final position:**
- AC scenario granularity has compression risk at scenario boundaries (irreducible without semantic analysis)
- Bootstrap may leave >50% corpus in "unknown" state — stopping condition defined but outcome uncertain
- Authority dependency blocks all lifecycle transitions until governance is resolved
- Stable identity may still be brittle during major consolidation rewrites
