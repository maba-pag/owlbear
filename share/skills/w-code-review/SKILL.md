---
name: w-code-review
description: "Workflow: Code review — evidence-based verification of implementation quality"
user-invocable: false
---

# Code Review

Evidence-based review of a completed implementation task.

Review model: batch-all-findings. Gather all blocking findings before issuing PASS/FAIL.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Scope

### In Scope

- Apply the three-item checklist: AC->code, test->AC, and proof sufficiency.
- Batch all blocking findings before verdict.
- Separate findings from opinions (`Review Evidence` vs `Observations`).
- Dispatch code-reader for `critical` bundles and any bundle with `+reader`.
- Dispatch challenger for `behavioral`/`critical` bundles and any bundle with `+challenge`.
- Verify builder evidence consistency.
- Add PASS confirmation statements for auditor traceability.

### Out of Scope

- Re-executing tests as primary proof source — builder provides evidence (`w-tdd-green`).
- Writing tests or expanding test suites — test-writer (`w-tdd-red`).
- Fixing code — builder (`w-tdd-green`).
- Full-suite regression — auditor (`w-task-verification`).
- Architect quality scoring — auditor (`w-task-verification`).
- Documentation updates — doc-writer (`w-doc-update`).
- Security scanning — CI/SAST (D2), monitored by auditor (`w-task-verification`).

## Step 0 — Setup

Read `r-pipeline-protocol` if not already loaded.

Claim the task via `start_work`, then call `show_task(id={id})` and load AC from frontmatter `ac` (authoritative when non-null). For legacy tasks where `ac` is null, parse AC lines from `## Acceptance Criteria` in the body.

## Step 1 — Scope the Review

Identify builder-scoped files from the builder commit hash in task notes:

```shell
git diff --name-only <commit>~1 <commit>
```

If no commit hash is present, reconstruct changed files from builder notes plus direct file inspection.

For signature changes, use `vscode_listCodeUsages` to verify downstream callers.

Run dirty-tree contamination check on scoped files:

```shell
git status --porcelain -- <changed_files> <task_test_files>
```

If overlapping uncommitted changes exist in scope, FAIL to `in-progress` with Required Follow-up targeting builder.

## Step 2 — Gather Builder Evidence First

Use builder-provided quality evidence from task body as the primary review input.

Required minimum evidence from builder notes:

- Scoped test result summary (pass/fail + failing test names when applicable)
- Scoped lint status
- Coverage summary when AC implies executable code changes
- File list and implementation summary

If evidence is missing or contradictory, request correction first (FAIL to `in-progress`).
Only run independent reruns when evidence quality is insufficient or inconsistent.

### Depth-Aware Dispatch

Determine review scope from frontmatter `proof_bundle` (authoritative when non-null). For legacy tasks where `proof_bundle` is null, fall back to the body `Proof bundle:` line (per `r-pipeline-protocol` taxonomy).

| Proof bundle | quality-runner expectation in builder notes | code-reader | challenger | Reviewer execution path |
|--------------|---------------------------------------------|-------------|------------|-------------------------|
| `skip` | lint evidence | skip | skip | Step 4 checklist with lint + AC/file evidence |
| `existing` | named tests + lint | skip | skip | Step 4 checklist with named-test/lint/file evidence |
| `smoke` | scoped tests + lint | skip | skip | Step 4 checklist with test/lint/file evidence |
| `behavioral` | scoped tests + lint + coverage | skip | run | Step 4 checklist + challenger cross-check |
| `critical` | full suite + lint + coverage | run | run | Step 4 checklist + code-reader and challenger cross-check |

Escalation modifiers only add checks and never remove defaults:

- `+reader`: dispatch `code-reader` for any bundle.
- `+challenge`: dispatch challenger for any bundle.

For `skip`, do not treat "no new tests" as "no executable proof" when existing proof is explicitly required. If AC text, Architecture Review, Test-Writer Notes, or Builder Notes include `Existing proof required: ...`, require matching Quality-Runner evidence before approving. If builder did not provide it, dispatch `quality-runner` yourself or reject for missing required proof.

