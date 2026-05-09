---
name: w-doc-update
description: "Workflow: Documentation update — verify and update docs for completed tasks"
user-invocable: false
---

# Documentation Update (v3)

Verify and update documentation for a task that has passed review. This revision uses
a four-item checklist, convention mapping, and a two-layer verification method.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Scope

### In Scope

- Verify README targets via convention mapping.
- Update external attribution.
- Verify research-doc linkage.
- Detect deletion impact and orphaned references.
- Add TODO markers for pre-existing unresolved documentation issues.

### Out of Scope

- Fixing runtime code — builder (`w-tdd-green`), routed via reviewer (`w-code-review`).
- Writing tests — test-writer (`w-tdd-red`).
- Code review — reviewer (`w-code-review`).
- Full-suite regression — auditor (`w-task-verification`).
- AC quality validation — architect (`w-arch-review`).

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

Claim the task via `start_work` (atomic claim + retrieves task body). Check the retrieved
body for resolved decision/action requests per pipeline-protocol → Task Setup → Resolved
Decision Pre-flight.

Verify the task is in `docs` status.

## Step 1 — Convention Mapping

Use convention mapping to determine documentation targets:

| Code Path Pattern | Mapped Documentation |
|---|---|
| `serve/{pkg}/src/**` | `serve/{pkg}/README.md` |
| `serve/{pkg}/pyproject.toml`, `serve/{pkg}/tests/**` | `serve/{pkg}/README.md` |
| `setup/**` | `setup/setup-guide.md`, `setup/sharing-guide.md` |
| `share/**` | `share/README.md`, `share/WIRING.md` |
| Any package's public interface changes | `README.md`, `README-consumer.md` (LLM judgment) |

If all changed files map to no READMEs, use the no-impact fast path: write
"no docs impact" with evidence and advance.

## Step 2 — Relevance-Gated Checklist (Exactly 4 Items)

Evaluate only applicable checks.

### Item 1: README Verification

- Use convention mapping to identify each `serve/{pkg}/README.md` target.
- Perform a full-file read for every mapped README.
- Layer 1: run grep-based structural checks for removed symbols/commands/flags.
- Layer 2: perform LLM editorial comparison for coherence and contradictions.
- Fix task-caused issues inline.
- For pre-existing unresolved issues, insert a visible TODO marker.

### Item 2: External Attribution

- If external sources influenced implementation, add/update
  `.owlbear/sources/overview.md`.
- If no external sources were used: record "N/A — no external attribution needed".

### Item 3: Research Doc

- If a research file exists, verify it is linked from the task body.
- If no research artifact exists: record "N/A — no research doc linkage needed".

### Item 4: Deletion Detection

- Detect when source files were deleted in this task and whether mapped docs now
  contain orphaned references.
- When deletion impact needs coordinated remediation, create a child task for the
  follow-up doc update.
- Open a DR (Decision Request) when ownership, sequencing, or scope is ambiguous.
- If no deletion impact exists: record "N/A — no deletion impact".

Apply visible TODO markers for unresolved documentation issues so they remain reviewable.

TODO marker format (always visible and greppable):

> **TODO:** {category} — {description} [#{id}]

Allowed categories:

- `stale`
- `inaccurate`
- `missing`
- `unverified`

Concrete example:

> **TODO:** stale — update outdated CLI flag description [#{id}]

Gate rules:

- task-caused unverified content blocks the gate.
- pre-existing unverified content passes the gate.

## Step 3 — Two-Layer Verification

Run both layers for every documentation update pass.

- Layer 1 — grep-based structural verification:
  confirm removed phrases are absent and required markers (like `> **TODO:**`) are present.
- Layer 2 — LLM editorial verification:
  perform a full-file editorial read for coherence, audience fitness, and contradictions.

Both layers must be documented in the task note with concrete evidence.

## Step 4 — Clean Scratch Files

Look for `.owlbear/scratch/{task-id}-*` files and delete any that exist.

## Step 5 — Commit & Advance

If you created or modified files, commit them before advancing.

Then advance via `end_work` (moves to `done` + releases claim).

## Output Template

Append to task body before advancing:

```markdown
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | {Yes/No} | {Updated/N/A} | {details} |
| 2 | External attribution | {Yes/No} | {Updated/N/A} | {details} |
| 3 | Research doc | {Yes/No} | {Updated/N/A} | {details} |
| 4 | Deletion detection | {Yes/No} | {Updated/N/A} | {details} |

### Verification Layers
- Layer 1 — {grep structural evidence}
- Layer 2 — {LLM editorial evidence}

### Files Updated
- {list or "None"}

### Scratch Files Cleaned
- {list or "None"}
```

## Verification Checklist

- [ ] Task is in `docs` status
- [ ] Checklist has exactly 4 items evaluated with evidence
- [ ] Convention mapping `serve/{pkg}/src/**` → `serve/{pkg}/README.md` applied
- [ ] Layer 1 structural grep verification completed
- [ ] Layer 2 editorial verification completed
- [ ] TODO marker format enforced where needed
- [ ] task-caused unverified content blocks
- [ ] pre-existing unverified content passes
- [ ] No application logic changes
- [ ] Scratch cleanup complete
- [ ] Documentation changes committed before advancing
