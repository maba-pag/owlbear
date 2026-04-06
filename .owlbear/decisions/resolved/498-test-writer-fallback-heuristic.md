---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Content-based heuristic with BLOCK escalation"
notes: "What does `BLOCK with diagnostic note` even mean, processually? who is supposed to know of this how and to what? block is horrible, if no action is assigned, e.g. a user-decision created. Find a new step 4."
# >> Agent metadata (do not edit)
task_id: 498
agent: researcher
created: 2026-03-31
urgency: blocking
decision_type: pipeline-behavior
impact_tier: 3
---

# Decision: Test-writer fallback heuristic for unrecognized non-impl tasks

## Context

When the test-writer encounters a task with no testable Python in the AC and the task
doesn't match non-impl pass-through tags, it stalls silently. Task #467 (create
challenger.agent.md) was tagged `scope:agents` but not `agent` — the test-writer fell
through to codebase search, found nothing, and produced no notes. Gate 4 blocked it
indefinitely. Architect tagging guidance (R2) and Gate 4 exemptions (R1) were
implemented as immediate fixes, but the test-writer itself has no resilience when tags
are wrong.

This is T3 because it modifies `tdd-red/SKILL.md` (agent skill) and
`test-writer.agent.md` (agent file) — pipeline behavior change.

See `docs/research/test-writer-non-impl-fallback-heuristic.md` for full analysis.

## Options

### A: Content-based heuristic with BLOCK escalation <- (rec:) recommended

Add "Step 2a" to tdd-red SKILL.md between Step 2 (search codebase) and Step 3 (plan
categories). After Step 2 finds no testable interfaces:

1. Scan AC for Python implementation intent (keywords: implement, function, method,
   class, module, src/, .py, import, endpoint, API)
2. If implementation intent found: proceed normally (new-module RED phase)
3. If NO intent AND AC references only non-Python files (.agent.md, SKILL.md, .yml,
   etc.): heuristic pass-through with warning note
4. If ambiguous: BLOCK with diagnostic note

Also add a boundary rule to test-writer.agent.md.

- Effort: ~25 lines across 2 files (tdd-red SKILL.md + test-writer.agent.md)
- Trade-off: adds instruction complexity, but catches mistagged tasks automatically
- Risk: keyword heuristic may miss edge cases; BLOCK escalation mitigates this

### B: Mandatory BLOCK on empty Step 2

If Step 2 finds nothing testable, always BLOCK and request manual tag review.

- Effort: ~10 lines in tdd-red SKILL.md only
- Trade-off: zero false-positive risk, but every mistagged task requires manual intervention
- Risk: increases pipeline friction for common non-impl tasks (agent files, skills)

### C: Defer / do nothing

Keep current behavior. Rely on architect tagging (L1) and Gate 4 exemption (L3) as
the only defenses.

- Effort: 0
- Trade-off: test-writer remains brittle when tags are wrong
- Risk: future mistagged tasks stall silently until manual triage

## Recommendation

.85 confidence — Option A. The content-based heuristic matches CI/CD content routing
patterns (GitHub Actions paths-ignore, GitLab rules:changes). The BLOCK escalation for
ambiguous cases prevents silent stalls while keeping pipeline velocity for clear non-impl
tasks. The keyword list is maintainable and the warning note makes heuristic pass-throughs
distinguishable from proper tag-based ones.

## Impact of Deferral

Task #498 is blocked. No auto-resolve — this is a T3 decision that modifies pipeline
agent behavior. No downstream tasks are affected until this is unblocked.
