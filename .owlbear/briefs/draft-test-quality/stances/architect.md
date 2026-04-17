# Architect Stance: Test Lifecycle via Consolidation Agent

## Architectural Stance

**A two-tier test model with an automated consolidation agent running as a new pipeline stage after review.** Task-scoped tests are correct test-writer output (untouched). The curator agent promotes valuable assertions into durable module-level tests and removes the transient files. Pending-curation markers and escalation thresholds prevent both silent coverage loss and indefinite accumulation.

The curator is primarily a **file lifecycle manager**, not a test quality transformer. Quality improvement (removing implementation-coupled assertions) is a sequential second-order optimization via auditor-driven pruning. These are separate concerns solved in sequence: stop accumulation first, improve quality second.

## Structural Reasoning

### Two-Tier Test Model

| Tier | Naming | Lifecycle | Owner |
|------|--------|-----------|-------|
| Task-scoped (transient) | `test_{module}_{task_id}.py` | Born at RED phase → consumed by curator after review → deleted or pending | Test-writer creates, curator consumes |
| Module-level (durable) | `test_{module}.py`, `test_integration_{feature}.py` | Grows via promotion → pruned via auditor review | Curator promotes into, auditor maintains |

**Why two tiers, not three or more:** The current pathology is binary — task-scoped files have no lifecycle at all, module-level files don't exist for most modules. Adding intermediate tiers (e.g., "candidate", "provisional") would complicate the model without solving the core problem. Start with two; expand only if pending-curation rates exceed 20% of curator attempts.

### Test-Curator Agent — New `curate` Pipeline Stage

**Pipeline position:** `... → review → curate → docs → done → archived`

**Why a new stage, not reviewer/auditor responsibility:**
- The reviewer's job is verification, not transformation. Mixing curation into review creates a conflict of interest and makes an already-complex skill heavier.
- The auditor runs at end-of-pipeline and is already a bottleneck. Test curation requires per-task granularity.
- A dedicated agent has a single responsibility with a clear success criterion: task-scoped file count goes to zero.

**Curator algorithm:**
1. Identify the task-scoped file(s) for the current task
2. For each test method + its complete dependencies (fixtures, parametrize decorators, class-level setup, required imports):
   a. Determine the promotion target:
      - Single-module behavior → `test_{module}.py`
      - Cross-module interaction → `test_integration_{feature}.py` (scenario preserved whole; never fragmented across module files)
      - Ambiguous → mark pending, leave in active suite
   b. If a provably equivalent test method exists in the target (same scenario, same behavioral property, same boundary) → skip as duplicate, log the matching method name
   c. Otherwise → promote the complete scenario to the target file with traceability comment: `# Promoted from task #{id}: "{ac_line}"`
3. Run the full module test suite(s) — all must pass
4. Success → delete the task-scoped file, write consolidation log entry
5. Failure → mark `@pytest.mark.pending_curation(task_id=N, cycle=0, date=YYYY-MM-DD)`, create LOW-priority follow-up task, advance pipeline

**Drop criterion:** ONLY provable duplication. "When in doubt, promote." This biases toward a larger but trustworthy suite rather than a lean but coverage-gapped one.

### Pending-Curation Lifecycle

Files the curator can't consolidate stay in the **active suite** (preserving behavioral protection) with tracking markers:

| Phase | Trigger | Action |
|-------|---------|--------|
| Active | Cycles 0–10 OR days 0–90 | Re-evaluated each time curator runs on the same module |
| Escalated | 10 module-scoped cycles OR 90 calendar days | Follow-up task escalated to HIGH priority for human review |
| Auto-archived | 15 cycles OR 180 days | Moved out of `tests/` with coverage warning |

**Wall-clock fallback** ensures dormant modules don't create immortal pending files. The dual clock (cycle-based + calendar-based) provides a hard ceiling under all conditions.

### Auditor as Adversarial Gate for Curator

The auditor (who already runs the full suite) gains verification responsibility for curator consolidations:
- Diff module-level test files since last audit
- For each deleted task-scoped file: verify the consolidation log shows every test method either promoted or justified-duplicate (with the matching method identified by name)
- Verify module coverage ≥ 90% floor
- Flag pending_curation files approaching thresholds
- Report pending_curation percentage as a health metric

### Naming Convention Enforcement

