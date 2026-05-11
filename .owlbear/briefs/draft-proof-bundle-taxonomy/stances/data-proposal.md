# Data Proposal — Proof Bundle Taxonomy Reform

**Panelist:** ideation-data (Modeler)
**Mode:** PROPOSE
**Date:** 2026-05-11

---

## Design Summary

Replace the single `(td:N)` ordinal with a **two-field task-level annotation** — `test:` and `proof:` — using closed enum values validated at the assignment boundary. Review depth and challenger dispatch are **derived by formula** with an explicit override mechanism. Named bundles serve as architect ergonomics but are expanded to canonical fields before any consumer reads them.

The core data-integrity win: every routing decision traces to exactly one field with exactly one enum value. No consumer ever parses prose to determine routing. No ordinal carries implicit meaning that varies by context.

---

## Key Structural Choices

### 1. Two explicit fields, closed enums

```yaml
# Task frontmatter (assigned by architect)
test: none | smoke | full          # controls test-writer dispatch
proof: none | existing | scoped | full  # controls quality-runner + reviewer scope
```

**Why two fields, not one extended axis:**

The single-axis model (Approach 2) forces a total ordering on concepts that are categorically different. `test:` answers "what new tests must be written?" `proof:` answers "what executable evidence must the reviewer see?" These are different questions with different consumers. Collapsing them into one ordinal recreates the td:0 overload problem — the very defect we're fixing.

The spot-check found 0/10 divergence. This is expected in a healthy pipeline — most tasks correlate. But the value of two fields is not measured by divergence frequency. It is measured by whether the routing decision is **unambiguous at read time**. With two fields, `test:none proof:existing` is self-documenting. With a single axis, the agent must know that "existing" means "don't write tests but do run named proof" — knowledge that currently lives in prose.

### 2. `proof:existing` eliminates the prose escape hatch

Today's `"Existing proof required: {scope}"` is a free-text field that agents parse with heuristics. This is the single most important data-quality fix in the proposal.

Under the new model:

```yaml
test: none
proof: existing
proof_scope: "tests/test_engine_coverage.py tests/test_engine_dead_code.py"
```

`proof_scope` is a **required companion** when `proof: existing`. It accepts a space-separated list of test file paths or glob patterns. Validation rejects `proof: existing` without `proof_scope`.

**Why not embed scope in the proof value?** Because enum values must be finite and comparable. Scope is data; the axis value is a routing signal. Mixing them produces an open-ended "enum" — which is just a string field with no validation.

### 3. Derived signals with explicit override

```yaml
# Derived (not written by architect unless overriding)
review: lint | scoped | full       # derived from max(test, proof)
challenge: skip | required         # derived from test axis + default rules
```

**Derivation rules:**

| test | proof | → review | → challenge |
|------|-------|----------|-------------|
| none | none | lint | skip |
| none | existing | scoped | skip |
| smoke | none | scoped | required |
| smoke | existing | scoped | required |
| smoke | scoped | scoped | required |
| full | scoped | full | required |
| full | full | full | required |

**Override:** The architect may write `challenge: skip` or `challenge: required` explicitly to override the derived value. When present, the explicit value wins. `review:` can also be overridden (e.g., forcing `review: full` on a `test: smoke` task with security implications).

**Why derivable-with-override rather than fully explicit?** Four independent fields on every task is annotation overhead that exceeds routing value. The derivation table is deterministic and small (7 rows). Overrides handle the 5% of tasks where the default is wrong. This matches the data: most tasks don't need to think about challenge or review depth separately.

### 4. Named bundles as syntactic sugar

```yaml
# Architect shorthand (expanded before routing)
bundle: inspect | existing | smoke | behavioral | critical
```

| Bundle | Expands to |
|--------|-----------|
| inspect | test:none proof:none |
| existing | test:none proof:existing |
| smoke | test:smoke proof:scoped |
| behavioral | test:full proof:scoped |
| critical | test:full proof:full |

**Validation rule:** If `bundle:` is present alongside `test:` or `proof:`, reject as ambiguous. Bundle is shorthand, not a third axis. The expansion happens at a single point — the architect's assignment step — and the canonical fields are what downstream consumers read.

**Why include bundles at all?** Architect ergonomics. Writing `bundle: smoke` is faster and less error-prone than `test: smoke proof: scoped`. But the bundle is sugar — it must not leak into consumer logic. Consumers read `test:` and `proof:`, never `bundle:`.

