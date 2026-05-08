# Data Quality Stance — Pipeline Review Rethink

## Data Quality Stance

AC is the pipeline's primary schema contract, but not its only one. Every downstream agent parses AC as structured input and produces artifacts shaped by it. The current pipeline has no validation boundary at the point where AC enters the system. Vague AC propagates through test-writing, building, and reviewing — each consumer interprets ambiguity differently, and failures surface 3-5 stages downstream.

The archive data is strong but multi-causal: 5/5 worst-iteration tasks had vague AC, but spirals were compounded by proof-quality defects (default-only fixtures, mock≠real shape, single-scenario coverage) and reviewer scope creep. AC quality is the highest-leverage single fix — it's the input that shapes everything downstream — but it does not eliminate proof-quality and fixture-quality failures, which are orthogonal defect classes.

The pipeline has three data contracts that need explicit schemas, not just one:
1. **AC contract** (planner/architect → downstream) — the specification schema
2. **Evidence contract** (builder → reviewer → auditor) — the verification data chain
3. **Lifecycle contract** (planner → consolidation-test task) — the knowledge preservation handoff

## Schema and Validation Reasoning

### AC Schema: Two Tiers, Not One Template

A single rigid predicate template (`function(inputs) → output [when condition]`) works for code-behavior AC but fails for process-behavior AC. The locked outcomes in this brief include workflow predicates ("Planner cannot create unchecked AC," "Reviewer batches all findings") that cannot be forced into function-call form without distortion.

**Tier 1 — Behavior AC** (code changes):
- Must name a specific function, method, endpoint, or command
- Must specify input conditions and expected observable output
- No adjectives without metrics; no unbounded quantifiers without enumeration
- No internal-state references — only externally observable behavior

**Tier 2 — Process AC** (workflow/role changes):
- Must name the specific agent, stage, or artifact affected
- Must specify the observable change in pipeline behavior (e.g., "architect always runs before test-writer" → verify via task-state transition log)
- Must be verifiable by artifact inspection or stage-transition audit, not by reading agent "intent"

Both tiers share one rule: **every AC line must be independently verifiable by a downstream agent without access to the author's intent.** If verification requires asking "what did the architect mean by this?" — the AC is malformed.

The architect's checker validates AC against these tier-appropriate rules. Malformed AC triggers architect rewrite (not rejection back to planner — the architect owns AC quality, as the brief's role model specifies).

### AC Schema Does NOT Solve Proof-Quality Failures

The archive shows that well-formed AC can still produce spiral iterations when:
- Test-writer uses default-only fixtures (false-green on happy path)
- Test-writer uses mocks that diverge from real object shapes
- Test-writer proves only one scenario for multi-branch AC
- Reviewer discovers these one-at-a-time instead of batching

These are proof-quality defects, not AC-quality defects. They require separate remediation:
- Test-writer skill must require multi-scenario fixtures and real-object-shape validation for boundary tests (locked outcome #6 addresses part of this with exact-value assertions)
- Reviewer batching (locked outcome #3) addresses the one-at-a-time discovery pattern

The AC schema prevents the upstream cause (vague specification); test-writer discipline prevents the midstream cause (weak proof); reviewer batching prevents the downstream amplification. All three are needed.

### Evidence Handoff: Structured Blocks with Provenance

**Builder → Reviewer contract:**

The builder's quality-runner appends a standardized evidence section to the task body. Required fields:

| Field | Purpose | Type |
|-------|---------|------|
| `run_id` | Unique identifier for this quality-runner invocation | string |
| `commit` | Git commit SHA the evidence was generated against | string |
| `timestamp` | ISO 8601 timestamp | string |
| `test_results` | Per-test-function pass/fail with assertion detail on failure | structured list |
| `coverage_summary` | Line/branch coverage for changed modules | structured |
| `lint_results` | Ruff findings with severity | structured list |
| `changed_files` | Files modified in this task | list |
| `proof_notes` | Builder's own assessment of proof gaps (optional but encouraged) | free text |

If this section is missing: reviewer flags as process violation. But "missing" ≠ "re-run from scratch." The reviewer should attempt to verify from available evidence (git log, test files, code inspection) and note the process gap — not silently compensate by duplicating the builder's work, and not refuse to review entirely. The failure mode to prevent is silent degradation of the evidence chain, not total halt on serialization glitches.

If the evidence references a different commit than the current task state: reviewer flags as stale evidence and requests builder update. This addresses the freshness concern.

**Reviewer → Auditor contract:**

| Field | Purpose | Type |
|-------|---------|------|
| `ac_mapping` | Per-AC status: PASS / FAIL / PARTIAL | structured list |
| `evidence_per_ac` | Test function name or code reference proving each AC | structured list |
| `findings` | Structured finding list (see Checker Output below) | structured list |
| `scope_note` | What the reviewer explicitly did NOT check | free text |

The `scope_note` is critical: it tells the auditor where to focus. Without it, auditor either re-checks everything (waste) or randomly samples (gaps).

**Planner → Consolidation-test task:**

The planner provides: (a) parent task IDs in the feature chain, (b) AC lines from each parent task, (c) test file paths to review. The planner does NOT inventory existing durable test coverage — that's the consolidation-test writer's job (they have codebase access; planner does not). The planner's role is specification, not verification.

The trigger for creating the consolidation-test task: planner creates it when a feature chain's final implementation task is created. The chain endpoint is a planner judgment (it wrote the chain), not a mechanical detection.

### Test Lifecycle: Scaffolding, Not Archival Knowledge

The earlier Critic rightly challenged my overvaluation of task-test data. The brief itself says 60% of task tests rot naturally — they are scaffolding that mocks later-implemented dependencies. Most task tests are process artifacts, not durable knowledge.

What IS lost when task tests are deleted:
- Edge cases discovered during TDD that went beyond the AC (genuine knowledge)
- Boundary-exercise fixtures that proved non-obvious behavior (genuine knowledge)
- Scaffolding that mocks unimplemented dependencies (disposable)
- Happy-path assertions superseded by durable tests (disposable)

The consolidation-test task's job is to distinguish these. It does not need embedded docstrings in every task test (that's overhead for disposable scaffolding). Instead, the consolidation-test writer should:
1. Read the AC from the parent tasks (provided by planner)
2. Read the task test files
3. Check which AC are already covered by durable tests in `serve/*/tests/`
4. Create durable tests for AC that lack coverage, incorporating edge cases and boundary fixtures from task tests

This is a judgment task, not a mechanical copy. The consolidation-test writer has full context (AC + task tests + existing durable tests) to make the right calls.

### Spiral Detection: Partially Semantic, Not Pure Lint

I initially claimed AC quality checking is "pattern matching, not AI judgment." The Critic correctly challenged this: checks like "are boundary conditions specified?" and "does this reference internal state?" require semantic understanding of the domain.

Honest decomposition:

**Mechanically checkable** (pure lint):
- Does every AC line start with an AC identifier? (Format)
- Does any AC line use banned quantifiers from an explicit list ("all", "every", "correct", "proper")? (Lexical)
- Is the AC count > 0? (Presence)

**Semantically checkable** (requires AI judgment):
- Does each AC name a specific function or observable behavior? (Semantic parsing)
- Are boundary conditions specified? (Domain knowledge)
- Does any AC reference internal state vs. external behavior? (Architectural judgment)

The mechanical checks are a lint pass. The semantic checks are the architect checker's (challenger's) cognitive work. Both are needed, but they should be honestly framed as two different activities: automated pre-check + deliberate review, not "just a checklist."