When challenger is required, dispatch it before final verdicting with: task_id, proposed_verdict, ac_lines, and codebase evidence.

### Code-Reader Consumer Contract

Inputs the reviewer provides:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Kanban task id |
| `ac_lines` | string[] | All AC lines from frontmatter `ac` (fallback: body `## Acceptance Criteria`) |
| `changed_files` | string[] | Builder-changed file paths |
| `test_files` | string[] | Task-scoped tests |
| `adjacent_files` | string[] | Optional caller-curated adjacent files or durable suites that are part of the proof surface |
| `risk_context` | string | Optional focused risk note explaining why adjacent context matters |

When AC, builder evidence, or reviewer scope depends on adjacent durable suites or neighboring consumers, pass those files explicitly via `adjacent_files`. This keeps code-reader constrained while preventing false missing-proof findings from an overly narrow task-local scope.

Required code-reader output sections:

```markdown
## ac_to_code_mapping
## test_to_ac_alignment
## proof_sufficiency
## observations
```

The reviewer synthesizes verdict from builder evidence + direct file checks + optional code-reader report.

## Step 3 — Build Evidence Packet

Create an AC evidence map before verdicting:

| AC Line | Code Evidence | Test Evidence | Status |
|---------|---------------|---------------|--------|

Citations must be concrete (`file:line`, test name, output snippet).

## Step 4 — Run the 3-Item Checklist

### 4.1 AC→Code Mapping

For each AC line, verify implementation behavior matches AC intent.
Any AC mismatch is a blocking finding.

### 4.2 Test→AC Alignment

For each AC line that requires behavior proof, verify at least one test would fail if AC behavior were violated.
Missing or lax proof is a blocking finding.

### 4.3 Proof Sufficiency

Check whether assertions are specific enough to prove behavior (not vague truthy checks) and include natural AC-implied boundaries.
Insufficient proof is a blocking finding.

Non-blocking improvements belong in `Observations`.

### 4.4 Safety & Security

For AC lines touching input handling, authentication, data storage, or external integrations:

- No unsanitized user input reaching SQL, shell, template, or path operations (injection surface)
- No credentials, tokens, or PII hardcoded or logged
- No new dependencies without justification in builder notes

Any safety violation is a blocking finding regardless of AC coverage.

## Step 5 — Batch Findings and Decide

Do not stop at first issue. Collect all blocking findings first.

PASS conditions:

- No blocking findings from Step 4
- Evidence packet covers every AC line
- Builder evidence is sufficient and internally consistent (or independently verified when needed)

FAIL routing:

- Implementation defect -> `in-progress`
- Missing/weak tests with otherwise-correct implementation -> `todo`
- AC ambiguity/incorrect contract -> `backlog`
- Repeated batch review cycle (2nd+ cycle) -> `backlog`

## Step 6 — Advance

Call `end_work` with `## Review Evidence` and `## Observations` in the note.

- PASS advances to `docs`
- FAIL rejects to route status with `### Required Follow-up` table

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

```markdown
## Review Evidence
- Verdict: {PASS|FAIL}
- PASS confirmation (one line): PASS #{id} -> docs | AC mapped to code and evidence sufficient.
- Blocking findings (if FAIL):
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|

## Observations
- Non-blocking notes, trade-offs, and optional follow-up suggestions.
```

## Verification Checklist

- [ ] Batch-all-findings used (no first-failure gating)
- [ ] Sole operative workflow is 4-item checklist (AC→code, test→AC, proof sufficiency, safety & security)
- [ ] Code-reader contract uses only 4 output sections (`ac_to_code_mapping`, `test_to_ac_alignment`, `proof_sufficiency`, `observations`)
- [ ] Builder quality evidence reviewed first; independent rerun only when justified
- [ ] Evidence map includes every AC line
- [ ] Safety & security check performed for AC lines touching security-relevant surfaces
- [ ] Output note uses only `Review Evidence` + `Observations` sections near verdict