A `conftest.py` hook validates:
- `test_{module}.py` — permanent module-level (no task ID suffix)
- `test_{module}_{digits}.py` — transient task-scoped (curator target)
- `test_integration_{feature}.py` — permanent cross-module
- Files matching no pattern → warning

### Reviewer Immutability Unchanged

The `w-code-review` test immutability rule (WEAKENED/REMOVED = automatic FAIL) remains intact for builders and reviewers. Only the curator has post-review modify/delete authority over TestFromAC tests, and only after review has passed. This preserves the review gate's integrity.

### Adjacent Concern: Early Detection

Expanding builder and reviewer scoped-runs to include the full module test suite (not just the task-scoped file) should be part of the same brief. This addresses the "late detection" root cause that the curator doesn't solve. The curator handles lifecycle; broader scoped-runs handle trust.

### Migration Plan (One-Time)

1. **Triage** — categorize all ~190 task-numbered files as: (a) duplicate of existing module-level test, (b) unique behavioral value, (c) broken-but-meaningful (evidence of code drift), (d) broken-and-stale
2. **Analyze broken** — for failing tests, determine if the failure indicates legitimate code drift or genuinely stale assertions. Broken ≠ deletable.
3. **Promote valuable** — module-by-module with scenario-level comparison and full suite verification
4. **Mark pending** — anything that doesn't consolidate cleanly gets pending_curation marker

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task-scoped file count | → 0 (steady state) | Count `test_*_{digits}.py` files |
| Module-level count | Sublinear growth relative to task count | Track ratio over time |
| Suite runtime | < 60 seconds | Timed pytest runs |
| Consolidation success rate | > 80% of curator attempts | Curator logs |
| Pending-curation count | < 20% of curator attempts | Curator health metric |

## Key Trade-offs

| Decision | Chosen | Alternative | Rationale |
|----------|--------|-------------|-----------|
| New pipeline stage | Yes — `curate` after review | Extend reviewer or auditor | Single responsibility; neither reviewer nor auditor should own transformation |
| Drop criterion | Provable duplication only | Heuristic drops (mock-heavy, old, etc.) | Conservative policy bounds downside risk; heuristics are brittle |
| Pending-curation in active suite | Yes — preserve behavioral protection | Quarantine (exclude from suite) | Coverage preservation > noise reduction; matches brief's outcome priority |
| "When in doubt, promote" | Yes — trust over suite size | Aggressive pruning | Brief ranks trust (#1) above speed (#2) above right-sizing (#4) |
| Curator scope | File lifecycle only | Curator also improves test quality | Separation of concerns; quality improvement is auditor's second-order job |

## Warnings

1. **Semantic judgment is the primary risk.** The curator must judge test equivalence — "same scenario, same behavioral property, same boundary." No amount of design eliminates this judgment requirement. The conservative "when in doubt, promote" policy bounds the downside but doesn't eliminate it. This is the most likely failure point.

2. **Promotion ≠ quality transformation.** Promoted tests may still be implementation-coupled. They're durable (in the lifecycle sense) but not necessarily high-quality (in the behavioral sense). "Green suite = trust" requires BOTH lifecycle management (curator) AND quality improvement (auditor pruning). The design addresses both in sequence, but the trust outcome is not fully delivered by the curator alone.

3. **Auto-archive is an imperfect backstop.** Timeout-based archival at 180 days doesn't prove behavior survives elsewhere. It prevents indefinite accumulation at the cost of potential edge-case coverage loss. The 90% coverage floor provides a lower bound but is a coarse proxy.

4. **Pending-curation files remain noisy.** Files in the active suite with pending_curation markers contribute the same noise as current task-scoped files — for up to 90 days. This is a deliberate trade-off: behavioral protection at the cost of some continued signal pollution. The escalation/archival timeline bounds this noise.

5. **Cross-module scenarios are hard.** The curator must distinguish "tests module A's behavior using module B as a collaborator" (promote to `test_A.py`) from "tests the interaction between A and B" (promote to `test_integration_{feature}.py`). This distinction is not always clear. Ambiguous cases go to pending_curation, but if cross-module scenarios are common, pending rates will be high.

## Confidence

**0.78** — The design addresses the stated problem (test lifecycle) with clear mechanics, bounded failure modes, and explicit trade-offs. The irreducible risk is semantic judgment in equivalence detection. The trust outcome depends on the sequential combination of curator (lifecycle) + auditor (quality), not the curator alone. The Critic correctly identified that promotion doesn't solve signal quality — but the design doesn't claim to solve it in one stage.
