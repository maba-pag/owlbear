# Context — Proof Bundle Taxonomy

## Problem Snapshot

The current `(td:N)` test-depth convention (0/1/2) is a single ordinal controlling five downstream decisions: test creation scope, proof execution scope, review depth, challenger dispatch, and code-reader dispatch. The user's goal is to make the pipeline both faster and higher-quality — not just fix taxonomy accuracy.

**Evidence of friction:**
- `(td:0)` is overloaded: 33 task files use it for executable verification, 53 for artifact/board verification — these need different downstream measures.
- One ordinal conflates test writing, proof execution, review depth, and adversarial challenge — decisions that vary independently.
- Tasks #1391 and #1443 took notably long through the pipeline despite clear scope — the current convention may be routing subagents suboptimally.

**Project type:** existing-feature/refactor — touches r-pipeline-protocol, w-arch-review, w-tdd-red, w-tdd-green, w-code-review, and multiple agent files.

**Open tensions:**
- The user is set on reforming td:x — the question is *how*, not *whether*.
- Primary driver is speed: reduce unnecessary subagent overhead and pipeline friction.
- Quality improvement is a secondary benefit, not the primary motivation.
- Other speed levers (AC count limits, single major AC per file) have already been applied separately.

## Outcomes

**Best realistic outcome:** A proof convention replaces `(td:N)` that makes subagent routing decisions explicit and independent — test creation, proof execution, review depth, and adversarial challenge are separate signals. Architects assign compact labels; downstream agents read only the axis they own. Pipeline throughput improves because low-risk work skips unnecessary subagents without the architect needing to think about routing.

**Minimum viable win:** `(td:0)` overload is eliminated — "no proof" and "existing proof required" are unambiguously distinguished. Downstream agents can tell whether quality-runner needs to run without reading the AC text.

**Scope boundary:** Reforms the convention and routing rules in pipeline skills (r-pipeline-protocol, w-arch-review, w-tdd-red, w-tdd-green, w-code-review), kanban task schema (frontmatter), and agent .agent.md files. Does NOT redesign pipeline stages, rewrite archived tasks, or change agent roles. Legacy mapping is documentation, not migration.

## Leading Candidate for Phase 2

2+2 model: 2 primary axes (test + proof) at task-level, with 2 derivable-with-override signals (review + challenge), plus optional bundles as architect shorthand. This is the middle ground between the input's full 4-axis Option A and the challengers' minimal fix.

## Settled Decisions

- **Task-level annotation.** Per-AC-line td:N moves to task-level. Test-writer reads AC text for assertion granularity.
- **Project type:** existing-feature/refactor.
- **Investment tier:** Shared.
