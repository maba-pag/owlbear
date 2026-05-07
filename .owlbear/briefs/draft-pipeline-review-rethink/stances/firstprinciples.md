# First-Principles Stance — Pipeline Review Rethink (Pass 2)

## Revised Irreducible Core

The value of multi-agent checking is **forced attention scoping**, not trust. Each agent doesn't bring "fresh eyes" in a generic sense — it brings a *constrained reading strategy* that surfaces different defect classes because the prompt forces different questions against the same artifact.

- Completeness check: "For each AC, does corresponding code exist?" (structure-mapping)
- Correctness check: "For the code that exists, does it actually satisfy the claim?" (logic-tracing)
- Integration check: "Does this change break assumptions held elsewhere?" (cross-boundary reasoning)

These are genuinely different cognitive operations with different optimal context-window allocations. The empirical data confirms: collapsing them into one pass degrades detection because the agent's attention budget gets split.

**Revised irreducible structure: 2 post-implementation perspectives + CI.** Not 1.

## Assumptions Challenged (Pass 2)

### 1. "Reviewer catches completeness, auditor catches correctness" — but is the BOUNDARY correctly drawn?

The current split: reviewer = AC completeness + mechanical re-verification, auditor = intent alignment + regression.

A cleaner split exists: **completeness** (did you build all the things?) vs. **soundness** (do the things you built actually work together?). The current reviewer bleeds into soundness territory (adversarial 8-checks, security scanning) while the auditor bleeds into completeness (spot-checking AC). The boundary is fuzzy because it was drawn by accretion, not design.

Challenge: **the problem is not the number of layers but the impurity of each layer's mandate.** Each checker should own exactly one failure class and own it completely.

### 2. "Tagging" solves the lifecycle problem — but tagging is the SECOND simplest solution, not the first

The 219 stale tests exist because:
- Task-scoped tests mock dependencies that get implemented later
- No lifecycle event triggers cleanup

Tagging adds metadata. Metadata must be maintained. Tags drift. The SIMPLEST solution: **task-scoped tests live in the task file itself** (or a dedicated `tests/task/` directory) and archival deletes the directory. No metadata to maintain — the lifecycle is structural, not semantic.

If structural separation is too costly, tagging is the next best. But test this claim: why CAN'T task-scoped tests be structurally separated from durable tests? If the answer is "pytest discovery" or "import structure," those are solvable. If the answer is "some task tests BECOME durable tests," that's the real problem — and tagging handles that transition better than structure.

**Irreducible requirement:** at archival, task scaffolding dies automatically. Tagging is ONE mechanism; structural separation is another. The decision should be: which has lower maintenance burden over 100 tasks?

### 3. "Architect must always run" — but what IS the architect actually checking?

The architect's stated job: "audit and rewrite AC to be specific + testable." First-principles decomposition:

- Is the AC *complete* given the intent? (Coverage)
- Is the AC *testable* as written? (Formulation quality)
- Is the AC *achievable* given the codebase? (Feasibility)

The first two are language operations on the task description. The third requires codebase knowledge. Only the third justifies a separate agent invocation with tool access.

Challenge: **if planner had access to codebase context (via search tools), would it write good-enough AC that architect only needs to validate, not rewrite?** The current skip-path data is tainted — tasks that skip architect are probably simpler tasks that would succeed regardless. The architect's value is untested on complex tasks because it was never consistently applied.

The honest answer: you can't know if architect is necessary until you consistently apply it and measure defect rates with vs. without. The current data doesn't prove it's necessary — it proves skipping it on simple tasks doesn't hurt. That's a different claim.

### 4. "Fresh context catches blind spots" — this is correct but UNDERSTATES the mechanism

Fresh context isn't just "another roll of the dice." It's **forced re-reading under a different question.** Builder reads code asking "does this pass tests?" Reviewer reads code asking "does this cover all AC?" Auditor reads code asking "does this break anything else?"

These are not probabilistic retry. They are deterministic attention-direction changes. The value model is:

```
V(agent_n) = P(defect_class_n | attention_direction_n) - P(defect_class_n | already_caught)
```

If each agent catches a genuinely orthogonal defect class, you DON'T get diminishing returns — you get additive coverage. The diminishing returns come from OVERLAP in attention direction, which is exactly what the current system has (reviewer re-running tests = same attention direction as builder).

