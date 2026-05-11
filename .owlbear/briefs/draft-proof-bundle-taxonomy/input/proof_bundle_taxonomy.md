# Proof Bundle Taxonomy Brief Seed

Date: 2026-05-10
Source: Agent ecosystem audit of `share/` in `owlbear-dev`
Status: Ideation input, not an approved implementation plan

## Goal

Design a replacement for the current single-axis `(td:N)` convention so pipeline agents can assign the right proof measures without collapsing distinct cases into one middle bucket.

The new model should tell each role what to do:

- Architect: classify proof expectations in AC.
- Test-writer: decide whether to write no tests, smoke tests, or full matrix tests.
- Builder: produce comparable quality-runner evidence.
- Reviewer: decide when code-reader and adjacent proof are required.
- Auditor: separate local proof gaps from structural regression gaps.
- Subagents: provide distinct value instead of repeating or rubberstamping the caller.

## Audit Findings

### Finding 1: `td:0` is overloaded

Current standard:

- `r-pipeline-protocol` defines `(td:0)` as `No test needed` and routes all-`td:0` tasks to test-writer skip, challenger skip, code-reader skip, and reviewer lint-only scope.
- `w-arch-review` lists `(td:0)` examples including `all tests pass`, `config-only`, mechanical removal, and cosmetic fixes.

Observed task history contradicts that single meaning:

- Task #1476 uses `(td:0)` for a bounded pytest pathset that must exit 0.
- Task #1479 uses `(td:0)` for triage/remediation plus a full `uv run pytest` rerun with pass/fail deltas.
- A read-only heuristic scan of first Acceptance Criteria sections found 33 files where `(td:0)` lines mention executable verification (`pytest`, `vitest`, quality-runner, full suite, tests pass, exit 0).
- The same scan found 53 files where `(td:0)` lines look like board/artifact verification (`board`, `kanban`, `parent:`, status, archive, `list_tasks`, file exists, `grep`).

Conclusion: `(td:0)` currently means at least two different things:

1. No executable proof exists; inspect artifacts or board state.
2. No new tests are needed, but existing executable proof must be run.

Those require different downstream measures.

### Finding 2: One level controls too many decisions

The current `(td:N)` value controls all of these at once:

- Test-writer scope.
- Challenger dispatch.
- Code-reader dispatch.
- Reviewer evidence depth.
- Quality-runner expectations.

Those are separate decisions. A task can need no new tests but still require full-suite proof. Another can need smoke tests but no code-reader. Another can need code-reader because of concurrency, security, data-loss, or adjacent-consumer risk, regardless of the number of assertions.

### Finding 3: Subagent routing should map to proof dimensions

The useful subagent split is already visible:

- `quality-runner`: mechanical execution and comparable evidence.
- `challenger`: adversarial pressure on design, AC, and recommendation quality.
- `code-reader`: adversarial code/test proof review for deep or risky implementation.
- `fix-attempt`: fresh-context repair after builder same-context retries fail.
- `planner`: centralized follow-up/decomposition gateway.

The current `(td:N)` model hides this by binding subagent dispatch to a single numeric test-depth value.

## Observed Task Shapes

1. Inspect-only / artifact verification
   - No new tests and no executable proof target.
   - Examples: parent task status, board state, files exist, archive movement.

2. Existing-proof verification
   - No new tests, but an existing test suite, predecessor tests, bounded pathset, or full suite must run.
   - Currently often mislabeled as `(td:0)`.

3. Smoke contract proof
   - One new happy-path assertion is enough.

4. Behavioral matrix proof
   - New behavior needs happy, edge, error, and boundary coverage.

5. High-risk / blast-radius proof
   - Security, concurrency, data loss, conflict handling, topology/config, cross-package regression, or full-suite health.
   - May need code-reader, challenger, adjacent suites, or full suite regardless of whether new tests are written.

## Options

### Option A: Modular Axes With Bundles

Replace the single `(td:N)` convention with orthogonal proof axes, exposed through named bundles.

Candidate axes:

```text
test:none | test:smoke | test:matrix
proof:inspect | proof:scoped | proof:adjacent | proof:full
review:standard | review:deep
challenge:none | challenge:required
```

Bundle examples:

```text
inspect-only = test:none proof:inspect review:standard challenge:none
existing-scoped = test:none proof:scoped review:standard challenge:none
existing-regression = test:none proof:adjacent review:standard challenge:none
smoke = test:smoke proof:scoped review:standard challenge:required
behavioral = test:matrix proof:scoped review:deep challenge:required
critical = test:matrix proof:adjacent|full review:deep challenge:required
```

Pros:

- Separates test creation from proof execution.
- Avoids a default middle level.
- Makes subagent purpose explicit: quality-runner maps to `proof`, code-reader to `review`, challenger to `challenge`.
- Handles mixed tasks without inventing many numeric levels.
- Extensible when new proof modes appear.

Cons:

- Larger change across pipeline standards and workflow skills.
- More annotation text unless bundles are concise and template-driven.
- Requires clear legacy mapping for existing `(td:N)` tasks.

Risks:

- Agents may omit axes unless architecture output requires both bundle and expansion.
- Bundle names can become vague unless tied to objective triggers.
- Mixed frontend/backend tasks may need explicit package/toolchain proof examples.

Confidence: 0.90.

Recommendation: strongest option. Use bundles for ergonomics and axes as the authoritative expansion.

### Option B: Four-Level Ordinal

Keep one numeric level, but redefine the levels around observed proof shape:

