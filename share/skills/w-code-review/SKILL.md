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

- Validate AC-to-code evidence, test adequacy, and proof sufficiency for completed implementation tasks.
- Route failures to the correct upstream owner with explicit Required Follow-up actions.

### Out of Scope

- Writing missing tests or expanding test suites directly — test-writer (`w-tdd-red`).
- Fixing implementation defects in source code — builder (`w-tdd-green`).
- Running full-suite regression as an exit gate — auditor (`w-task-verification`).

## Step 0 — Setup

Read `r-pipeline-protocol` if not already loaded.

Claim the task via `start_work` and note every AC line from the task body.

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

Determine max depth from AC `(td:N)` tags.

| Max depth | quality-runner expectation in builder notes | code-reader | Reviewer execution path |
|-----------|---------------------------------------------|-------------|-------------------------|
| td:0 | lint evidence only | skip | Step 4 checklist with lint + AC/file evidence |
| td:1 | scoped tests + lint | skip | Step 4 checklist with test/lint/file evidence |
| td:2 | scoped tests + lint + coverage | run | Step 4 checklist + code-reader cross-check |

For td:2, dispatch `code-reader` in parallel with your own file reading when needed.

### Code-Reader Consumer Contract

Inputs the reviewer provides:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Kanban task id |
| `ac_lines` | string[] | All AC lines from task body |
| `changed_files` | string[] | Builder-changed file paths |
| `test_files` | string[] | Task-scoped tests |

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
- [ ] Sole operative workflow is 3-item checklist (AC→code, test→AC, proof sufficiency)
- [ ] Code-reader contract uses only 4 output sections (`ac_to_code_mapping`, `test_to_ac_alignment`, `proof_sufficiency`, `observations`)
- [ ] Builder quality evidence reviewed first; independent rerun only when justified
- [ ] Evidence map includes every AC line
- [ ] Output note uses only `Review Evidence` + `Observations` sections near verdict
