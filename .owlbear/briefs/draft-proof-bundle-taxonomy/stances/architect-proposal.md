# Architect Proposal — Proof Bundle Taxonomy

## Design Summary

**Recommended approach: Extended Single-Axis (Approach 2)**, with targeted improvements over the naive variant.

Replace `(td:0)` / `(td:1)` / `(td:2)` with a **5-value single-axis enum** called **proof-bundle**, annotated once at task level. Each value maps to a fixed dispatch row — no axis decomposition, no bundle-to-axes resolution layer, no derivation logic. Two optional override modifiers (`+challenge`, `+reader`) handle the rare cases where the architect's risk judgment differs from the default.

The 2+2 model (Approach 1) is rejected. The spot-check of 10 tasks found **zero divergence** between the test and proof axes. Two axes that never diverge in practice are one axis with extra annotation cost. The 2+2 model buys composability for a scenario that doesn't occur, and every consumer pays for it on every task by reading two fields instead of one.

### Taxonomy

| Bundle | Test-writer | Quality-runner proof | Challenger | Code-reader | Review scope |
|--------|-------------|---------------------|------------|-------------|-------------|
| `skip` | SKIP | none | no | no | lint only |
| `existing` | SKIP | run named proof | no | no | lint + named proof evidence |
| `smoke` | smoke (1 assertion/AC line) | scoped | no | no | scoped tests + lint |
| `behavioral` | full TDD | scoped + coverage | yes | no | tests + lint + coverage |
| `critical` | full TDD | full + coverage | yes | yes | full (tests + code-reader + lint + coverage) |

### Override modifiers

| Modifier | Effect | Use case |
|----------|--------|----------|
| `+challenge` | Force challenger dispatch | Smoke-depth task that touches a security boundary |
| `+reader` | Force code-reader dispatch | Behavioral-depth task with complex cross-module coupling |

Modifiers append to the bundle value: `smoke+challenge`, `behavioral+reader`. They only escalate — you cannot use them to suppress a default dispatch.

## Key Structural Choices

### 1. Single axis, not multi-axis

The 2+2 model proposes two primary axes (test + proof) and two derivable signals (review + challenge). The derivability analysis from first-principles confirms: review depth and challenger dispatch are functions of the primary signal, not independent variables. But the spot-check goes further — **test depth and proof scope are also coupled**. Every `test:full` task in the sample also had `proof:scoped` or higher. Every `test:none` task had `proof:none` or `proof:existing`. The axes are not independent; they are one decision expressed as two fields.

A single axis means:
- One field for the architect to assign
- One read per consumer
- One routing table (5 rows), not a matrix (3×4 = 12 cells, most invalid)
- Zero derivation logic — the dispatch row is the value

### 2. Five values, not three

The current 3-value ordinal has two defects:

**Defect 1: td:0 overload.** "No proof" and "existing proof required" are semantically opposite but share a value. Agents parse prose to disambiguate. Splitting td:0 into `skip` and `existing` is the single highest-value change — it turns an unstructured escape hatch into a structured routing signal.

**Defect 2: td:1 → td:2 gap.** The jump from td:1 to td:2 changes three things simultaneously: test depth (smoke → full TDD), code-reader dispatch (skip → run), and review scope (scoped → full). Many tasks need full tests but don't warrant code-reader analysis. The `behavioral` value fills this gap — full TDD without the overhead of deep structural review.

### 3. Challenger defaults lowered, with explicit override

Current behavior: challenger dispatches for all td:1+ tasks. This is overly aggressive — smoke tests for simple happy-path assertions don't benefit from adversarial challenge.

New defaults:
- `skip`, `existing`, `smoke` → no challenger (low-risk tasks skip adversarial overhead)
- `behavioral`, `critical` → challenger dispatched (high-investment tasks get pressure-tested)

The `+challenge` modifier lets the architect escalate when a nominally low-risk task touches sensitive code. This is opt-in escalation, not opt-out suppression — a safer default direction.

### 4. Task-level field, not per-AC-line suffix

Decision D4 settles this. The architect writes one annotation in the Architecture Review verdict:

```
Proof bundle: smoke
```

Test-writer reads AC text for assertion granularity (which AC lines get smoke vs. skip), but the routing decision is task-level.

### 5. Values ARE the routing key — no indirection

