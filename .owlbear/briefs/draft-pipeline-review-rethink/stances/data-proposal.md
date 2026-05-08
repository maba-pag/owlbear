# Data Proposal — Hybrid AC Quality Schema

## Design Summary

A single AC quality schema with one meta-rule, two tiers, and concrete validation rules per tier. The architect's 3 rules become the Tier 1 (Behavior AC) validation test. New parallel rules — equally concrete — define Tier 2 (Process AC) quality. The schema is a data contract: AC lines are structured input consumed by test-writer, builder, and reviewer. Malformed input produces garbage output; the schema prevents malformation at the source.

## The Schema

### Meta-Rule (applies to both tiers)

> **Every AC line must be independently verifiable by a downstream agent without access to the author's intent.**

Verification test: hand the AC line to an agent who has never seen the task description. Can they determine PASS or FAIL from the AC text alone + codebase access? If not, the AC is malformed.

### Tier 1 — Behavior AC (code changes)

Use when the AC describes what code does — function behavior, endpoint responses, CLI output, data transformations.

**Three validation rules:**

| # | Rule | What it catches |
|---|------|-----------------|
| B1 | **Function-scoped.** Name the function, method, endpoint, or command under test. | "The system handles errors" — which system? which errors? where? |
| B2 | **Input→output pair.** Specify at least one concrete input and its expected observable output. | "Returns the correct result" — correct according to what? |
| B3 | **No unbounded quantifiers.** "all," "every," "any," "correctly," "properly" are banned unless followed by exhaustive enumeration. | "Handles all edge cases" — infinite scope, untestable |

**Quality gate:** Can a test-writer derive the exact set of test scenarios from the AC line without asking the architect what they meant? The scenario set must be deterministic from the AC text alone. A single AC line may require multiple test scenarios (positive, negative, boundary), but which scenarios are required must be unambiguous.

#### Bad → Good Transformations (Behavior AC)

**Example 1 — Missing function scope:**

- Bad: `The parser handles malformed input gracefully.`
- Good: `parse_config() raises ConfigError with message "missing required field: {name}" when any of [priority, title, status] is absent from the input dict.`
- Why: Bad version doesn't name the function. "Gracefully" is an unbounded adjective. Good version names `parse_config()`, specifies the exact exception type, message template, and the exhaustive field list.

**Example 2 — No input→output pair:**

- Bad: `The API returns appropriate error responses.`
- Good: `POST /api/tasks/{id}/move returns 404 with body {"error": "task_not_found", "detail": "No task with id {id}"} when the task ID does not exist in the board.`
- Why: Bad version specifies no endpoint, no method, no status code, no body shape. Good version is a complete I/O contract — the test-writer can write the assertion without interpretation.

**Example 3 — Unbounded quantifier:**

- Bad: `All invalid inputs are rejected with clear error messages.`
- Good: `validate_priority(value) raises ValueError for inputs [None, "", "invalid", 42, -1]. Each ValueError message starts with "invalid priority: ".`
- Why: "All invalid inputs" is infinite. Good version enumerates the specific invalid inputs that must be tested and the observable output for each.

### Tier 2 — Process AC (workflow/role changes)

Use when the AC describes what agents do, what stages produce, or how pipeline behavior changes — skill rewrites, protocol changes, role boundary shifts.

**Three validation rules:**

| # | Rule | What it catches |
|---|------|-----------------|
| P1 | **Agent-and-stage scoped.** Name the specific agent, skill, or pipeline stage affected. | "The pipeline validates AC quality" — which agent? at which stage? |
| P2 | **Observable artifact or state change.** Specify what artifact is produced, modified, or blocked — and what property changes. | "Reviewer is more thorough" — more thorough how? what changes in its output? |
| P3 | **Verification method stated.** Name how compliance is checked: artifact inspection, stage-transition audit, field presence, or diff comparison. | "Architect always reviews tasks" — how would you detect non-compliance? |

**Quality gate:** Can a reviewer verify PASS/FAIL by inspecting artifacts or stage transitions alone — without observing the agent's runtime behavior or reading its internal reasoning? Process AC must point to an observable output, not a cognitive process.

#### Bad → Good Transformations (Process AC)

**Example 1 — No agent/stage scope:**

- Bad: `AC quality is validated before implementation begins.`
- Good: `The architect's challenger subagent runs AC validation (rules B1-B3 for behavior AC, P1-P3 for process AC) on every task before the architect moves it to todo. Validation failures appear as structured findings in the task body.`
- Why: Bad version doesn't say who validates, when, or where the result goes. Good version names the agent (challenger), the timing (before move to todo), and the observable artifact (structured findings in task body).

**Example 2 — Unobservable behavior change:**