### 5. `proof_scope` as structured data

When `proof: existing`, the architect must name what to run:

```yaml
proof_scope: "tests/test_engine_coverage.py"
```

When `proof: scoped`, the test-writer names the created test files. When `proof: full`, scope is implicit (full suite). When `proof: none`, `proof_scope` must be absent.

**Validation matrix:**

| proof value | proof_scope | Valid? |
|------------|-------------|--------|
| none | absent | ✓ |
| none | present | ✗ — reject |
| existing | absent | ✗ — reject |
| existing | present | ✓ |
| scoped | absent | ✓ (test-writer fills it) |
| scoped | present | ✓ (architect pre-specified) |
| full | absent | ✓ |
| full | present | ✗ — reject (full means full) |

---

## Data Flow

### Stage 1: Architect assigns (w-arch-review)

The architect evaluates the task and writes either:

- `bundle: <name>` — expanded to canonical fields immediately, or
- `test: <value>` and `proof: <value>` — with optional `proof_scope:` and overrides

The architect appends a **Proof Bundle** section to the architecture review verdict:

```
## Proof Bundle
test: smoke | proof: scoped
review: scoped (derived) | challenge: required (derived)
```

If any derived signal is overridden, the section shows: `challenge: skip (override — rationale: {reason})`.

### Stage 2: Test-writer reads `test:` axis (w-tdd-red)

| test value | Test-writer action |
|-----------|-------------------|
| none | SKIP — append pass-through note |
| smoke | 1 assertion per AC line, happy path only |
| full | Multiple paths, edge cases, full TDD |

The test-writer does **not** read `proof:` — that axis is not its concern. It reads AC text for assertion granularity, as settled in D4.

### Stage 3: Builder reads `proof:` axis (w-tdd-green)

| proof value | Builder action |
|------------|---------------|
| none | No quality-runner dispatch |
| existing | Run named `proof_scope` tests via quality-runner |
| scoped | Run task-specific tests via quality-runner |
| full | Run full suite via quality-runner |

### Stage 4: Reviewer reads `review:` + `challenge:` (w-code-review)

| review value | Reviewer action |
|-------------|----------------|
| lint | Lint only — no test execution |
| scoped | Run task tests + lint |
| full | Run full suite + code-reader dispatch + lint |

| challenge value | Reviewer action |
|----------------|----------------|
| skip | No challenger dispatch |
| required | Dispatch challenger subagent |

### Stage 5: Auditor (w-task-verification)

No change — auditor is third-line defense and does not route on proof bundle. It verifies that evidence artifacts exist and match AC.

---

## Backward Compatibility

### Legacy mapping table

| Old annotation | New equivalent | Notes |
|---------------|---------------|-------|
| All AC `(td:0)` | `test: none proof: none` (or `bundle: inspect`) | Pure pass-through |
| All AC `(td:0)` + "Existing proof required" | `test: none proof: existing proof_scope: {named tests}` | Prose escape hatch becomes structured |
| Max `(td:1)` | `test: smoke proof: scoped` (or `bundle: smoke`) | Smoke tests + scoped proof |
| Max `(td:2)` | `test: full proof: scoped` (or `bundle: behavioral`) | Full TDD + scoped proof |
| Max `(td:2)` + security/critical | `test: full proof: full` (or `bundle: critical`) | Full TDD + full suite |

### Migration strategy

- **New tasks:** Use new model from reform effective date.
- **In-progress tasks:** Agents encountering per-AC-line `(td:N)` annotations apply the legacy mapping table above. No task rewriting.
- **Archived tasks:** No change. Historical `(td:N)` annotations are informational.
- **Test file docstrings:** Existing `(td:N)` references in test headers are informational. Add a one-line note to r-pipeline-protocol: "Legacy `(td:N)` references in test files predate the proof bundle reform and are not routing signals."

---

## Validation

### Assignment-time validation (architect boundary)

This is the critical validation boundary — the point where data enters the pipeline.

1. **Enum membership:** `test:` must be one of `{none, smoke, full}`. `proof:` must be one of `{none, existing, scoped, full}`. Any other value is rejected.

2. **Co-occurrence rules:**
   - `bundle:` present → `test:` and `proof:` must be absent (and vice versa).
   - `proof: existing` → `proof_scope:` must be present and non-empty.
   - `proof: none` or `proof: full` → `proof_scope:` must be absent.

