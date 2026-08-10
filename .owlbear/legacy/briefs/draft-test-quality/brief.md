# Test Lifecycle Management

## Investment Tier: Shared

## Problem

The TDD pipeline generates task-scoped test files that verify narrow implementation details of individual kanban tasks. These tests accumulate without curation — no consolidation, no pruning, no promotion, no expiration. Over time, the test suite becomes dominated by stale, task-coupled assertions that:

- **Waste time:** Hundreds of tests take minutes to run, blocking agent dispatch cycles.
- **Destroy signal:** When a module is improved, stale task-scoped tests break. Agents can't distinguish pre-existing noise from real regressions they caused.
- **Corrupt behavior:** Agents learn to dismiss test failures as "probably not my fault," eroding the TDD feedback loop entirely.

Root causes: (1) conventions for module-level testing exist on paper but aren't enforced; (2) RED/GREEN agents run only task-scoped tests — full-suite runs happen only at the auditor stage; (3) no test lifecycle mechanism exists — tests are born and never evaluated for lasting value; (4) TestFromAC immutability rules prevent reviewers from consolidating or pruning during review.

## Outcomes

1. **Green suite = trust.** A failing test triggers investigation, not dismissal.
2. **Fast suite.** Full suite under 60 seconds.
3. **Automated lifecycle.** Task-scoped tests are transient scaffolding; only contract-level module tests persist. No manual cleanup needed.
4. **Right-sized suite.** Test files map to modules, not tasks. Suite stays proportional to codebase size.
5. **Coverage floor.** ≥ 90% per curator operation on touched modules (target 95% at steady state).

## Approach

### Nuclear reset + lifecycle curator

Delete all existing tests. Introduce a **test curator agent** as a new pipeline stage operating **post-archive**. The curator consolidates task-scoped tests into durable module-level files, promoting only contract-level assertions. A two-tier test model replaces the current flat accumulation.

### Why this approach

The existing test suite is beyond curation — 83% task-numbered files with uncertain value. Automated triage is more complex than starting fresh. The nuclear reset gives immediate relief (zero noise, fast runs) while the curator prevents re-accumulation. Coverage rebuilds organically as modules are actively developed.

### Two-tier test model

| Tier | Files | Lifespan | Authority |
|------|-------|----------|-----------|
| **Task-scoped** (transient) | `tests/test_{module}_{task_id}.py` | Active pipeline only | Test-writer creates, builder implements, reviewer validates. Immutable during pipeline. |
| **Module-level** (durable) | `tests/test_{module}.py` | Permanent (subject to future lifecycle) | Curator promotes from task-scoped. Contract-level assertions only. |

### Curator agent

- **Pipeline position:** Post-archive. After a task is archived, the curator evaluates its task-scoped test file.
- **Non-blocking:** The curator must not slow down the build pipeline. It runs asynchronously — either in parallel with non-test-touching agents or as a separate background process. It never gates the next task from starting. The exact integration pattern (parallel dispatch, queue-based, triggered on archive) is a design decision to be surfaced as a user-decision (action request) during implementation.
- **Authority:** Can promote assertions to module-level files, remove task-scoped files, and prune redundant assertions. Gated by green suite + coverage ≥ 90% on touched modules.
- **Quality gate:** Promotion requires contract-level classification. Implementation-coupled assertions (testing internal state, private methods, specific mock configurations) are not promoted — they served their purpose during the task and are discarded.
- **AC provenance:** Promoted assertions carry a comment or docstring linking to the original AC (e.g., `# From task #553: AC-2 — bookmark dedup on URL`).
- **Atomic operations:** Curator works module-by-module. Each module-batch must leave the full suite green with coverage ≥ 90%. Git revert on failure.
- **Lifecycle log:** Append-only JSONL log of all curator operations for diagnostics and auditability.

### Scoped TestFromAC immutability

