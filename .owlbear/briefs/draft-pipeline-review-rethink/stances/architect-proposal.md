# Architect Proposal — Unified AC Quality Schema

## Design Summary

A two-tier AC quality schema governed by one meta-rule. Tier 1 (Behavior AC) uses the architect's three concrete rules for code changes. Tier 2 (Process AC) adapts the same structural rigor for workflow/role changes using data's insight that pipeline tasks frequently target agent behavior, not code. Data's meta-rule sits above both tiers as the single acceptance gate.

The schema is designed as a self-contained skill-file section for `h-ac-quality` or inclusion in the architect's checker skill. Both the planner (drafting) and the architect (validating) reference the same section. The architect owns quality; the planner uses it as drafting guidance.

---

## Proposed Skill Section: AC Quality Rules

### Meta-Rule

**Every AC line must be independently verifiable by a downstream agent without access to the author's intent.**

Quality test: Can a test-writer (Tier 1) or artifact-inspector (Tier 2) derive the exact verification steps from the AC text alone, without asking "what did the author mean by this?"

If the answer is no, the AC is malformed. The architect rewrites it.

---

### Tier 1 — Behavior AC (code changes)

Use for any task that adds, modifies, or removes code behavior.

**Three rules:**

1. **Function-scoped.** Every AC line names the specific function, method, endpoint, or CLI command under test. Banned subjects: "the system," "the module," "errors," "output."

2. **Input→output pairs.** Each AC line specifies at least one concrete input condition and its expected observable output. No AC line describes behavior without naming what triggers it and what it produces.

3. **No naked quantifiers.** The words "all," "every," "correctly," "properly," "exactly," "valid," and "appropriate" are banned unless followed by an exhaustive enumeration. The enumeration IS the specification. If you can't enumerate it, you don't understand the requirement yet.

**Transformations — bad AC → good AC:**

**Example 1 — Naked quantifier**

> Bad: `parse_config()` handles all error types correctly.
>
> Good: `parse_config()` raises `ConfigError` when the `priority` field is missing. `parse_config()` raises `SchemaError` when `priority` is not in `['p1', 'p2', 'p3']`. `parse_config()` raises `FileNotFoundError` when the config path does not exist on disk.
>
> Why: "all error types" forces the test-writer to guess which errors exist. The enumeration removes ambiguity — three AC lines, three test scenarios.

**Example 2 — Missing function scope + missing output**

> Bad: The API returns proper error responses for invalid input.
>
> Good: `POST /api/tasks/{id}/move` returns HTTP 404 with body `{"error": "task_not_found"}` when `id` does not match any task file in the tasks directory. `POST /api/tasks/{id}/move` returns HTTP 422 with body `{"error": "invalid_status"}` when the `target` field value is not in `['backlog', 'todo', 'in-progress', 'review', 'done']`.
>
> Why: "The API" is unscoped (which endpoint?). "Proper" is undefined. The rewrite names the endpoint, the input condition, and the exact response shape.

**Example 3 — Internal state reference**

> Bad: `CacheManager.invalidate()` clears the internal `_entries` dict and sets `_dirty` to `False`.
>
> Good: After `CacheManager.invalidate()`, a subsequent call to `CacheManager.get(key)` returns `None` for any `key` that was previously cached. `CacheManager.is_dirty()` returns `False`.
>
> Why: `_entries` and `_dirty` are implementation details — testing them couples to internals. The rewrite tests the same semantics through the public interface.

---

### Tier 2 — Process AC (workflow / role / pipeline changes)

Use for any task that changes agent behavior, pipeline sequencing, artifact formats, or role boundaries — where the "unit under test" is not a function but an agent action or stage transition.

**Three rules:**

1. **Agent/stage-scoped.** Every AC line names the specific agent, pipeline stage, or artifact type affected. Banned subjects: "the pipeline," "the workflow," "the process," "agents."

2. **Observable state change.** Each AC line specifies the concrete before→after change in pipeline behavior, artifact content, or stage sequencing. No AC line describes a goal without naming the observable difference.

3. **Named verification method.** Each AC line states HOW verification occurs — one of: artifact inspection (file exists, file contains pattern), stage-transition audit (task passed through stage X before Y), or configuration check (field has value). If verification requires reading agent intent or replaying an entire session, the AC is too vague.

**Transformations — bad AC → good AC:**

**Example 1 — Unscoped subject + no verification method**