Both challengers warned against bundles that decompose into axes (first-principles: "bundles recapitulate td:N with an extra lookup layer"). This proposal avoids that trap. The bundle values are not shorthand for axis combinations — they are the primary routing key. No consumer ever decomposes a bundle into sub-fields. The routing table is the contract.

## Assignment Procedure

The architect assigns proof-bundle during Architecture Review (Step 2.1 replacement):

**Step 2.1 — Proof Bundle Assignment**

1. Read each AC line. Assess testability:
   - No testable interface? → candidate for `skip` or `existing`
   - Single happy-path assertion sufficient? → candidate for `smoke`
   - Multiple paths, edges, error handling? → candidate for `behavioral` or `critical`

2. Choose the **highest applicable bundle** across all AC lines. This is the task's proof bundle — one value, not per-line.

3. Default to `smoke` when uncertain. Proof bundle can be escalated but not lowered after approval.

4. If the task requires existing proof (named tests, full-suite pass, quality-runner evidence) but no new tests, use `existing` and note the scope:
   ```
   Proof bundle: existing
   Existing proof scope: tests/test_engine_*.py
   ```

5. Apply override modifiers when risk judgment warrants escalation beyond the bundle default:
   ```
   Proof bundle: smoke+challenge
   ```

6. Write the assignment in the Architecture Review verdict section. Remove per-AC-line `(td:N)` suffixes — they are replaced by this task-level field.

**Subagent gating (replaces current "if ALL td:0" logic):**
- `skip` → append `Test-writer: SKIP` to verdict. Skip challenger.
- `existing` → append `Test-writer: SKIP` to verdict. Skip challenger. Note existing proof scope.
- All others → test-writer processes normally.

## Consumer Routing

Each consumer reads exactly one field: `Proof bundle: X` from the Architecture Review verdict (or task body).

### Test-writer (`w-tdd-red`)

```
match proof_bundle:
  skip | existing → Step 1c pass-through (no new tests)
  smoke           → Step 3 with smoke mode (1 assertion/AC line, happy path only)
  behavioral      → Step 3 with full TDD (multiple paths/edges per AC line)
  critical        → Step 3 with full TDD (same as behavioral for test-writer)
```

Override modifiers are invisible to test-writer — they don't affect test creation.

### Builder (`w-tdd-green`)

```
match proof_bundle:
  skip             → pass-through (no code changes expected)
  existing         → run named proof via quality-runner before advancing
  smoke            → run quality-runner mode=scoped
  behavioral       → run quality-runner mode=scoped (coverage required)
  critical         → run quality-runner mode=full (coverage required)
```

### Reviewer (`w-code-review`)

```
match proof_bundle:
  skip             → lint only, unless existing proof named
  existing         → lint + verify named proof evidence in builder notes
  smoke            → scoped tests + lint evidence
  behavioral       → scoped tests + lint + coverage evidence
  critical         → full tests + lint + coverage + dispatch code-reader

Override check:
  +reader present  → dispatch code-reader regardless of bundle
  +challenge present → (reviewer does not dispatch challenger — this is architect-scoped)
```

### Challenger dispatch (architect, `w-arch-review` Step 2.5)

```
match proof_bundle:
  skip | existing | smoke   → skip challenger (default)
  behavioral | critical     → dispatch challenger

Override:
  +challenge on any bundle  → dispatch challenger
```

## Migration

### In-progress tasks

Tasks currently in the pipeline with per-AC-line `(td:N)` annotations use a legacy mapping table added to `r-pipeline-protocol`:

| Legacy annotation | Proof bundle equivalent |
|-------------------|------------------------|
| All AC lines `(td:0)`, no existing proof named | `skip` |
| All AC lines `(td:0)`, existing proof named in verdict/notes | `existing` |
| Max depth `(td:1)` | `smoke` |
| Max depth `(td:2)` | `critical` |

Consumers check for `Proof bundle:` first. If absent, fall back to max `(td:N)` using this table.

**Note:** Legacy td:1 maps to `smoke` (not `behavioral`), which means previously-challenger-dispatched tasks lose automatic challenger under the new defaults. This is intentional — the speed improvement is the goal. If the architect intended adversarial review, the task should have been td:2.

### Transition period

