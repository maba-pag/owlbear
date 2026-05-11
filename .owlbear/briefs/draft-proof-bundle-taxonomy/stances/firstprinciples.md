# First-Principles Stance — Proof Bundle Taxonomy

## Irreducible Claims

These are the claims I cannot reduce further — they survive challenge:

1. **Different tasks require different verification effort.** Some changes need new tests, some need existing tests to pass, some need only lint. This is real variance, not over-categorization.
2. **The td:0 overload is a genuine defect.** "No proof exists" and "existing proof must pass" require different downstream behavior (quality-runner dispatch vs. skip). A single value encoding both forces agents to parse prose to disambiguate. This is the only claim backed by concrete pipeline failures.
3. **Each downstream agent needs exactly one routing answer.** Test-writer: write tests or not (and what kind). Builder/quality-runner: what to run. Reviewer: dispatch code-reader or not. Architect: dispatch challenger or not.

## Borrowed Structure Identified

### 1. "Four orthogonal axes" is borrowed from configuration-management thinking

The proposal frames the problem as a 4-axis configuration space (test × proof × review × challenge). But orthogonality is a design goal, not a discovered property. The current codebase shows these decisions are **correlated by design**:

- `proof:full` → `review:deep` (always, per current w-code-review)
- `test:matrix` → `challenge:required` (nearly always — the same architectural-risk signal drives both)

If two axes are derivable from a third, they aren't orthogonal — they're consequences. The proposal acknowledges this but treats it as an edge case rather than the central problem with the 4-axis model.

### 2. "Named bundles" recapitulate td:N

If the architect picks from `{inspect-only, existing-scoped, existing-regression, smoke, behavioral, critical}`, that's a 6-value enum. The agent then decomposes it into per-axis values. But if 80%+ of tasks use a bundle without axis overrides, the bundles **are** the convention and the axes exist only to explain the bundles. That's isomorphic to td:N with better names and more values — not a structural reform.

Worse: bundles create a naming problem. The architect must learn a vocabulary (`existing-regression` vs `existing-scoped`) where td:N was self-documenting. If agents only read their own axis, no agent ever sees the bundle name at runtime. The bundle is architect-facing shorthand that adds an indirection layer without a downstream consumer.

### 3. Per-AC-line granularity is inherited, not examined

The current system annotates *each AC line* with `(td:N)`. The proposal preserves this without questioning it. But the routing decisions are **task-level**, not line-level:

- Test-writer: processes task if ANY line is td:1+
- Reviewer: dispatches code-reader if MAX depth is td:2
- Architect: dispatches challenger if NOT ALL td:0

Every consumer already aggregates to task-level (max, any, all). Per-line annotation creates work for the architect and complexity for consumers, but the only per-line consumer is the test-writer choosing *how many* assertions to write — and even that maps to a per-task decision (skip / smoke / full-tdd).

## Derivability Analysis

| Proposed axis | Actually independent? | Evidence |
|---|---|---|
| test: none\|smoke\|matrix | **Yes** — this is the primary signal the architect produces | Drives test-writer behavior directly |
| proof: inspect\|scoped\|adjacent\|full | **Partially** — "inspect" vs "scoped" is independent of test, but "full" correlates strongly with test:matrix | Adjacent/full are the same for quality-runner; difference is review depth |
| review: standard\|deep | **No** — currently a direct function of max(td:N). Proposal offers no case where proof:full + review:standard is desirable | Derivable from proof |
| challenge: none\|required | **No** — currently gated on "all td:0". The architect already decides challenge need in Step 2.5. Making it explicit adds a field but not new information | Derivable from test ≠ none OR explicit architect override |

**Net independent axes: 2** (test creation depth, proof execution scope). The other two are derivable defaults with optional overrides.

## The Actual Routing Questions

| Stage | Question | Current signal | Minimal signal needed |
|---|---|---|---|
| Test-writer | "Do I write tests? What kind?" | max(td:N) across AC lines | `test: skip\|smoke\|full` (task-level) |
| Builder/QR | "What do I run?" | max(td:N) + prose "Existing proof required" | `proof: none\|existing\|scoped\|full` (task-level) |
| Reviewer | "Dispatch code-reader?" | td:2 present? | Derivable: `proof == full` |
| Architect | "Dispatch challenger?" | NOT all td:0 | Derivable: `test != skip` OR explicit flag |

## Challenge: Is this a routing problem or a defaults problem?

The speed problem has a simpler root cause: **td:0 tasks that need quality-runner don't reliably get it**, and **td:1 tasks always trigger challenger even when the risk is trivial**.

Two targeted fixes address both without a taxonomy:

1. **Split td:0** into `td:0` (no proof) and `td:0p` (existing proof required, auto-dispatch quality-runner). This eliminates the overload — one character change.
2. **Make challenger dispatch opt-in, not depth-gated.** The architect already evaluates risk. Let them add `(challenger)` when warranted instead of auto-dispatching for all non-td:0 tasks.

These two patches fix the stated problems (speed + td:0 overload) without introducing axes, bundles, or a new vocabulary. The test-writer, builder, and reviewer continue using a familiar ordinal with one new value.

## Recommended Minimal Model

**If the goal is speed improvement and td:0 disambiguation:**

Replace `(td:0)` / `(td:1)` / `(td:2)` with `(td:0)` / `(td:0p)` / `(td:1)` / `(td:2)` and decouple challenger dispatch from depth. Total change: ~20 lines across 3 skills.

**If the goal is a structural reform regardless:**

Use 2 axes (test + proof) at task level, not 4. Derive review and challenge. Drop bundles — they reintroduce the single-enum coupling the reform is trying to escape. Drop per-AC-line annotation in favor of task-level signals, since every consumer already aggregates.

## Confidence

**0.82** — High confidence that 4 axes overfit the problem space and bundles recapitulate td:N. Moderate confidence that the targeted fix (td:0p + opt-in challenger) is sufficient, pending evidence on how often the correlated defaults actually diverge in practice.