- Bad: `Reviewer focuses on completeness, not correctness.`
- Good: `Reviewer skill w-code-review limits its checklist to 3 items: (1) AC→code mapping, (2) test→AC alignment, (3) proof sufficiency. Findings outside these 3 categories go in the "flagged concerns" section, not the pass/fail determination. The skill file contains an explicit "out of scope" section listing correctness, performance, and style.`
- Why: "Focuses on" is a cognitive state, not an artifact property. Good version specifies the exhaustive checklist, where out-of-scope items go, and what the skill file must contain — all inspectable by diffing the skill file.

**Example 3 — No verification method:**

- Bad: `Planner always creates a consolidation-test task for feature chains.`
- Good: `When planner decomposes a feature into tasks [A, B, C], it also creates task D with title "consolidation test for {feature}" and dependencies on [A, B, C]. Auditor flags any feature chain missing a consolidation-test task during its review of the final task in the chain. Verification: search for a task with "consolidation test" in title and matching parent dependencies.`
- Why: Bad version is a behavioral claim about the planner with no way to detect violations. Good version specifies the artifact shape (title pattern, dependency structure) and the backstop agent (auditor) and the verification query.

## Key Structural Choices

1. **Same meta-rule, parallel concrete rules.** Both tiers share the "independently verifiable" meta-rule. Each tier has exactly 3 concrete rules. The tiers are structurally symmetric — the architect doesn't need different mental models for different AC types, just different slot names (function vs. agent, input→output vs. artifact change, enumeration vs. verification method).

2. **Rules are slot-filling, not style guides.** Each rule names a required slot (B1: function name, B2: input and output, B3: enumerated set; P1: agent/stage, P2: artifact/property, P3: verification method). If the slot is empty, the AC fails. This is mechanical — no judgment calls about "is this specific enough?"

3. **Verification method is Process AC's equivalent of Input→Output.** Behavior AC's power comes from B2 (the test-writer knows what to assert). Process AC's equivalent gap has always been "how do I verify this?" — P3 forces the architect to answer that question upfront, which is equivalent to specifying the output for a function.

4. **The schema is a lint target.** B3 (banned quantifiers) and P1 (agent name present) are mechanically checkable. B1, B2, P2, P3 require semantic judgment but are slot-structured — the architect's challenger checks for slot presence, then validates slot content. Two-pass: lint first, then semantic review.

## Trade-offs

| Trade-off | Position | Risk |
|-----------|----------|------|
| Two tiers vs. one template | Two tiers. One template either over-constrains process AC or under-constrains behavior AC. | Tier classification adds a decision point — mitigated by the architect making the classification, not the planner |
| 3 rules per tier vs. more granular checklist | Three each. Enough to catch the failure modes in the archive; few enough to memorize. | May miss edge cases not in the 5-task archive sample — mitigated by the meta-rule as a fallback |
| Slot-filling vs. natural language guidelines | Slot-filling. "Name the function" is enforceable; "be specific" is not. | Overly rigid slots may produce mechanically compliant but semantically weak AC — mitigated by challenger's semantic pass after lint |
| P3 (verification method required) vs. implicit verification | Explicit. Forces the architect to think about how compliance is detected. | Adds architect effort per process AC line — justified because process AC without verification method is unverifiable by definition |

## Domain Rationale

AC is a data contract. Each AC line is a record consumed by downstream agents as structured input. The schema treats AC quality as a data quality problem:

- **Missing fields** = malformed records. B1/B2/B3 and P1/P2/P3 define the required fields per record type. A record missing any required field is rejected at the validation boundary (architect stage), not propagated downstream.

- **Unbounded quantifiers** = NaN propagation. "All edge cases" is the AC equivalent of a NaN: it produces plausible-looking downstream output (tests that pass on whatever the test-writer guessed) from undefined input. B3 catches this explicitly.

- **Unverifiable process claims** = implicit schema. "Reviewer focuses on completeness" is a constraint that exists only in the author's head, never materialized as a checkable property. P3 forces explicit schema — the verification method is the type annotation for process AC.

- **The meta-rule is the NOT NULL constraint.** Every AC line must be independently verifiable = every record must contain enough information to evaluate without external context. This is the single rule that prevents silent garbage propagation.

The schema does NOT solve proof-quality failures (default-only fixtures, mock≠real shape). Those are orthogonal defect classes addressed by test-writer discipline and reviewer batching. The schema prevents the highest-leverage single failure class: vague specification that makes all downstream work ambiguous.

## Confidence

0.82

High confidence on: the 6 concrete rules (grounded in archive failure analysis), the meta-rule (validated by Critic in stance phase), the slot-filling approach (mechanically enforceable).

Lower confidence on: whether P3 will produce useful verification methods in practice vs. boilerplate (0.70 — needs empirical validation after first 10 process AC lines), whether the 3-rule-per-tier count is sufficient or will need a 4th rule for a failure class not yet seen (0.72).
