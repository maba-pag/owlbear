# End-User Proposal — Proof Bundle Taxonomy

## Design Summary

**Recommended: Extended Single-Axis with named depth levels.**

Replace `(td:0)` / `(td:1)` / `(td:2)` with five named task-level labels that each resolve to a complete routing row. One assignment, one lookup, zero aggregation.

The labels:

| Label | Meaning | Test-writer | Quality-runner | Challenger | Code-reader |
|---|---|---|---|---|---|
| `proof:skip` | No verification needed | SKIP | SKIP | SKIP | SKIP |
| `proof:existing` | Named tests must pass; no new tests | SKIP | RUN named scope | SKIP | SKIP |
| `proof:smoke` | Smoke tests, scoped proof | WRITE smoke | RUN scoped | SKIP | SKIP |
| `proof:behavioral` | Full TDD, scoped proof | WRITE full | RUN scoped | YES | SKIP |
| `proof:critical` | Full TDD, full suite, deep review | WRITE full | RUN full + adjacent | YES | YES |

One field. One read per consumer. The label is the routing key — no derivation, no axis decomposition, no bundle-to-axes resolution.

### Optional override: `challenge:yes`

A single opt-in flag the architect adds when a task below `proof:behavioral` has unusual risk. This is the only override. It does not create a second axis — it's an exception flag, not a dimension.

## Key Structural Choices

### 1. Single axis, not two

The 2+2 model asks the architect to assign `test:` and `proof:` independently. The spot-check found 0/10 tasks where these axes diverge. That means in 100% of observed cases, the architect is making a redundant decision — answering two questions that have the same answer.

Redundant decisions are not "flexibility." They are friction. Every redundant assignment is a chance to misconfigure, a moment of hesitation ("wait, should test and proof match here?"), and a signal to the architect that the system has more degrees of freedom than the problem warrants.

The single axis captures the real mental model: **"How much verification does this task need?"** That is one question with one answer. The named levels map that answer directly to routing — no decomposition step, no cross-referencing.

### 2. Named labels, not numbers

`proof:smoke` tells you what happens. `td:1` does not. The current ordinal forces every new consumer (and every architect returning after a break) to look up the routing table. Named labels are the routing table — the lookup is eliminated.

Naming discipline: each label describes the *verification activity*, not the *risk level* or *task category*. This prevents the label from becoming a judgment call about risk and keeps it as a factual statement about what the pipeline will do.

### 3. `proof:existing` as a first-class level

This is the single highest-value change in the entire reform. Today, "run existing tests but don't write new ones" is encoded as `(td:0)` plus a prose escape hatch (`"Existing proof required: {scope}"`). Agents parse free text to figure out whether quality-runner should run. Under the new model, `proof:existing` is unambiguous: quality-runner runs the named scope, test-writer skips, challenger skips. No prose parsing. No overload.

The architect annotates the scope in the AC text (e.g., "proof:existing — `test_engine_cockpit_view.py`"). The label routes; the AC text names the target. Clean separation.

### 4. Task-level assignment, no per-AC-line annotation

Every current consumer aggregates per-line `(td:N)` annotations to a task-level signal (max, any, all). The per-line step exists only to create work for the architect. Under the new model, the architect writes one label in the task frontmatter or architecture review output:

```
proof: smoke
```

Done. No per-line annotation, no aggregation logic, no max-depth calculation.

### 5. Challenger as opt-in override, not depth-gated default

Currently, challenger dispatches for all `td:1+` tasks. This means every smoke-level task gets adversarial review — even when the risk is trivial. The first-principles challenger correctly identifies this as a speed cost with no quality benefit for low-risk work.

Under this proposal, challenger dispatches automatically only at `proof:behavioral` and above. For `proof:smoke` or `proof:existing` tasks that have unusual risk, the architect adds `challenge:yes`. This is not a second axis — it's a single boolean override with a default of "no."

This directly serves the primary driver (speed) by eliminating unnecessary challenger calls on routine work.

## Trade-offs

