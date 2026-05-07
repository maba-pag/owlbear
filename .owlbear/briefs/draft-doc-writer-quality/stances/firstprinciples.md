# First-Principles Stance — doc-writer quality

## Irreducible Core

Three claims survive reduction:

1. **Documentation is wrong.** Evidenced: stale orchestrator references, inconsistent type signatures, phantom verification dates.
2. **The current gate does not detect wrongness.** Evidenced: the agent passes files with errors it should have caught.
3. **Something must change.**

Everything else in the framing is inherited structure, not earned from the problem.

## Assumptions Challenged

### 1. "Per-task gating is the right mechanism for doc quality"

**Status: not load-bearing.**

The framing inherits the pipeline shape (task → docs gate → done) and never questions whether documentation correctness should be coupled to task execution. The evidence actually argues *against* this coupling: the root cause is "the README was already wrong before the task ran." A per-task trigger is structurally incapable of fixing pre-existing rot — that's a corpus-level concern, not a task-level one.

The proposal tries to patch this by widening the read scope ("read the entire README"), but this turns a fast gate into a slow gate without changing the trigger. If the doc-writer reads the entire README on every task, it's doing a corpus audit per task — the worst of both worlds: slow enough to be a bottleneck, but still triggered by irrelevant events (a task that changed a test file shouldn't trigger a full README read).

**Reduction:** The real question is "when should doc verification happen?" The proposal answers "per task but bigger." A simpler answer might be "when the doc actually changes, or periodically." The per-task gate's only irreducible job is "did *this task's changes* break a doc claim?" — which is a narrow, fast, automatable check.

### 2. "Reading more will fix verification failures"

**Status: the weakest assumption in the framing.**

The current agent already has the persona of a "technical editor at a regulated-industry publisher." It already has access to the full README. It already has a 7-item checklist. It still stamps "Last verified: 2026-05-05" on a diagram that references a removed component. The failure mode is not "the agent didn't read enough" — it's "the agent rubber-stamps."

The proposal keeps the same mechanism (LLM reads doc, compares to code, reports) but expands input scope. Nothing in the framing addresses *why* the agent will actually verify this time. If the problem is that the LLM doesn't catch stale references when reading a doc, reading more of the doc doesn't fix the capability gap.

**What would be structurally different:** Verification that doesn't rely on LLM editorial judgment. Examples: grep for symbols that were removed in the diff; compare function signatures in README code blocks against actual `ast.parse` output; check that import paths in docs resolve. These are *checkable* claims, not editorial opinions. The framing treats doc verification as an editorial problem when significant parts of it are a structured-comparison problem.

### 3. "Two tiers (fast gate + slow audit) are needed"

**Status: possibly smuggled from a different problem.**

The two-tier model (per-task gate + periodic audit) is borrowed from CI/CD patterns (pre-commit hooks + nightly builds). But documentation isn't code. Code correctness is binary and testable; doc correctness is gradient and subjective. The two-tier split assumes both tiers produce different value. But under the proposal:

- Per-task gate: reads entire README, fixes task-related issues, flags pre-existing issues.
- Periodic audit: reads entire README, fixes everything, reviews diagrams.

The only non-overlapping value of the audit is diagrams and cross-document consistency. Is a separate mechanism justified for those two concerns, or does the tiering add organizational complexity that a single periodic sweep handles better?

### 4. "Module-level docstrings are a doc-writer concern"

**Status: wrong domain.**

Docstring presence is a code-quality concern. It's checkable by `ruff` (D100 family). Docstring *accuracy* is a verification concern, but it's the same verification concern as any other code-adjacent claim — it belongs wherever "does this comment match this code?" belongs. Putting it in the doc-writer blurs the agent's responsibility boundary and adds a code-reading obligation to what should be a documentation agent. If ruff already flags missing docstrings, this is redundant. If it doesn't, enable the rule — don't build an LLM-powered linter.

### 5. "Follow-up kanban tasks are the right sink for pre-existing issues"

**Status: will flood the board.**

The docs are described as "REALLY bad, outdated, and plain wrong." The first honest verification pass will flag dozens of pre-existing issues across 9 package READMEs. Creating a kanban task for each one produces a flood of low-priority doc-debt tickets that will sit in backlog indefinitely — the exact pattern that makes kanban boards useless.

**Reduction:** If the docs need a one-time cleanup, that's a single task ("audit and fix all package READMEs"), not N per-issue follow-up tasks. If the docs need ongoing maintenance, the periodic audit handles it. The follow-up-task mechanism is designed for a world where pre-existing issues are rare exceptions. In this world, they're the majority.

### 6. "Diagram reassignment needs formal ownership transfer"

**Status: over-specified.**

The decision to "remove all diagram responsibility from doc-writer and move to doc-audit" is correct in direction but over-formal in mechanism. The irreducible claim is "the doc-writer should stop doing verification theater on diagrams." The simplest implementation: delete the two diagram checklist items from `w-doc-update`. No ownership ceremony needed. The doc-audit prompt either already covers diagrams or gets a line added.

## What the Framing Gets Right

- Root cause diagnosis is accurate: task-scoped diff checking will never fix pre-existing rot.
- Removing diagram theater from the per-task gate is correct.
- Separating "task-caused issues" from "pre-existing issues" in attribution is a real concern.

## What the Framing Misses

The deepest problem is unaddressed: **why did the LLM fail at editorial verification?** The proposal assumes it failed because it didn't read enough. The evidence suggests it failed because editorial verification is hard for LLMs — they read fluently but don't *check* claims against ground truth without explicit structure. The fix isn't "read more" — it's "check structurally" (symbol existence, signature matching, import resolution) and reserve LLM editorial judgment for things that can't be checked mechanically.

## Confidence

**0.82** — The root cause is solid. The proposed outcomes inherit too much structure from the existing pipeline without testing whether per-task gating earns its place. The "read more, catch more" assumption is the highest-risk element.
