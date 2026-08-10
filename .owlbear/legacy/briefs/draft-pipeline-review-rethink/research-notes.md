# Research Notes — Pipeline Review Rethink

## Verified Findings

### 1. Archive Iteration Analysis

The 5 largest archived tasks by line count are the worst iteration offenders:

| Task | Lines | Review cycles | Root causes |
|------|-------|--------------|-------------|
| #1061 (kanban migrate entry point) | 2036 | 10+ rounds, 6 FAILs, 3 loop-breakers, 6 architect refinements | Vague AC ("match §5.3/§5.4 exactly"), infinitely divisible wording |
| #1050 (storage surface tests) | 1656 | 8 FAILs, 5 architect reviews | Vague AC + test weakness + reviewer scope creep + cross-task regression |
| #1053 (engine storage integration tests) | 1464 | 6+ FAILs, 4 architect refinements | Path ambiguity (which `load_config()`?) + vague AC semantics |
| #1064 (boundary test updates) | 2247 | 3 FAILs → PASS | Test weakness (scanner assumptions, missing proof) |
| #1034 (ideation panel diagram) | 2552 | Not a code task (diagram) — different pattern |

**Spiral root causes across all worst-case tasks:**
- Vague AC wording: 5/5 tasks — "exactly," "all modes," "independent," "correct values" are infinitely divisible
- Substring/presence-only test assertions: 4/5 tasks — tests pass on partial matches, reviewer catches false-green one at a time
- Path ambiguity: 3/5 tasks — AC says "at config load time" but doesn't name which function
- Reviewer scope creep: 2/5 tasks — reviewer raises concerns not in any AC, consuming architect-override cycles

### 2. Reviewer Value is Real but Delivery is Wasteful

- Before reviewer depth increase: reviewer rubberstamped, auditor found flaws
- After depth increase: reviewer catches ~80% of flaws, auditor rarely catches anything now
- Finding types are genuinely distinct: reviewer = "not fully implemented AC" (completeness), auditor = "logic flaws" (correctness)
- But: reviewer currently gates on first critical failure → causes 5x partial pipeline runs vs 2x full runs
- Gate-on-first-failure was intentional (save time per run) but counterproductive at scale

### 3. Test Lifecycle

- 219 stale test failures across 39 files are task-scoped tests that rot
- 60% rot naturally (mocking later-implemented dependencies), 40% from project direction changes
- Test files already carry `_{task_id}` in filenames → structural deletion at archival is feasible with zero new infrastructure
- Reviewer currently guards TestFromAC_ immutability (WEAKENED/REMOVED = auto FAIL) — perverse incentive against cleanup
- Re-running tests in reviewer has little value — subagent delegation already prevents cheating practically

### 4. Agent Architecture Observations

- Builder feedback loop (build→check→rebuild) works well at 2x other agents — not the problem
- Reviewer at 3x is the cost bottleneck — all three pain dimensions equally (token cost, velocity, failure rate)
- Planner creates most tasks and AC; architect is often bypassed (planner routes directly to `todo`)
- Test-writer stays separate from builder — empirical: both miss AC individually; merging worsens quality
- Per-usage pricing imminent — cost optimization becomes directly financial

### 5. Early Challenger Insights (Pass 2)

- **Value model:** Multiple checking agents provide "forced attention scoping" (deterministic attention-direction), not "fresh eyes" (probabilistic). Each agent forces attention to a specific dimension that would be diluted if combined.
- **"Never trust upstream" is cargo-culted:** Builder and reviewer are the same model — no incentive divergence. The real value is context-refresh, not distrust.
- **Structural separation > tagging:** Task-scoped tests in `tests/` with `_{task_id}` naming (deleted at archival), durable tests in `serve/*/tests/` (survive). Zero metadata infrastructure needed.
- **Builder should NOT tag:** Builder has no lifecycle visibility — lifecycle decisions belong to planner/architect.
- **Reviewer/auditor boundary is impure, not wrong in number:** Fix purity of mandates, not count.
- **Rework cost model:** If rebuild is a 5-min agent run (1.5-3x cost), heavy pre-emptive checking has lower ROI than in human engineering (10-100x rework cost). Lighter checking + cheaper rework might outperform heavy prevention.

## Candidate Implications

1. **Upstream AC quality improvement has highest leverage** — prevents multi-round spirals at source. Every vague AC word multiplies downstream cost.
2. **Reviewer batching (not gating) could cut review iterations 50-80%** — single pass identifies all issues, single fix cycle addresses all.
3. **Structural test separation eliminates metadata infrastructure need** — the naming convention already exists.
4. **Mandatory architect gate adds per-task cost but prevents downstream spirals** — net savings based on archive evidence.
5. **Consolidation-test task at end of feature chain** cleanly handles durable test creation.
6. **Security scanning may be better as CI/pre-commit** than as per-task cognitive work (first-principles suggestion — needs validation).
7. **"Never trust upstream" → "verify from a different attention direction"** — reframing the philosophy preserves the value while eliminating redundant mechanical checks.

## Open Research Questions (for Mediation)

1. What exactly should the reviewer check beyond AC completeness? Define the exhaustive checklist.
2. How should architect AC quality rules change specifically? What constitutes "enumerated, observable AC" in practice?
3. Does the planner need structural code changes or just routing policy to force architect gate?
4. What triggers the consolidation-test task? At feature completion? At archival? Per parent task? Per feature chain?
5. Loop-breaker threshold: should it move from 3 FAILs to 2? Or restructure as "1 FAIL with fix-ALL-findings instruction"?
6. Should security scanning move entirely to CI/pre-commit, or keep as opt-in reviewer check for security-tagged tasks?
7. Auditor architect-quality scoring: keep, simplify, or remove? (Currently scores AC quality that no architect may have written.)
8. How to handle the existing 219 stale tests? One-time cleanup task, or gradual as tasks are archived?
9. Reviewer skill file (`w-code-review/SKILL.md`): simplify in-place or full rewrite?
10. What is the handoff artifact between reviewer and auditor? (Currently reviewer writes Review Evidence section in task body — is this the right contract?)
