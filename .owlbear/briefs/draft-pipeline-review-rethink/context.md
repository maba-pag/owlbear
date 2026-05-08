# Context — Pipeline Review Rethink

## Problem Statement

The agentic pipeline's quality gates are misaligned between their stated purpose and their mechanical operation. The result is disproportionate token spend, excessive wall-clock time (reviewer ~3x any other agent), high failure/retry rates, and 219 stale task-scoped tests accumulating as zombie assertions.

The deeper issue is not "checking is too expensive" but "the checking layers are doing work that doesn't match their actual value proposition":

1. **Reviewer** — stated value: "verify AC are implemented." Actual operation: runs full test suite (duplicating builder), dispatches code-reader for 8 adversarial checks, produces evidence tables, confidence scoring. The AC-comparison work (its real value) is buried under mechanical verification the builder already did.

2. **Auditor** — stated value: "verify intent behind AC, catch cross-task regressions." Actual operation: spot-checks AC (light), runs full suite (heavy), scores architect quality. The intent-vs-AC check (its unique value) gets minimal depth while the full test run duplicates what reviewer should have already validated.

3. **Architect skip** — many tasks bypass the architect entirely (planner moves to `todo` directly). This means the "are these the right AC for the intent?" question goes unasked until the auditor — after all implementation and review work is done. The auditor then scores architect quality on AC that no architect ever reviewed.

4. **Test lifecycle gap** — task-scoped tests (`TestFromAC_*`) are born during RED phase as scaffolding for the builder. 60% rot naturally even when implementation proceeds as planned (they mock later-implemented dependencies). They have no defined end-of-life — the pipeline produces scaffolding it never cleans up.

5. **Error circumvention overhead** — significant token waste from agents retrying operations in multiple ways when tools fail, rather than the checking logic itself.

## Project Type

existing-feature/refactor

## Affected Components

- Reviewer agent + skills (`w-code-review`, `w-task-verification`)
- Auditor agent
- Architect agent (skip path via planner)
- Test-writer agent (task-scoped test lifecycle)
- Quality-runner subagent (mechanical execution layer)
- Code-reader subagent (dispatched for td:2 only)
- Planner agent (task routing, architect bypass)
- Orchestrator (dispatch sequencing)
- Pipeline protocol (`r-pipeline-protocol`)
- TDD RED/GREEN workflow skills

## Observed Overlaps and Misalignments

| Step | Who runs tests? | Purpose | Overlap |
|------|----------------|---------|---------|
| RED | test-writer via quality-runner | Verify tests FAIL | None |
| GREEN | builder via quality-runner | Verify tests PASS | None |
| Review | reviewer via quality-runner (scoped) | "Independent" verification | Duplicates builder's run |
| Audit | auditor via quality-runner (full) | Cross-task regression | Genuine unique value |

| Check | Reviewer | Auditor | Architect | Gap? |
|-------|----------|---------|-----------|------|
| AC implemented? | Primary job | Spot-check only | N/A | None |
| Tests sound? | Yes (5.0-5.3) | Trust reviewer | N/A | None |
| AC match intent? | No | Yes (unique value) | Should do, but often skipped | GAP |
| Cross-task regression? | No (scoped run) | Yes (full run) | N/A | None |
| Security? | Yes (5.1) | No | No | None |
| Architecture fit? | No | Scores quality | Primary job (when not skipped) | MISALIGNMENT |

## Active Tensions

- Defense-in-depth (3 layers) vs. unsustainable total cost
- Reviewer's real value (AC gap detection) vs. its mechanical overhead (re-running tests, 8-check code-reader)
- Auditor's unique value (intent alignment + regression) vs. re-checking what reviewer already checked
- Architect as quality gate vs. planner bypassing architect
- Task-scoped tests as TDD scaffolding vs. permanent test debt
- Error retry overhead vs. inherent checking complexity
- "Never trust upstream" philosophy vs. diminishing returns of re-verification
## Key User Observations (empirical, not theoretical)

1. **Before reviewer depth increase:** reviewer rubberstamped builder work, auditor found real flaws. **After increase:** reviewer catches ~80% of flaws, auditor rarely catches anything now.

2. **Finding types are distinct:** Reviewer finds = "not fully implemented AC" (missed requirements). Auditor finds = "logic flaws" (implementation is wrong even when AC are nominally met). These are genuinely different failure modes.

3. **Builder's feedback loop works well.** Builder is 2nd longest agent (~2x others) but the quick build-check-rebuild cycle is high-value. The 3x reviewer cost is the problem, not the builder.

4. **Re-running tests has little value.** Agents have been seen trying to cheat, but subagent delegation already prevents this practically.

5. **Scope is holistic — all checking agents need role redefinition.** Not just the reviewer. Root causes and role clarity for each agent in the chain.

6. **Tagging is an unexplored lever:** test-writer should tag narrow task-tests for deletion vs. survival. Builder should tag temporary implementations with expiry. This creates the lifecycle management that's currently missing.

7. **Cost model change imminent:** Moving from per-prompt to per-usage pricing. Cost optimization becomes directly financial, not just velocity.

8. **Test-writer stays separate from builder.** Both already miss AC individually — merging would worsen quality. Merging test-writer into architect makes conceptual sense (full AC context) but financial nonsense (architect uses most expensive model).

## Archive Analysis: Multi-Iteration Task Patterns