**The fix is not fewer agents but purer attention mandates.**

### 5. "Per-usage pricing changes the calculus" — only if cost is per-token, not per-defect

The ROI framing: reviewer at 3x cost catches 80% of defects. But what's the cost of an uncaught defect?

- If uncaught defect = rework at 10x cost: reviewer ROI = (0.8 × 10x) / 3x = 2.67x return
- If uncaught defect = user catches it in 5 minutes and files a task: reviewer ROI = (0.8 × 1x) / 3x = 0.27x return

The question is not "does reviewer catch things" but "how expensive are the things it catches to fix later?" In an AI agent system with fast rebuild cycles, the rework cost may be MUCH lower than in human software engineering. A missed AC doesn't compound into months of wrong-direction work — it becomes a 2-minute rebuild once flagged.

Challenge: **the rework cost model from human engineering may not apply.** If rework is cheap (just re-run builder), the economic case for expensive pre-emptive checking weakens. The irreducible economic question: is `cost(reviewer) + cost(auditor)` < `P(defect) × cost(rework)`? If rework is a 5-minute builder re-run, and defect rate without checking is 30%, you need checking to cost less than 0.3 × (5 min builder cost). Currently reviewer costs 3x builder, which means reviewer alone exceeds the rework budget unless defect rate without it would be >60%.

### 6. The builder-tags-expiry concept has a hidden assumption

"Builder tags temporary implementations with expiry" assumes builder KNOWS what is temporary. But builders don't — they implement what tests demand. A builder has no horizon beyond the current task. Temporary-vs-permanent is an ARCHITECTURAL judgment that requires knowing the roadmap.

This tag should come from the planner or architect (who wrote the AC knowing what's temporary scaffolding vs. target architecture), not the builder.

## What Survived My First Pass Intact

- "Never trust upstream" IS cargo-culted — the value is attention-direction, not trust
- Auditor's test re-run IS redundant with CI (this claim strengthened by data)
- The complexity-scaling classification problem remains real

## What My First Pass Got Wrong

- "1 checking agent + CI" — insufficient. Empirical data shows 2 orthogonal attention-directions catch genuinely different defect classes
- "Test-writer is ceremony" — wrong. The empirical data showing both miss AC individually when merged is decisive. Separate attention on "what should we test?" vs. "how do we implement?" produces better coverage
- "Architect is optional" — insufficiently tested claim. The skip-path data is biased toward simple tasks

## Minimum From-Scratch Design (Revised)

1. **Planner:** Intent + tagged AC (marks which AC are scaffolding vs. durable; marks temporary implementation needs)
2. **Architect:** Mandatory. Validates feasibility against codebase. Rewrites AC only when untestable. Light gate, not full design pass.
3. **Test-writer:** Writes tests. Places task-scoped tests in structurally separable location OR tags them. No merge with builder.
4. **Builder:** Implements. Does NOT tag things — it has no lifecycle visibility.
5. **Checker (singular):** Two-phase prompt. Phase 1: completeness scan (AC → code mapping). Phase 2: soundness scan (logic trace on flagged areas only). Self-escalates to full soundness scan on complex tasks. NO test re-run.
6. **CI:** Full regression suite. Not an agent.
7. **Archival hook:** Deletes task-scoped tests (by structure or tag).

Key difference from current: **one checker with two attention phases replaces reviewer + auditor.** The phases are sequential within one invocation, not separate agents. This preserves the orthogonal-attention benefit while halving the context-load cost (no redundant codebase ingestion for a second agent).

## Open Question I Cannot Resolve

Can a single agent reliably execute TWO different attention strategies in sequence within one invocation? Or does the first phase's findings contaminate the second phase's attention? If contamination is real, two separate agents remain necessary — but with pure, non-overlapping mandates and NO mechanical re-verification in either.

## Confidence

0.71 — Lower than pass 1. The empirical data genuinely constrains the solution space. I'm confident the current boundaries are wrong (reviewer/auditor overlap is waste), but uncertain whether the fix is "one agent, two phases" or "two agents, pure mandates." The answer depends on whether sequential attention-direction changes within one context window actually work, which needs testing.
