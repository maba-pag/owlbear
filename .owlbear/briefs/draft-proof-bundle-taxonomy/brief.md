# Brief — Proof-Bundle Taxonomy

**Summary:** Replace the `(td:N)` test-depth convention with a single-axis `proof-bundle` taxonomy that makes pipeline routing explicit, eliminates the td:0 overload, and reduces subagent overhead on routine work.

## Problem

The current `(td:N)` convention (0/1/2) is a single ordinal controlling test creation, proof execution, review depth, challenger dispatch, and code-reader dispatch. Three friction points:

1. **td:0 overload.** "No proof needed" and "existing proof required" are indistinguishable without parsing AC prose.
2. **Coarse routing.** Three levels serve five distinct dispatch profiles — the gap between td:1 (smoke) and td:2 (full TDD + code-reader) forces over-testing or under-testing.
3. **Unnecessary subagent overhead.** td:1 triggers challenger by default, adding a subagent dispatch to every smoke-level task.

## Design

A single task-level field replaces per-AC-line `(td:N)`:

```
Proof bundle: skip | existing | smoke | behavioral | critical
```

### Routing Table

| Bundle | Test-writer | Challenger | Code-reader | Reviewer scope |
|--------|------------|------------|-------------|----------------|
| `skip` | SKIP | skip | skip | Lint only |
| `existing` | SKIP | skip | skip | Named tests + lint |
| `smoke` | Smoke tests | skip | skip | Scoped tests + lint |
| `behavioral` | Full TDD | yes | skip | Scoped tests + lint + coverage |
| `critical` | Full TDD | yes | yes | Full suite + lint + coverage |

### Escalation Modifiers

Two append modifiers override column defaults upward only. Suppression is structurally impossible.

| Modifier | Effect | Redundant on |
|----------|--------|-------------|
| `+challenge` | Forces challenger dispatch | `behavioral`, `critical` |
| `+reader` | Forces code-reader dispatch | `critical` |

Modifiers combine: `smoke+challenge+reader` is valid. Order is fixed (bundle, then modifiers alphabetically). Redundant modifiers are accepted but normalized away. Invalid tokens reject at the architect assignment step.

### Behavioral vs Critical Discriminator

| Choose | When |
|--------|------|
| `behavioral` | Task changes observable behavior with bounded scope — new feature, refactor with contract changes, bug fix. Test-writer produces full TDD coverage; reviewer runs scoped tests. |
| `critical` | Task touches cross-cutting concerns, public API surfaces, or high-blast-radius code paths. Reviewer runs the full suite and dispatches code-reader for structural analysis. |

**When uncertain between behavioral and critical:** If the change surface crosses package boundaries or affects >3 downstream consumers, prefer `critical`. Otherwise prefer `behavioral`. The architect adjusts during review.

### Proof-Scope for `existing`

When assigning `existing`, the architect appends a free-text scope note in the verdict:

```
Proof bundle: existing
Existing proof scope: tests/test_engine_*.py, tests/test_cockpit_read_api.py
```

Quality-runner uses this scope to select which existing tests to run. If the scope note is missing, quality-runner runs lint only and flags the gap for the reviewer.

## Assignment Procedure

**Planner assigns; architect adjusts.**

### Planner (primary — task creation)

When creating a task, the planner sets the proof bundle based on the task's decomposition:

1. Write the AC lines for the task.
2. Determine the proof bundle that fits the task's overall complexity.
3. Assign `Proof bundle: {value}` in the task body.
4. If `existing`, include `Existing proof scope: {glob or file list}`.

**Selection guide:**

| Signal | Likely bundle |
|--------|--------------|
| All work needs no executable verification | `skip` |
| No new tests needed; named existing tests cover it | `existing` |
| Simple assertions, bounded scope | `smoke` |
| Multiple paths/edges, error handling, contract changes | `behavioral` |
| High blast radius, broad downstream impact | `critical` |

**When uncertain between adjacent bundles**, prefer the higher one. The architect can de-escalate during review.

**Split consideration:** If AC lines span different proof modes or failure domains, consider splitting. Mixed evidence shapes within one failure domain are fine — assign the highest applicable bundle.

### Architect (adjustment — architecture review)

During architecture review, the architect adjusts the planner's assignment based on full codebase and risk context:

1. Confirm the bundle matches the task's actual complexity and risk.
2. Adjust in either direction if needed (e.g., `smoke` → `behavioral`, or `behavioral` → `smoke` if the planner overcalled).
3. Add escalation modifiers if needed: `Proof bundle: smoke+challenge`.
4. If `existing`, verify the proof-scope glob is accurate.
5. If ALL AC lines need no executable verification and bundle is `skip`, append `Test-writer: SKIP` to the verdict.