Analysis of the 5 most-iterated archived tasks (#1171, #1229, #1252, #1039, #1332) reveals:

### The iteration spiral pattern
- Tasks that spiral don't spiral because of missed AC implementations — they spiral because of **proof quality escalation**. The reviewer finds subtler test-quality issues each round (default-value fixtures, mock≠real shape, missing negatives, single-scenario fixtures).
- Each round costs a full agent cycle (reviewer → architect/test-writer → builder → reviewer). 4-5 rounds = ~20x the cost of a single review.
- The loop-breaker activates after 3 FAILs — often too late.

### Root causes are upstream
- Bad AC: untestable internal-state requirements, vague behavioral clauses
- Bad fixtures: default-only, single-scenario, mock shapes diverging from real objects
- Proof scope creep: reviewer keeps discovering deeper proof gaps that should be separate follow-up tasks, not blocking the current one

### Reviewer value is real but the feedback loop is wasteful
- The reviewer's catches are genuine quality improvements (false-green prevention, boundary proof, exact-value assertions)
- But "catch one issue, re-run entire pipeline, catch next issue" is multiplicatively expensive
- A single reviewer pass that identifies ALL issues at once (rather than gating on the first failure) would dramatically reduce round-trips

### Cross-task pattern summary
| Issue | Impact | Fix direction |
|-------|--------|---------------|
| Default-value fixtures | False-green tests | Test-writer must vary fixtures |
| Mock ≠ real shape | Boundary bugs hidden | Use real objects in boundary tests |
| Proof scope creep | Loop escalation | Architect separates "implementation complete" from "proof depth" |
| Untestable internals | Review loop on unprovable clauses | AC must describe observable contract only |
| Round-trip normalization | Masks lossy behavior | Compare raw output, not re-serialized |
| Fixture limitations | Can't prove multi-scenario AC | Fixtures must cover all AC branches |

## User's Proposed Test Lifecycle Solution

Instead of tagging:
1. **Task-scoped tests** live in `tests/` with `_{task_id}` naming → always deleted at archival
2. **Module/durable tests** live in `serve/*/tests/` (package-local) → survive indefinitely
3. **Planner creates a final "consolidation test" task** at the end of each feature chain → this task creates/updates durable module tests based on the full feature's work
4. Structural separation eliminates need for metadata/tagging infrastructure

## Locked Outcomes

1. **Planner cannot create unchecked AC** — all tasks must route through architect before implementation
2. **Architect produces explicit, enumerated, observable AC** — named functions not concepts, no infinitely-divisible wording
3. **Reviewer batches all findings** — returns complete fix list instead of gating on first failure (prevents 5x partial runs vs 2x full runs)
4. **Reviewer stops re-running tests** — reads builder's quality-runner results, does not re-execute
5. **Test lifecycle: structural separation** — task tests in `tests/` (deleted at archival), durable tests in `serve/*/tests/`. Planner creates a final consolidation-test task per feature chain
6. **Test-writer defaults to exact-value assertions** — no substring, no presence-only checks
7. **Auditor focuses on regression + intent** — full suite run, intent-vs-AC alignment, logic flaws
8. **Every agent gets role sharpening** — purer mandates, clear handoff contracts, no overlapping checks

## Checker Subagent Mental Model

The pipeline already follows a pattern where each agent has (or could have) a **checker subagent** that validates its output before handoff:

- **Builder → Reviewer** — the reviewer IS the builder's checker, externalized into its own pipeline stage because the builder already does too much work. Stays externalized because: (1) combining the two longest agents blocks parallel work; (2) reviewer rejects to test-writer or architect, not just builder.
- **Architect → Challenger** — already exists in `w-arch-review/SKILL.md` Step 2.5. Validates design decisions before approval.
- **Test-writer** — checker dropped (minimal value).
- **Researcher** — checker dropped.
- **Doc-writer** — checker dropped (cost/benefit insufficient).
- **Auditor** — THE big-picture pipeline gate, not a checker but a cross-cutting verifier.

**Key design principle:** The optimization is "refocus existing checkers," not "add new ones."

### Architect Checker Enhancement

The architect's checker (challenger) should expand to validate **AC quality**, not just design decisions. When architect receives a task with planner-created AC:
1. Architect sees AC, sees no immediate rewrite task
2. Hands off to checker subagent to validate AC quality
3. Acts on checker output: if checker flags issues → architect rewrites AC; if checker approves → architect ends work

This works IF the planner follows the same AC quality rules as the architect — so planner creates AC that are already close to the standard, and the architect's checker catches the remaining gaps without the architect doing redundant review of already-good AC.

## Refined Role Table

| Agent | Core job | Checker | Distinct value | Key change |
|-------|----------|---------|----------------|------------|
| Planner | Write clear intent + AC using architect's quality rules | None | Task specification quality | Follows same AC quality skill as architect; MUST route through architect |
| Architect | Fix AC only when checker flags them; validate feasibility | Challenger (expanded to AC validation) | AC quality gate (mandatory) | Checker-first workflow; no redundant review of good AC |
| Test-writer | Write tests with exact-value assertions; structural separation | None (dropped) | Test scaffolding with clear lifecycle | Default to exact-value, no substring/presence-only |
| Builder | Implement + fast feedback loop (self-checks via quality-runner) | Reviewer (externalized) | Implementation quality | No change to builder's own loop |
| Reviewer | Return ALL findings in one pass (batch, not gate). Check missed AC, proof quality | N/A (IS the checker) | AC completion verification | Stop re-running tests; batch all findings |
| Doc-writer | (Out of scope — needs separate rebuild) | None (dropped) | Documentation accuracy | Separate effort |
| Auditor | Full suite regression, intent alignment, logic flaws | N/A (pipeline gate) | Cross-cutting sanity | Focus on unique value only |