| Level | Meaning | Measures |
|-------|---------|----------|
| `td:0` | Inspect-only, no executable proof | test-writer skip; reviewer artifact/board/file evidence |
| `td:1` | Existing-proof verification, no new tests | test-writer skip; quality-runner scoped/adjacent/full as AC requires |
| `td:2` | Smoke new-test work | one assertion per AC line; quality-runner scoped |
| `td:3` | Matrix/high-risk work | full RED categories; coverage; code-reader; challenger required |

Pros:

- Easy to learn.
- Directly fixes the current `(td:0)` overload.
- Smaller diff than modular axes.

Cons:

- Still one dimension controls several different decisions.
- High-risk and matrix-test depth are not always the same.
- Agents may shift the easy-middle shortcut from level 1 to level 2.

Risks:

- Future false assignments remain likely for mixed tasks.
- Review/challenge decisions remain coupled to test-writing depth.

Confidence: 0.82.

Recommendation: viable fallback if modular axes are judged too heavy.

### Option C: Five-Level Ordinal

Use more numeric levels:

| Level | Meaning |
|-------|---------|
| `td:0` | Inspect-only, no executable proof |
| `td:1` | Existing scoped proof only |
| `td:2` | Existing adjacent/full proof only |
| `td:3` | New smoke tests |
| `td:4` | New matrix tests / high-risk deep review |

Pros:

- More nuance than four levels.
- Splits existing scoped proof from adjacent/full proof.
- Reduces current false `(td:0)` assignments.

Cons:

- Scale is less intuitive: level 3 can be simpler than level 2 depending on new-test vs existing-proof shape.
- Higher cognitive load than four levels.
- Still conflates risk, proof, and test creation.

Risks:

- False precision.
- Agents may debate numbers instead of selecting concrete measures.
- Easy-middle behavior can return around `td:2`.

Confidence: 0.68.

Recommendation: not preferred.

### Option D: Bundles Only

Use named bundles without exposing axes:

| Bundle | Intended use |
|--------|--------------|
| `inspect-only` | Artifact/board/file proof only |
| `existing-scoped` | Existing task/predecessor tests prove the change |
| `existing-regression` | Adjacent or full-suite proof required |
| `smoke` | One new assertion per AC line |
| `behavioral` | Full matrix tests and coverage |
| `critical` | Behavioral plus adjacent/full proof, challenger, and code-reader |

Pros:

- No numeric middle bucket.
- Easy for agents to read and discuss.
- Less verbose than raw axes.

Cons:

- Less flexible for mixed tasks.
- Bundle expansion can drift unless the standard keeps the source-of-truth table.

Risks:

- Agents may choose bundles by feel if triggers are not concrete.
- `critical` can become overused without objective criteria.

Confidence: 0.84.

Recommendation: use as the UX layer over Option A, not as the only model.

## Recommended Direction

Adopt Option A, presented through Option D-style bundles.

Authoritative model:

```text
bundle -> test axis + proof axis + review axis + challenge axis
```

Example architecture output:

```text
Proof bundle: existing-regression
Expansion: test:none proof:full review:standard challenge:none
Reason: no new behavior contract, but task success is defined by full-suite regression delta.
```

Example high-risk behavior output:

```text
Proof bundle: critical
Expansion: test:matrix proof:adjacent review:deep challenge:required
Reason: conflict-resolution race behavior with data-loss risk and adjacent Shell wiring.
```

## Implementation Sketch For A Future Brief

1. Update `r-pipeline-protocol`:
   - Replace `Test-Depth Convention` with `Proof Bundle Convention`.
   - Define axes, bundles, objective triggers, legacy `(td:N)` mapping, and subagent routing.

2. Update `w-arch-review`:
   - Architect assigns a proof bundle and expansion per task or AC group.
   - Architecture output template includes bundle, expansion, and rationale.
   - Challenger trigger follows `challenge:required`, not numeric depth.

3. Update `w-tdd-red`:
   - Test-writer reads only `test:*`.
   - `test:none` means pass-through with notes.
   - `test:smoke` means one assertion per AC line.
   - `test:matrix` means happy/edge/error/boundary coverage.

4. Update `w-tdd-green`:
   - Builder verification follows `proof:*` through quality-runner.
   - Direct pytest/ruff command templates are already being removed from active workflow text.

5. Update `w-code-review`:
   - Reviewer evidence expectation follows `proof:*`.
   - Code-reader dispatch follows `review:deep`.
   - Optional `adjacent_files` and `risk_context` have already been introduced as an interim improvement.

6. Update agents:
   - Refresh examples and output format wording for architect, test-writer, builder, reviewer, and auditor.
   - Make subagent roles explicit: quality-runner executes proof, challenger challenges design/AC, code-reader challenges deep code/test sufficiency.

7. Preserve legacy task history:
   - Do not rewrite archived tasks.
   - Add a legacy mapping table so agents can interpret old `(td:N)` task bodies during retries.

## Open Questions For Ideation

1. Should proof bundles be task-level only, or can AC lines carry different bundles?
2. Should `challenge:required` be objective-trigger based only, or always enabled for `behavioral` and `critical` bundles?
3. Should `proof:full` be allowed before auditor, or reserved for auditor/critical remediation tasks?
4. Should `review:deep` always mean code-reader, or should there be a lighter `review:focused` mode?
5. Should frontend tasks have explicit proof variants such as `proof:frontend-scoped` and `proof:frontend-adjacent`, or should quality-runner resolve that from test paths?
6. Should suite-scoped workflows such as test-curation use `task_id` run labels permanently, or should quality-runner grow a first-class `run_id` field?