| Trade-off | Position |
|---|---|
| **Less composable than 2+2** | Accepted. Composability has value only when axes diverge. At 0/10 observed divergence, the value is zero and the cost (double assignment, parse complexity) is real. If future evidence shows divergence, the named levels can be decomposed — but that's a future problem backed by future evidence, not a present design requirement. |
| **Five values vs. three** | Accepted. Three values with an overloaded zero is worse than five values with clear names. The cognitive cost of learning five self-documenting labels is lower than the cognitive cost of remembering what `td:0` means in context. |
| **Challenger override is a second field** | Accepted. A single boolean override is categorically different from a second axis. It has one value (`yes`) and a default (`no`). The architect reaches for it rarely. It does not create a configuration space — it creates an exception path. |
| **Cannot express "write full tests but run only scoped proof"** | Accepted. This combination does not appear in the spot-check, and the first-principles analysis confirms test depth and proof scope are correlated by design. If this combination becomes needed, a new level can be added — but adding it now for a hypothetical case adds a level nobody uses. |

## Domain Rationale

### Assignment UX

The architect's job is to look at a task and answer: **"How much verification does this need?"** This is already the question they answer with `td:N`. The reform replaces an opaque ordinal with a named label that makes the answer self-documenting.

Assignment cost under each model:
- **Current (td:N):** One number per AC line → compute max → one task-level signal. ~5 seconds per AC line, plus aggregation.
- **2+2 model:** Two axis values per task → cross-reference for consistency → done. ~10 seconds per task, plus a "do these match?" sanity check.
- **This proposal:** One label per task → done. ~3 seconds.

The single-axis model wins on assignment speed because it eliminates both per-line annotation *and* multi-axis consistency checking.

### Readability

An agent consuming the routing signal reads one field and gets a complete answer. No decomposition. No "read test axis, then read proof axis, then derive review depth." The label *is* the dispatch instruction.

A human scanning the task board sees `proof:behavioral` and knows immediately: full TDD, scoped quality-runner, challenger runs. No lookup table needed.

### Error Modes

| Error mode | 2+2 model risk | This proposal risk |
|---|---|---|
| Axis mismatch (test:full + proof:none) | Real — architect can assign contradictory axes | Eliminated — levels are pre-validated combinations |
| Wrong level selected | Possible — architect picks `smoke` when `behavioral` is appropriate | Same risk, but the self-documenting name reduces it |
| Override forgotten | N/A — no overrides in 2+2 | Low — `challenge:yes` is rare; architect explicitly evaluates risk |
| Label meaning forgotten | N/A — axes are generic | Low — labels describe the activity, not an abstraction |

The most dangerous error mode — axis mismatch — is structurally eliminated by the single-axis model. You cannot assign contradictory values to a field that has one value.

### Cognitive Load

The primary driver is speed. Cognitive load is the bottleneck for both the architect (assignment) and the agents (consumption).

**Architect cognitive load:** One decision, one label. The question "how much verification?" maps directly to the mental model architects already use. No axis decomposition, no consistency check.

**Agent cognitive load:** One field read, one routing row. Each agent reads `proof:` and gets its complete instruction. No cross-referencing, no derivation logic, no "if proof is X and test is Y then review is Z" conditionals.

**Operator cognitive load:** Task board shows one label per task. Throughput analysis can filter by level. No multi-axis grouping needed.

### Naming

The labels follow a single principle: **each name describes what the pipeline does, not what the architect thinks about risk.**

- `skip` — pipeline does nothing
- `existing` — pipeline runs existing tests (doesn't write new ones)
- `smoke` — pipeline writes and runs smoke tests
- `behavioral` — pipeline writes and runs full behavioral tests
- `critical` — pipeline writes and runs full tests with deep review

These are activity descriptions. They're verifiable: after the pipeline runs, you can check whether the named activity actually happened. They don't require judgment to interpret — `behavioral` means behavioral tests, not "I think this task is kind of important."

The `proof:` prefix is the namespace. It replaces `td:` (which stands for "test depth" — a name that already conflates test creation with proof execution). `proof:` is the umbrella concept: what evidence does this task produce?

## Confidence

**0.80**

High confidence that the single-axis model is the right choice given 0/10 observed axis divergence and the primary speed driver. High confidence that named labels outperform ordinals for self-documentation. Moderate confidence on the exact label set — the five proposed levels cover the observed routing patterns, but `proof:existing` scope semantics (how the architect names the target tests) may need refinement during implementation. The `challenge:yes` override is the weakest element — it could be folded into a sixth level (`proof:challenged-smoke`?) if the boolean override proves confusing in practice, but I believe the override is cleaner than level proliferation.