3. **Override validation:** `review:` and `challenge:` may only be present when they differ from the derived value. If present, they must contain valid enum values and the architect must include a rationale.

4. **Completeness:** Both `test:` and `proof:` are required (or `bundle:` alone). Missing fields are rejected — no implicit defaults. The current td:N default-to-1 creates ambiguity between "architect chose 1" and "architect forgot."

### Consumer-time validation (each downstream stage)

Each consumer validates only the field it reads:

- Test-writer validates `test:` ∈ `{none, smoke, full}`.
- Builder validates `proof:` ∈ `{none, existing, scoped, full}` and checks `proof_scope:` co-occurrence.
- Reviewer validates `review:` ∈ `{lint, scoped, full}` and `challenge:` ∈ `{skip, required}`.

If a consumer encounters a missing or invalid field, it **fails loudly** — no silent fallback, no default behavior. This is non-negotiable. Silent defaults are how td:0 became overloaded in the first place.

### Where validation lives

Validation rules live in the skill files that define each stage. There is no separate validation service — the pipeline is skill-driven, and each skill is its own validation boundary. The rules above are codified as prose constraints in the skill text, enforced by the agent reading the skill.

---

## Trade-offs

| Dimension | Benefit | Cost |
|-----------|---------|------|
| Routing clarity | Each consumer reads exactly one field | Architect writes 2 fields instead of 1 suffix |
| Prose elimination | `proof:existing` replaces free-text escape hatch | `proof_scope:` is a new required field for one proof value |
| Override flexibility | Derived signals reduce annotation for 95% of tasks | Override mechanism adds 2 optional fields to the schema |
| Bundle ergonomics | Common patterns are one word | Bundle expansion must be validated (no conflicts with explicit fields) |
| No defaults | Missing fields fail loudly — no ambiguity | Architect cannot omit annotation — every task requires explicit choice |
| Legacy coexistence | In-progress tasks work via mapping table | Two conventions coexist during transition window |

### Risk: Over-specification

The 2+2 model introduces more moving parts than the current 3-row table. If the pipeline is small and stable, this overhead may not pay for itself.

**Mitigation:** Bundles collapse the common cases to single-word annotation. The 7-row derivation table is deterministic and memorizable. The marginal complexity is in the schema definition, not in daily use.

### Risk: proof_scope drift

`proof_scope:` file paths can become stale as test files are renamed or deleted.

**Mitigation:** `proof_scope:` is consumed at build/review time — if the named files don't exist, quality-runner fails immediately. This is a feature, not a bug: stale scope surfaces as a hard failure, not silent data loss.

---

## Domain Rationale

From a data integrity perspective, this design eliminates three categories of data corruption that exist in the current model:

1. **Semantic overloading.** `td:0` means two different things depending on whether free-text "Existing proof required" appears elsewhere in the task. This is a schema violation — one value, two meanings. The new model assigns these to different enum values on different axes (`proof: none` vs `proof: existing`), making the distinction structural.

2. **Implicit schema.** The current routing table has an undocumented escape hatch where `td:0` tasks with "Existing proof required" prose trigger quality-runner despite the routing table saying SKIP. The escape hatch is not in the schema — it's in the agent's LLM interpretation. The new model makes every routing path explicit in the derivation table. No path requires prose parsing.

3. **Silent default propagation.** When `(td:N)` is missing, the current convention defaults to td:1. This means an architect's omission produces the same signal as an architect's deliberate choice. The new model rejects missing fields — silence is an error, not a default.

The two-axis model is the right shape because it separates two genuinely different data types: **instructions** (test: what to write) and **evidence requirements** (proof: what to verify). These have different producers, different consumers, and different lifecycles. Forcing them into a single ordinal creates a lossy compression that downstream consumers must decompress by reading context — which is exactly the kind of implicit schema that causes data quality failures.

---

## Confidence

**0.82**

High confidence in the schema design and validation boundaries — these are direct applications of data integrity principles to a well-understood domain. Moderate uncertainty about whether bundles earn their complexity (vs. just requiring the two raw fields) and whether `proof_scope:` will be consistently maintained. The 0/10 divergence finding means the two-axis structure is theoretically correct but practically untested — the design is robust to divergence if/when it appears, but it may be perceived as over-specified for a pipeline where axes correlate 95%+ of the time.
