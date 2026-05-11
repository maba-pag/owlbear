# Research Notes — Proof Bundle Taxonomy

## Verified Findings

### F1: td:N is defined in 2 skill files and consumed in 4

| Site | File | Role | Lines |
|------|------|------|-------|
| Primary definition | `share/skills/r-pipeline-protocol/SKILL.md` | Defines td:0/1/2 semantics and routing table | L129-149 |
| Assignment procedure | `share/skills/w-arch-review/SKILL.md` | Architect assigns per-AC-line, calculates max depth | L84-107 |
| Consumer: test-writer | `share/skills/w-tdd-red/SKILL.md` | ALL td:0 → pass-through; td:1 → smoke; td:2 → full TDD | L19, L44-111, L133-137 |
| Consumer: builder | `share/skills/w-tdd-green/SKILL.md` | Checks for depth-zero pass-through note | L41 |
| Consumer: reviewer | `share/skills/w-code-review/SKILL.md` | td:0 → lint only; td:1 → scoped; td:2 → code-reader dispatch | L22, L78-88 |
| Consumer: auditor | `share/skills/w-task-verification/SKILL.md` | No explicit td:N routing — 3rd-line defense | N/A |

### F2: Existing-proof guard is a free-text escape hatch

When a `(td:0)` AC line names existing tests, full-suite proof, or quality-runner evidence:
- Architect notes: `"Existing proof required: {scope}"` in architecture review verdict
- Test-writer skips (td:0 behavior)
- Builder/reviewer must run named proof through quality-runner anyway

This is the escape hatch that handles the td:0 overload today. It works but is not structured — agents must parse prose.

### F3: Routing is a 3-row dispatch table keyed on max(td:N)

| Max depth | Test-writer | Challenger | Code-reader | Reviewer scope |
|-----------|------------|------------|-------------|----------------|
| td:0 | SKIP | skip | skip | lint only (unless existing proof named) |
| td:1 | smoke tests | yes | skip | scoped tests + lint |
| td:2 | full TDD | yes | yes | full (tests + code-reader + lint) |

### F4: Test files embed td:N in docstrings/headers

At least 11 test files reference `(td:N)` in AC documentation comments. These are informational, not routing — they won't need updating, just a legacy note.

### F5: Active and archived task files use per-AC-line td:N annotations

Architecture review output template includes a "Test Depth" section with max depth. Task AC lines carry `(td:N)` suffixes. These are historical artifacts — the reform applies to new tasks only.

### F6: The current dispatch flow is compact

```
Architect assigns per-AC-line td:N → max(td) → routing table → test-writer/challenger/code-reader/reviewer
```

The entire routing logic lives in ~20 lines of the pipeline protocol's routing table plus ~30 lines in each consumer skill. Total change surface is bounded.

## Candidate Implications

### I1: The 2+2 model replaces the routing table with a 2-axis lookup

The current 3-row table (keyed on max td:N) becomes a matrix keyed on (test, proof):
- Test-writer reads `test:` axis → skip / smoke / full
- Builder/quality-runner reads `proof:` axis → none / existing / scoped / full
- Reviewer derives code-reader dispatch from proof scope (proof:full → code-reader)
- Architect derives challenger from test axis + risk judgment (with explicit override)

### I2: Task-level annotation simplifies the architect assignment step

Instead of annotating each AC line and computing max, the architect writes one task-level pair:
```
test: smoke | proof: scoped
```
This eliminates the per-line annotation step and the aggregation logic.

### I3: Bundles may still have value as architect ergonomics

Even with a 2-axis model, common combinations could be named for quick assignment:
```
inspect = test:none proof:none
existing = test:none proof:existing
smoke = test:smoke proof:scoped
behavioral = test:full proof:scoped
critical = test:full proof:full
```
Whether this adds enough value over raw axis pairs is a Phase 2 design question.

### I4: The existing-proof guard becomes a first-class axis value

`proof:existing` replaces the free-text `"Existing proof required: {scope}"` escape hatch. This is the single highest-value change — it turns an unstructured escape hatch into a structured routing signal.

### I5: Change surface is bounded

- 2 definition sites (r-pipeline-protocol, w-arch-review)
- 3 consumer sites (w-tdd-red, w-tdd-green, w-code-review)
- 1 instruction file (pipeline-agents.instructions.md — indirect)
- Agent .agent.md files — dispatch tables referencing td:N
- Test file headers — informational only, no routing change needed

## Open Research Questions

### Q1: How often do test and proof axes actually diverge in practice?

The challengers claim >95% correlation. If true, the 2-axis model adds annotation cost without routing value for most tasks. Phase 2 should spot-check 10-20 representative tasks from the archive to measure actual axis divergence.

### Q2: What are the proof:existing scope variants?

The current free-text escape hatch allows arbitrary scope descriptions. Phase 2 needs to define the proof axis values precisely:
- proof:none — no executable proof
- proof:existing — named existing tests must pass (what granularity?)
- proof:scoped — quality-runner runs task-specific tests
- proof:full — quality-runner runs full suite + adjacent

### Q3: Should challenger dispatch be derivable or explicit?

The challengers argue for explicit opt-in. The input file argues for axis-based routing. Phase 2 must decide: does the architect flag `challenge:required` explicitly, or is it derived from `test:full` with an override mechanism?

### Q4: What does the architecture review output template look like under the new model?

Currently: "Test Depth" section with max depth and test-writer status. Under 2+2: needs to include both axes plus any override flags. Template design is Phase 2 work.

### Q5: How should the legacy mapping work for in-progress tasks?

Tasks currently in the pipeline have per-AC-line td:N annotations. The reform applies to new tasks only, but agents reviewing or retrying existing tasks need to interpret old annotations correctly. A mapping table in r-pipeline-protocol is probably sufficient.