- New tasks: architect assigns `Proof bundle: X` in Step 2.1
- In-progress tasks: consumers apply legacy mapping
- Legacy mapping table removed after all pre-reform tasks clear the pipeline (estimated: 2-3 weeks)
- Archived tasks: no migration. Historical `(td:N)` annotations in task files and test docstrings are informational — they require no updating.

### Rollout sequence

1. Update `r-pipeline-protocol` — new taxonomy definition, routing table, legacy mapping
2. Update `w-arch-review` — Step 2.1 replacement (proof bundle assignment)
3. Update `w-tdd-red` — replace td:N routing with proof-bundle match
4. Update `w-tdd-green` — replace depth-zero pass-through check with proof-bundle match
5. Update `w-code-review` — replace depth-aware dispatch with proof-bundle match
6. Update agent `.agent.md` dispatch tables that reference td:N

**Change surface:** ~6 files, ~20 lines routing table + ~30 lines per consumer. Bounded and predictable.

## Trade-offs

| Trade-off | Assessment |
|-----------|-----------|
| Less composable than 2+2 | Accepted. 0/10 divergence means composability has no demonstrated value. If a future task genuinely needs divergent axes, the override modifiers handle it without schema change. |
| More values to learn (5 vs 3) | Accepted. But the names are self-documenting — `behavioral` says more than `2`. Net cognitive load is lower, not higher. |
| Challenger skipped for smoke tasks | Intentional. This is the primary speed improvement. Low-risk tasks paying for adversarial review is the waste the reform addresses. |
| `behavioral` is a new tier with no historical precedent | Accepted. It fills the gap between td:1 (smoke + no code-reader) and td:2 (full TDD + code-reader). Tasks that need full tests but not structural review currently over-pay at td:2 or under-test at td:1. |
| Override modifiers add surface area | Minimal — two modifiers, append-only, escalation-only. The alternative (a separate field for each override) is worse. |

## Domain Rationale

### Why not 2+2 (Approach 1)?

The 2+2 model is structurally elegant and theoretically correct. If test depth and proof scope were independent decisions, two axes would be the right decomposition. But they aren't independent. The evidence is unambiguous: 0/10 tasks in the spot-check showed divergence.

Multi-axis models impose costs even when axes are correlated:
- **Annotation cost:** architect writes two fields instead of one, for zero routing benefit in >95% of tasks
- **Parse cost:** each consumer reads two fields and resolves a matrix, instead of one field and a flat lookup
- **Configuration space:** 3×4 = 12 possible combinations, most invalid or unused. The architect must know which combinations are legal. A 5-value enum has 5 valid states — what you see is what you get.
- **Bundle layer problem:** If bundles are added as architect ergonomics (the "optional bundles" in the 2+2 proposal), they create an indirection layer: architect picks bundle → bundle decomposes to axes → consumer reads axis. This is strictly worse than picking a value that IS the routing key.

The 2+2 model solves a problem that the evidence says doesn't exist, at a cost that every task pays.

### Why extended single-axis?

The single-axis model is the **minimal structural extension** that solves the two demonstrated defects:

1. **td:0 overload** → fixed by splitting into `skip` and `existing`
2. **td:1 → td:2 gap** → fixed by inserting `behavioral` between `smoke` and `critical`

It preserves the property that made td:N work: one value, one lookup, one dispatch row. It replaces the property that made td:N fail: numeric ordinals that encode multiple decisions in a single integer.

### Extensibility

Adding a new proof bundle is a single-row addition to the routing table. No axis interactions, no matrix expansion, no derivation rule updates. The extended single-axis model is as extensible as the multi-axis model for the types of extension that actually occur (new verification levels), and simpler for the types that don't (independent axis divergence).

## Confidence

**0.87** — High confidence that the extended single-axis model is the right structural choice given the evidence. The 0/10 divergence finding is the decisive data point — it eliminates the theoretical case for multi-axis decomposition. The 5-value taxonomy is the smallest extension that solves both demonstrated defects. The override modifiers handle edge cases without introducing a second axis.

Residual uncertainty: whether `behavioral` earns its place as a distinct level, or whether 4 values (skip/existing/smoke/critical) would suffice. I include it because the td:1→td:2 gap is real, but it could be validated or dropped during implementation without affecting the design's structural integrity.