## Consumer Routing

Each downstream agent reads `Proof bundle: {value}` from the architecture review verdict. Modifiers are parsed as appended `+{name}` tokens.

### Test-writer (w-tdd-red)

| Bundle | Action |
|--------|--------|
| `skip` | Pass-through — no tests written. Advance to `in-progress`. |
| `existing` | Pass-through — no new tests written. Quality-runner will execute named existing tests. |
| `smoke` | Write one smoke test per AC line (single assertion, happy path). |
| `behavioral` | Full TDD — map each AC line to happy path, edge cases, error paths, boundary conditions. |
| `critical` | Same as `behavioral`. |

Test-writer reads AC text for per-line assertion granularity regardless of bundle. AC lines describing non-test work (artifact inspection, board verification) are skipped by the test-writer — the builder handles them.

### Builder (w-tdd-green)

Implements code to pass the tests written by the test-writer. For `skip` and `existing` bundles, the builder implements directly from AC (no tests to pass). For `existing`, the builder must also ensure the named existing tests still pass.

### Reviewer (w-code-review)

| Bundle | Quality-runner scope | Code-reader | Coverage |
|--------|---------------------|-------------|----------|
| `skip` | Lint only | skip | skip |
| `existing` | Named tests + lint | skip | skip |
| `smoke` | Scoped tests + lint | skip | skip |
| `behavioral` | Scoped tests + lint | skip | yes |
| `critical` | Full suite + lint | yes | yes |

Modifiers override: `+challenge` forces challenger dispatch. `+reader` forces code-reader dispatch.

### Challenger

Dispatched for `behavioral` and `critical` by default. Dispatched for any bundle with `+challenge`. Skipped otherwise.

## Migration

The reform applies to new tasks only. In-progress tasks use a compatibility mapping:

| Legacy | New bundle |
|--------|-----------|
| All AC `(td:0)`, no existing proof named | `skip` |
| All AC `(td:0)`, existing proof named in verdict | `existing` |
| Max `(td:1)` | `smoke` |
| Max `(td:2)` | `critical` |

Agents reading a task check for `Proof bundle:` first. If absent, fall back to the legacy `(td:N)` mapping above. The legacy mapping is removed from the pipeline protocol when all pre-reform tasks have cleared the pipeline.

Archived tasks are untouched.

## Change Surface

| File | Change |
|------|--------|
| `share/skills/r-pipeline-protocol/SKILL.md` | Replace td:N definition and routing table with proof-bundle taxonomy |
| `share/skills/w-arch-review/SKILL.md` | Replace per-AC td:N annotation step with bundle validation step |
| `share/skills/w-tdd-red/SKILL.md` | Replace td:N gating with bundle-based gating |
| `share/skills/w-tdd-green/SKILL.md` | Replace depth-zero pass-through check with skip/existing check |
| `share/skills/w-code-review/SKILL.md` | Replace td:N reviewer dispatch with bundle-based dispatch |
| `share/skills/w-task-decomposition/SKILL.md` | Add proof-bundle assignment to planner procedure |
| `share/instructions/pipeline-agents.instructions.md` | Update td:N references to proof-bundle |
| Agent `.agent.md` files (builder, reviewer) | Update dispatch table references |

## Acceptance Criteria

1. `r-pipeline-protocol` defines the 5-value proof-bundle taxonomy with the complete routing table (including reviewer scope column and modifier expansion rules).
2. `w-task-decomposition` includes the proof-bundle selection guide; planner writes `Proof bundle: {value}` in the task body during task creation.
3. `w-arch-review` validates/adjusts the planner's bundle assignment (both directions) in the task body and writes the final value to the architecture review verdict.
4. `w-tdd-red` reads the proof-bundle from the task body/verdict and gates test creation (skip/existing → pass-through; smoke → one assertion per AC; behavioral/critical → full TDD).
5. `w-tdd-green` handles skip/existing bundles (no tests to pass; builder implements from AC directly).
6. `w-code-review` gates reviewer scope, code-reader, and challenger dispatch on the proof-bundle value and respects `+challenge`/`+reader` modifiers.
7. `pipeline-agents.instructions.md` and relevant agent files reference proof-bundle instead of td:N.
8. Legacy `(td:N)` compatibility mapping exists in `r-pipeline-protocol` for in-progress tasks.
9. No per-AC-line `(td:N)` annotation appears in any active skill or procedure.
