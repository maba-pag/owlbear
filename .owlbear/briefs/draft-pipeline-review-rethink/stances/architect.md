# Architectural Stance — Pipeline Review Rethink

## Position

The proposal is structurally sound. The 8 locked outcomes are architecturally coherent, the role table produces clean separation, and structural test lifecycle is the right mechanism. Five joints are load-bearing and need tighter specification to prevent implementation drift.

### Joint 1: Consolidation-test trigger must be part of upfront decomposition

"End of feature chain" is not a kanban concept and cannot be mechanically detected. The trigger must be the planner's decomposition act: when the planner decomposes a feature into tasks A, B, C, it also creates task D ("consolidation test for [feature]") with dependencies on A, B, C.

This is ongoing lightweight metadata (planner must update dependencies when scope changes), not zero-infrastructure. But the alternative — state-triggered detection — has worse failure modes (unreliable "last child done" detection, no first-class feature-chain identity in the kanban model). The maintenance cost is justified because the planner already owns the decomposition; this adds one more task to the initial plan, not a new mechanism.

Fallback: auditor flags missing consolidation-test during final task review.

### Joint 2: AC quality has a single owner — the architect

The locked outcomes say planner follows architect's AC rules AND architect produces enumerated, observable AC. This creates an ownership split that will produce ambiguity. The clear chain:

1. **Planner** drafts best-effort AC using the shared AC quality skill
2. **Architect** owns AC quality — validates and rewrites as needed
3. **Challenger** (architect's checker) stress-tests the architect's final AC

The planner is a drafter, not a co-owner. The architect is accountable for AC quality. The shared skill (`h-ac-quality` or equivalent) is the single source of truth for what "good AC" means — both planner and architect reference it, but only architect gates on it.

### Joint 3: Reviewer reads source artifacts directly

Reviewer ALWAYS reads test files and implementation code with a "completeness" lens (AC→code mapping). It uses builder's quality-runner output only for pass/fail status, avoiding re-execution. The reviewer does not re-run tests, but it does read code.

This is non-negotiable. The archive analysis shows the reviewer catches default-value fixtures, mock-vs-real shape drift, missing negatives, and fixture limitations. None of these are derivable from quality-runner output alone — they require reading the actual test and implementation source.

### Joint 4: Reviewer→auditor handoff artifact

The brief leaves this as an open question. My position: the reviewer writes a structured **Review Evidence** section in the task body containing:

- **AC completion matrix**: each AC line → PASS/FAIL with file:line evidence
- **Proof quality notes**: per-AC assessment of assertion quality (exact-value, boundary coverage)
- **Flagged concerns**: anything the reviewer noticed but is outside its scope (for auditor attention)

The auditor reads this as the reviewer's *claim* and then runs its own independent checks (full suite, intent alignment). The auditor does NOT re-verify the reviewer's AC completion work — it trusts the matrix and focuses on soundness and integration.

### Joint 5: TestFromAC immutability rule must be revised

The current reviewer auto-FAILs when TestFromAC tests are weakened or removed. This directly conflicts with the structural test lifecycle (task-scoped tests deleted at archival, durable tests created via consolidation). The immutability rule must be revised to: TestFromAC tests in `tests/` (task-scoped) are expected to be deleted at archival. TestFromAC tests in `serve/*/tests/` (durable) retain the immutability guard.

This is a prerequisite change, not a side effect of the restructuring.

## Design Question Responses

### Q1: AC Non-Divisibility Rules

Three concrete rules:

1. **Function-scoped**: Every AC line must name the function or endpoint under test. "The system handles errors correctly" → FAIL. "`parse_config()` raises `ConfigError` when `priority` field is missing" → PASS.

2. **Input→output pairs**: Each AC line specifies at least one concrete input and its expected output. No AC line describes behavior without naming what triggers it and what it produces.

3. **Banned quantifiers**: "all," "every," "correctly," "properly," "exactly matches" are banned unless followed by an exhaustive enumeration. "Handles all error types" → FAIL. "Handles `FileNotFoundError`, `PermissionError`, and `ValueError`" → PASS.

**Quality test**: Can a test-writer derive the exact set of test scenarios from an AC line without ambiguity about what "pass" means? Not necessarily one-to-one (a single AC may require multiple test scenarios — positive, negative, boundary), but the scenario set must be deterministic from the AC text alone.

### Q2: Reviewer Checklist Restructure

**Keep in reviewer** (requires code reading under completeness lens):
1. AC→code mapping: for each AC, does corresponding implementation exist?
2. Test→AC alignment: does each test actually assert on what the AC claims?
3. Proof sufficiency: does the test cover stated behavior with exact-value assertions?

**Scope-creep guard**: these 3 items are the exhaustive reviewer checklist. Any finding outside these 3 is out of scope for reviewer — it goes in "flagged concerns" for auditor attention.

The proof-sufficiency check is the bleed risk between reviewer and auditor. The boundary: reviewer checks *structural* proof quality (does a test exist, does it assert exactly, does it cover the branches named in the AC). Reviewer does NOT evaluate whether the test logic is *correct* — that is semantic and belongs to auditor.

**Move to CI/pre-commit** (mechanical, deterministic):
- Security static analysis (SAST tooling), import cycle detection, type checking

**Note on security**: the brief leaves "move entirely to CI vs. keep opt-in for security-tagged tasks" as unresolved. I recommend moving the mechanical portion (static analysis) to CI and keeping a lightweight security attention-check in reviewer only for tasks explicitly tagged `security`. This is a hedge — full resolution needs empirical data on how often reviewer catches security issues that SAST misses.

**Stays with architect** (pre-implementation gate):
- Architectural fit — architect is now mandatory, so this is checked before building

**Auditor handles**:
- Cross-task regression (full suite run)
- Intent-vs-AC alignment (does implementation satisfy the spirit, not just the letter?)
- Architectural regression (did this change break an existing boundary?)

### Q3: Consolidation-Test Lifecycle

Created during planner's upfront decomposition. Dependencies on all implementation tasks in the feature group. Planner updates dependencies if scope changes. Auditor flags missing consolidation-test as backstop.

The 219 existing stale tests require a migration task as part of this design: move surviving tests to `serve/*/tests/`, delete the rest. This migration must happen AFTER the TestFromAC immutability rule is revised (Joint 5), otherwise the reviewer will auto-FAIL every deletion.

### Q4: Loop-Breaker Restructure

With batching, each review cycle does substantially more diagnostic work than a single-gate failure. The appropriate threshold is likely lower than the current 3, but the exact number needs empirical validation.

**Recommendation**: start at 2 batch-review cycles and adjust based on data.
- Cycle 1: reviewer surfaces all findings. Builder fixes all.
- Cycle 2: reviewer checks fixes, surfaces any residual. Builder fixes.
- If cycle 3 would be needed: escalate to architect for AC refinement. The problem is upstream, not in the builder.

### Q5: Reviewer-Auditor Boundary

| Dimension | Reviewer | Auditor |
|-----------|----------|---------|
| Core question | "Are all AC implemented?" | "Does it actually work and not break anything?" |
| Scope | Per-task, per-AC | Cross-task, cross-boundary |
| Test execution | None (reads builder output) | Full suite run |
| Source reading | Yes — test files + implementation | Yes — implementation + integration points |
| Handoff direction | Writes Review Evidence → auditor reads | Terminal gate |
| Failure class | Completeness gaps | Soundness + regression |

The separation is structurally clean. The remaining bleed risk is "proof sufficiency" — reviewer could drift into evaluating test correctness (auditor territory). The guard: reviewer's checklist is fixed at 3 items, and the skill file must make this boundary explicit with examples of in-scope vs. out-of-scope findings.

## Structural Warnings

1. **Architect cost is real.** The architect uses the most expensive model. Mandatory routing adds per-task cost. The justification is leverage: archive analysis shows 5-10x iteration cost from bad AC, which dwarfs the per-task architect cost. The fast-approve exit (architect reads AC → challenger approves in one pass → move on) minimizes time but not per-invocation cost.

2. **Error-circumvention overhead is adjacent, not orthogonal.** The brief names it as a core cost source. The pipeline restructuring reduces blast radius (fewer cycles = fewer opportunities for tool errors to cascade) but doesn't fix tool reliability itself. This is a lower-priority but real concern that needs a separate workstream.

3. **Temporary implementation lifecycle is an open gap.** Code can't be structurally separated like tests. The AC should explicitly note which implementations are scaffolding. The consolidation task should include replacing scaffolding implementations with durable ones. This needs more design work — the current proposal doesn't fully address it.

4. **Duplicated rule authority needs shared skill.** Planner and architect both reference AC quality rules. A shared skill (`h-ac-quality`) as single source of truth prevents drift. This is a delivery-order dependency: the shared skill must exist before the agent role rewrites.

## Key Trade-offs

| Trade-off | Position | Reasoning |
|-----------|----------|-----------|
| Mandatory architect vs. cost | Always route, fast-approve exit | Archive spirals prove upstream quality is highest-leverage fix |
| One checker vs. two | Two (reviewer + auditor) | Attention contamination in sequential phases within one context is real |
| Reviewer re-runs tests | No re-run, reads source directly | Eliminates most reviewer cost; direct source reading preserves safety |
| Loop-breaker threshold | Start at 2 batch cycles, validate empirically | Batching increases per-cycle diagnostic coverage; exact threshold needs data |
| Consolidation trigger | Upfront planner decomposition | Small maintenance cost beats unreliable state detection |
| Security scanning | SAST to CI, lightweight check for security-tagged tasks | Hedge — needs empirical validation |

## Confidence

0.78

High confidence on: role boundaries (reviewer completeness / auditor soundness), batch-review model, structural test separation, mandatory architect gate, AC quality ownership chain.

Lower confidence on: consolidation-test trigger durability under scope changes (0.65), loop-breaker threshold of 2 vs. 3 (needs data), security scanning placement (0.60), temporary-implementation lifecycle (underspecified).
