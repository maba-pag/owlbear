# End User Stance — Test Quality & Lifecycle

## User Experience Position

The test suite is currently hostile to its users. 229 files, 83% task-numbered, no lifecycle, no distinguishability. Agents face a wall of tests they can't evaluate and rationally learn to ignore. The human faces a cleanup burden that accumulates silently until manual deletion is the only option. The system has trained its own users to distrust it.

## Core Argument

### 1. Lifecycle is the primary trust lever — but it requires semantic consolidation, not just file reduction

The brief correctly identifies lifecycle as the core problem. Stale task tests cause noise, noise causes dismissal, dismissal kills the TDD feedback loop.

But lifecycle hygiene alone is insufficient. A smaller suite can still contain implementation-coupled tests that break on improvement. **Consolidation must produce contract-level module tests that verify behavior, not just replicate task assertions at a lower file count.** If the consolidated tests are still coupled to implementation details, the suite shrinks but the trust problem persists at the module level.

### 2. Immutability is a blocker, not a contributing factor

The review gate makes `TestFromAC_*` classes immortal — removal is an automatic FAIL. This doesn't just contribute to the lifecycle problem; it makes lifecycle action literally illegal under current rules. No lifecycle mechanism can operate until this gate opens. Whether it opens for a lifecycle agent, the reviewer, or the auditor is a design choice, but it must open. This is the first domino.

### 3. Scoped execution is a root cause that lifecycle doesn't fix

Builders run only their task-scoped test file. Auditor runs the full suite. This means builders produce cross-task regressions they never see, never learn from, and never fix. The auditor inherits the entire triage burden.

Lifecycle keeps the suite clean for the auditor, but it does not fix the builder's structural blindness. **Builders need at minimum a fast signal about whether their change breaks the affected module's durable tests** — even a targeted smoke test, not a full-suite run. Without this, the feedback loop is broken at the point of creation.

### 4. AC provenance must survive consolidation — it's non-optional

`TestFromAC_*` naming provides the link from acceptance criteria to test assertions. This is how behavioral intent is tracked and how coverage preservation is verified during pruning. **If you consolidate task tests into module tests and drop the AC lineage, nobody can verify the result actually covers the original behavioral requirements.**

Provenance can change form (comments, docstrings, metadata in module-level tests rather than task-numbered filenames), but the semantic link from "this assertion verifies AC X" must persist in the durable layer.

### 5. Agents experience test state through filesystem structure — and the transition is visible

Stateless agents read the filesystem. They `ls tests/` and see what's there. Currently: 190 task-numbered files that all look the same. Agents cannot distinguish permanent from scaffolding, valuable from stale, theirs from someone else's.

**The durable end-state:** module-level test files (`test_{module}.py`) are the permanent suite, clearly distinguishable from task-scoped scaffolding.

**The transition is not invisible.** During the hybrid period, agents will encounter a mixed corpus — some legacy task files, some consolidated module files, some new task files pending consolidation. The infrastructure must handle this explicitly (clear naming, markers, or separation) rather than pretending stateless agents won't notice the mess.

### 6. The convention must be updated to reflect the two-tier reality

Written conventions prescribe module-level tests. The pipeline correctly produces task-scoped tests. The brief calls this "convention drift" and "convention gap" — it's a genuine conflict, not just incomplete documentation.

The convention must acknowledge the two-tier model: **task tests are correct scaffolding produced during RED/GREEN; module tests are the durable artifact produced during lifecycle processing.** The test-writer's behavior is correct. The convention describing expected outcomes is wrong.

### 7. Human UX: health invariants plus behavioral evidence

**Suite properties** (green, fast <60s, right-sized, coverage ≥90%) are the ongoing automated health signal. If any invariant drifts, surface it.

**Behavioral evidence** is the primary trust outcome. Outcome 1 is verified by absence of "pre-existing, skipping" patterns in agent behavior. This is a harder signal to capture than suite stats, but it's the actual measure of whether the system is working. The human needs access to both.

**Zero-touch is the goal** for day-to-day operation. The human should not curate individual tests. The lifecycle mechanism handles that. The human monitors invariants and investigates only when an invariant breaks.

### 8. Module-level tests also need lifecycle governance

The durable layer cannot be exempt from lifecycle. Module-level tests can also go stale, become implementation-coupled, or accumulate as the codebase evolves. The lifecycle model must cover both tiers: task tests have aggressive lifecycle (transient, consolidated or pruned after task completion), module tests have lighter lifecycle (periodic relevance review, coverage verification).

## Key Trade-offs

| Trade-off | Position |
|-----------|----------|
| Lifecycle hygiene vs. semantic quality of consolidated tests | Both required. Shrinking the suite without improving test quality perpetuates the trust problem at the module level. |
| Fast scoped execution vs. cross-task regression detection | Keep scoped execution for speed. Add targeted module-test signal for builders. Don't force full-suite runs at builder stage. |
| Provenance preservation vs. clean module-level naming | Preserve provenance in a form compatible with module-level organization (comments/metadata, not task-numbered filenames). |
| Zero-touch human experience vs. behavioral trust verification | Automate suite metrics. Require behavioral verification (agent investigation patterns) for the trust outcome — even if this is harder to instrument. |
| Aggressive task-test lifecycle vs. coverage preservation | Hard constraint: ≥90% coverage floor. Consolidation must verify coverage before and after pruning. Provenance enables this verification. |

## Warnings

1. **Solving lifecycle without opening the immutability gate is theatre.** If `TestFromAC_*` tests remain immortal under code review, no lifecycle mechanism can operate. This rule must change first.
2. **Consolidation that just reduces file count without improving test quality will recreate the problem at the module level.** The consolidation step must produce contract-level behavioral tests, not transplanted implementation assertions.
3. **The hybrid/transition period is the highest-risk phase for agent trust.** A mixed corpus of legacy task files and new module files is more confusing than either pure state. Plan for it explicitly.
4. **Ignoring the builder's visibility gap means the auditor remains the noise sponge.** Lifecycle cleans the suite, but builders still won't see their own cross-task impacts without an execution model change.
5. **Module-level tests are not immortal either.** Without lifecycle governance on the durable layer, you'll have the same accumulation problem in 12 months, just with different filenames.

## Confidence

**0.78** — Position is hardened through five Critic cycles. Core argument is structurally sound. Remaining uncertainty: how behavioral trust verification works in practice, and whether the builder-visibility expansion is achievable without unacceptable performance cost. The Critic consistently challenged the lifecycle-sufficiency claim, which strengthened the final position's insistence on semantic quality during consolidation and the separate scoped-execution fix.