### Checker Output Format

Each checker produces structured findings:

```
Finding-{n}:
  severity: critical | major | minor
  ac_ref: AC-{n} or "process"
  evidence: {specific code/test/artifact reference}
  evidence_strength: direct | inferred | absent
  recommendation: {concrete fix action}
```

The `evidence_strength` field (added after Critic challenge) distinguishes findings backed by direct proof from findings based on inference or absence of evidence. This is not a confidence score on the finding itself (which would invite gaming) — it's a factual statement about what evidence exists. The parent agent can weigh a "critical + absent evidence" finding differently from a "critical + direct evidence" finding without the checker self-censoring uncertain observations.

## Key Trade-offs

1. **Two-tier AC schema adds complexity vs. one template** — but a single template either over-constrains process AC or under-constrains behavior AC. Two tiers match the actual problem shape.

2. **Evidence provenance (commit, timestamp, run_id) adds overhead** — but without it, evidence freshness is unverifiable. Stale evidence is worse than missing evidence because it silently misleads.

3. **Consolidation-test task is a judgment task, not mechanical** — this means it can fail in ways that mechanical deletion cannot. But the alternative (keeping all task tests forever) is the 219-stale-test status quo.

4. **Reviewer "attempt to verify from available evidence" on missing builder evidence** — this is a gray zone between "halt entirely" and "silently compensate." The risk is that reviewers will routinely compensate and the builder evidence contract becomes unenforced. Mitigation: track the rate of missing-evidence flags. If it exceeds a threshold, escalate as a process problem.

5. **Schema compliance ≠ truth** — agents can satisfy template rules while producing weak or misleading content. The AC schema prevents the most mechanical failures (vague wording, unbounded quantifiers) but does not guarantee good AC. The architect's semantic review is still necessary.

## Warnings

1. **Evidence chain degradation**: If any handoff section is silently skipped or malformed, downstream agents must flag explicitly, not compensate silently. Silent compensation is the pipeline equivalent of NaN propagation — it produces plausible-looking results from corrupted inputs.

2. **Schema drift in handoff formats**: The AC schema will get attention because it's high-visibility. The evidence handoff formats (builder→reviewer, reviewer→auditor) will drift because they're infrastructure. Both need mechanical enforcement, not just documentation.

3. **Consolidation-test task is mandatory, not optional**: If the planner skips it, task-test knowledge is permanently lost at archival. This is a single point of failure for knowledge preservation. The orchestrator should enforce its creation, not rely on planner discipline.

4. **Multi-causal spirals require multi-point fixes**: AC schema alone will reduce but not eliminate iteration spirals. Proof-quality discipline (test-writer) and finding-batching (reviewer) are independently necessary. Shipping only the AC fix and expecting spiral elimination will produce disappointment.

## Confidence

0.75 — Revised down from initial 0.82 after Critic surfaced valid challenges on multi-causality, schema rigidity, and data-retention overvaluation. The core positions (AC as schema contract, structured evidence handoffs, honest decomposition of mechanical vs. semantic checks) are sound. The main uncertainty is whether agents will reliably produce structured evidence in the specified formats, or whether compliance will be theatrical. That can only be validated empirically.