- **During active pipeline** (task creation → archive): `TestFromAC_*` classes remain immutable. Builder cannot weaken or remove. Reviewer validates immutability. (No change from current rules.)
- **Post-archive:** Curator gains authority to promote, consolidate, or remove assertions. This is a new authorized capability — agents can now permanently remove test assertions, gated by safety mechanisms.

### Builder visibility expansion

- Builders run **both** the task-scoped test file **and** the module's durable test file (if it exists) during GREEN phase.
- Not full-suite — just the affected module's durable tests alongside the task tests.
- Provides early signal on cross-task regression without full-suite cost.

### Alternatives Considered

- **Mechanical promotion only (no quality gate):** Rejected. Moves noise from task files to module files without improving trust. End-User and Data panelists argued convincingly that promotion without semantic quality improvement perpetuates the problem.
- **Human-gated deletion:** Rejected. Creates a bottleneck and defeats the zero-curation outcome. Safety gates (green suite + coverage floor) provide sufficient protection.
- **Curator bootstrap of legacy files:** Rejected. More complex than starting fresh. User has demonstrated willingness to bulk-delete.
- **Forward-only (no legacy cleanup):** Rejected after Critic challenge. Leaves legacy noise in place, preventing trust/speed improvements while adding process overhead to new work.

## Scope

**In:**
- Delete all existing test files (one-time human action)
- Test curator agent (new pipeline stage, post-archive)
- Two-tier test model (conventions, naming, file placement)
- Scoped TestFromAC immutability (convention update to w-tdd-red, w-code-review)
- Builder visibility expansion (convention update to w-tdd-green)
- Quality gate on promotion (contract-level classification)
- AC provenance preservation
- Hard gates (green suite + coverage floor) with git revert
- Lifecycle log (append-only JSONL)

**Out:**
- Module-level test lifecycle (durable tests also go stale — known future concern, separate brief when it materializes)
- Full callable-level data model / AC scenario tracking (Data panelist's progressive enrichment tiers — deferred)
- Independent verification of curator operations beyond auditor spot-checks
- Changes to test-writer behavior (task-scoped tests are correct output)

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Coverage gap after nuclear reset | Coverage rebuilds as modules are actively developed. 90% floor applies per curator operation, not globally during rebuild. Accept temporary gap. |
| Curator makes wrong promotion/removal decisions | Conservative "when in doubt, promote" policy. Atomic module-batch operations with git revert. Append-only log for diagnostics. |
| Silent behavioral assertion loss within maintained coverage | Acknowledged as irreducible. Green suite + coverage floor ≠ behavioral preservation. Design does not overclaim. Auditor spot-checks provide partial mitigation. |
| Contract-level classification is ambiguous | Start with heuristics (assertion targets: public API = contract, internal state = implementation). Refine over time. Ambiguous cases promoted (conservative). |
| Module-level tests also accumulate over time | Known future concern. Not in scope. Monitor and address when it materializes. |

## Key Decisions

| Decision | Choice | Trade-off |
|----------|--------|-----------|
| Quality gate on promotion | In v1 — contract-level required | Slower to ship, but solves trust problem |
| Agent deletion authority | Accepted post-archive | New capability; silent assertion loss possible |
| Builder visibility | In scope | Small scope increase for big signal improvement |
| Legacy approach | Nuclear reset | Temporary 0% coverage; immediate noise relief |

## Context

- Pipeline: `w-tdd-red` → `w-tdd-green` → `w-code-review` → `w-task-verification` → **new: curator**
- Affected skills: `w-tdd-red`, `w-tdd-green`, `w-code-review`, `w-task-verification`, `h-python-conventions`, `r-project-standards`
- Existing markers: `api`, `slow`, `integration`, `e2e` — no lifecycle markers currently
- Coverage config: `source_pkgs` in pyproject.toml covers all workspace packages
- Test runner: pytest with xdist (`-n auto`), strict asyncio mode, importlib import mode