> Bad: The planner creates better task decompositions.
>
> Good: When planner decomposes a feature into ≥2 implementation tasks, it also creates a consolidation-test task whose `deps:` field lists every implementation task ID in the decomposition. Verify by artifact inspection: the consolidation-test task file exists in `tasks/` and its `deps:` field references each sibling task ID.
>
> Why: "Better" is subjective and unverifiable. The rewrite names who (planner), what (creates consolidation-test task), when (≥2 implementation tasks), and how to check (inspect the file's `deps:` field).

**Example 2 — Vague process change**

> Bad: Reviewer batches findings instead of gating on the first one.
>
> Good: Reviewer writes all findings to a `## Review Evidence` section in the task body before returning a PASS or FAIL verdict. A FAIL verdict is accompanied by ≥1 structured finding entry. A PASS verdict has zero finding entries. Verify by artifact inspection: the task body after review contains exactly one `## Review Evidence` section with finding count consistent with the verdict.
>
> Why: "Instead of gating on the first one" describes the old behavior, not the new. The rewrite specifies the exact artifact shape the reviewer must produce and how to verify it.

**Example 3 — Missing observable change**

> Bad: Architect always reviews tasks before implementation.
>
> Good: No task file exists in `todo/` without an `## Architect Review` section containing a verdict line matching the pattern `APPROVED — {ISO-date}` or `REVISED — {ISO-date}`. Verify by artifact inspection: scan all task files in `todo/` for the section and pattern.
>
> Why: "Always reviews" is a process aspiration. The rewrite defines the artifact evidence that proves it happened.

---

### Common Anti-Patterns (both tiers)

| Anti-pattern | Why it fails the meta-rule | Fix |
|---|---|---|
| Adjective without metric: "correctly," "properly," "valid," "appropriate" | Downstream agent must invent a definition of correct | Replace with enumerated expected values or named behavior |
| "Handles errors" | Which errors? What handling? | Name each error type and its specific handling |
| "The system" / "the pipeline" as subject | Unscoped — verifier must guess which component | Name the function, endpoint, agent, or stage |
| Internal state: "sets `_cache` to `{}`" | Requires implementation access to verify | Rewrite as observable: "subsequent `get()` returns `None`" |
| Happy path only | No boundary or negative cases | Add explicit AC lines for invalid input, edge cases, and error paths |
| Goal without artifact: "architect reviews quality" | No physical evidence to inspect | Name the artifact, its location, and its expected content |

---

### Validation Checklist

The architect's checker (challenger) validates every AC line against this checklist. Failures trigger architect rewrite.

**Mechanical checks (lint-pass, no judgment needed):**

- [ ] Every AC line has an identifier (AC-1, AC-2, …)
- [ ] No banned adjectives/quantifiers appear without exhaustive enumeration
- [ ] At least one AC line exists per task
- [ ] Tier is declared: `type: behavior` or `type: process`

**Semantic checks (architect judgment):**

- [ ] Each AC names a specific function/endpoint (Tier 1) or agent/stage/artifact (Tier 2)
- [ ] Each AC has at least one input→output pair (Tier 1) or observable state change + verification method (Tier 2)
- [ ] No internal-state references — only externally observable behavior or inspectable artifacts
- [ ] Boundary and negative cases are present, not just happy path
- [ ] Meta-rule holds: a downstream agent can derive exact verification steps from the text alone

**Quality gate:** If any semantic check fails, the architect rewrites the failing AC lines. The task does not proceed to test-writing with failing AC.

---

## Key Structural Choices

1. **One meta-rule, two tiers, three rules each.** The structure is symmetric: both tiers have the same number of rules with parallel concerns (scope, I/O or change, verification). This makes the schema teachable — learn the pattern once, apply it to either tier.

2. **Tier declaration is explicit.** Each task declares `type: behavior` or `type: process`. Mixed tasks get both tiers applied to the relevant AC lines. This prevents the checker from applying function-scoped rules to process AC (which would reject legitimate workflow tasks) or process-lenient rules to code AC (which would let vague behavior through).

3. **The banned-word list is concrete and finite.** "All, every, correctly, properly, exactly, valid, appropriate" — seven words. This is a grep-level check, not a judgment call. The architect can lint for these mechanically and escalate only the semantic checks to deliberate review.

4. **Verification method is Tier 2 only.** Tier 1 doesn't need it — test-writers know how to verify function behavior (call it, assert output). Tier 2 needs it because "verify agent behavior" is genuinely ambiguous without specifying the method. This asymmetry is intentional, not an inconsistency.

5. **Examples are transformations, not templates.** Bad→good pairs teach the pattern through contrast. Templates ("fill in the blanks") produce mechanical compliance without understanding. The anti-pattern table provides the diagnostic; the examples provide the treatment.

## Trade-offs

| Trade-off | Position | Why |
|---|---|---|
| Two tiers vs. one template | Two tiers | One template either distorts process AC into function-call form or relaxes behavior AC below useful rigor. The pipeline genuinely has both task types. |
| Banned-word list vs. style guidance | Hard ban with escape hatch (enumerate to use) | Style guidance drifts. A concrete list is enforceable. The escape hatch (enumerate) prevents the ban from rejecting legitimate comprehensive AC. |
| Symmetric rule count (3+3) vs. organic | Symmetric | Easier to teach, remember, and validate. Both tiers address the same three concerns: scope, observable change, and verifiability. |
| Explicit tier declaration vs. auto-detection | Explicit | Auto-detection requires semantic parsing of every AC line to determine tier. Explicit declaration is cheap, unambiguous, and makes the checker's job simpler. |
| Verification method in Tier 2 only | Asymmetric by design | Adding it to Tier 1 is noise — "call the function and check the return" is obvious. Tier 2 genuinely needs it because verification paths for process changes are non-obvious. |

## Domain Rationale

This schema directly addresses the highest-leverage root cause identified in the archive analysis: vague AC that propagates ambiguity through 3-5 pipeline stages. The archive's 5 worst-iteration tasks all had AC that failed at least two of the three Tier 1 rules. The locked outcome "architect produces explicit, enumerated, observable AC" is operationalized by these rules — they define what "explicit, enumerated, observable" means concretely.

The Process AC tier fills a real gap. Five of the eight locked outcomes in this brief are process changes, not code changes. Without Tier 2, the planner would need to force "all tasks route through architect" into function-call form — producing either distorted AC or AC that gets a free pass from the checker because it "doesn't look like code AC."

The meta-rule (from data's stance) unifies both tiers under a single testable principle. It is the tie-breaker when the three rules don't clearly apply: if a downstream agent can't derive verification steps from the AC text alone, it fails regardless of which rules it technically passes.

## Confidence

0.84 — High confidence on the structural design (two tiers, three rules each, meta-rule umbrella). The banned-word list and example transformations are grounded in archive evidence. Main uncertainty: whether the Tier 2 verification-method rule will feel natural to planners drafting workflow tasks, or whether it will produce stilted "verify by: look at the file" boilerplate. This can only be validated empirically by running a few process-change tasks through the schema.
