---
id: 1355
title: 'P1-02: Write agent-deep-audit.prompt.md'
status: archived
priority: medium
created: 2026-05-04T21:22:32.030360+00:00
updated: 2026-05-05T16:47:45.062902+00:00
tags:
- phase-1
- scope:prompts
- prompt
- snr
parent: 1353
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## AC (from Brief AC2 + AC3 deep side)

**In scope:**
- Create `share/prompts/agent-deep-audit.prompt.md` (new file)
- Two scope modes: agent mode (agent + all referenced skills) and skill mode (skill + all consumer agents)
- Pre-analysis: map full dependency cluster, load files, understand unit before evaluating
- Core analysis: correctness, completeness, naming/structure, value-per-instruction, signal-to-noise (per-sentence), cross-file coherence
- Output: single structured proposal per target — structural proposals first, compression proposals second, issues third
- Interaction model: section-by-section approval via `askQuestions` (grouped by file), batch-approve escape hatch
- Conservative bias: lean toward keeping when uncertain; procedural sequences and institutional memory get extra protection
- Inline the shared 6-category noise taxonomy (matching definitions used in #1354)
- For universal skills (`applyTo: **`): pragmatic sampling — top 3-5 heaviest consumers

**Out of scope:**
- Ecosystem-wide coherence checks (that's the broad audit's job)
- Automated pipeline from broad audit findings
- Actually running the deep-dive on all files

**6-category noise taxonomy (inline in prompt):**
1. Verbose prose wrappers
2. Over-specification
3. Redundant conditionals
4. Prescriptive message templates
5. Cross-reference ceremony
6. Stale institutional memory

**Brief:** see parent #1353 → `.owlbear/briefs/draft-skill-snr/brief.md`

[[2026-05-05]]
## Research\n\nResearch gate passed — Brief provides full spec, prior art validated.\n\n### Key findings\n- Prior art: 3 internal prompt references (agent-audit pattern 250 lines, memory-audit askQuestions loop, frontend-audit scope+dimensions)\n- No existing equivalent for per-cluster deep-dive auditing\n- Dependency cluster mapping: `required_reading` + inline backtick references in agent body; reverse via `grep_search` for skill consumers\n- Target: `share/prompts/agent-deep-audit.prompt.md`\n- Frontmatter: `description:` only (no agent delegation, matching sibling #1354)\n- Input: `${input:mode}` (agent/skill) + `${input:target}` (name)\n- Structure: Preamble → Dependency Mapping → Core Analysis (6 sub-dimensions from AC) → Proposal Format → Interaction Model (askQuestions section-by-section) → Guardrails\n- Inline 6-category noise taxonomy with brief exact definitions\n- Estimated ~220 lines (within 300-line budget)\n- Universal skills: pragmatic sampling, top 3-5 heaviest consumers\n- Tier: T1 autonomous — no decisions needed\n- No follow-up tasks — implementation fully specified by Brief AC2 + AC3
[[2026-05-05]]


## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single prompt file, single purpose (deep-dive cluster audit) |
| Interface clarity | PASS | Inputs: `${input:mode}` (agent/skill) + `${input:target}` (name). Output: structured proposal. Interaction: section-by-section askQuestions |
| Dependency correctness | PASS | No deps; #1354 is independent — shared taxonomy fully specified inline |
| Module layering | N/A | Prompt file, no imports |
| TDD compliance | PASS | Tagged `prompt` (pass-through); #1356 serves as evaluation gate |
| KISS/YAGNI | PASS | Scope well-bounded by Brief; out-of-scope items explicit |
| Premise challenge | PASS | No existing deep-dive equivalent; `.owlbear/prompts/agent-audit.prompt.md` is broad-only |
| Pattern consistency | PASS | Frontmatter `description:` only matches sibling prompts (memory-audit, frontend-audit) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Prompt authoring only |

### Test Depth
- All AC lines: (td:0) — prompt file creation, no testable Python interface
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0, no challenge needed

### Verdict: APPROVE
### Action Taken: Approved to todo. Builder implements per Brief AC2+AC3 spec. Research section provides exact structure, input vars, and line budget.
[[2026-05-05]]
Architecture review complete. All criteria PASS/N/A. All AC lines td:0 (prompt file, no Python). Tagged `prompt` ensures test-writer pass-through. Approved to todo.
[[2026-05-05]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
- Rationale: task creates `share/prompts/agent-deep-audit.prompt.md` only — no Python source, no testable interface. Architecture review tagged td:0 on all AC lines.
[[2026-05-05]]
## Builder Notes
- Non-implementation task (prompt authoring with td:0 coverage profile) — no code changes required in builder phase.
- Test-writer pass-through honored; no TestFromAC execution applicable.
- Files changed: none.
- Lint/tests: not run (not applicable for td:0 prompt pass-through).
- Evidence summary: task body `## Test-Writer Notes` explicitly designates non-implementation pass-through and architect marked all AC lines td:0.
[[2026-05-05]]
## Review Evidence
### Review Scope
- Reviewed the task contract, parent brief, and the live `share/prompts/` directory.
- This is a td:0 prompt-authoring task. No task-local `TestFromAC_*` suite exists.
- `quality-runner` was not dispatched: td:0 review with no task test artifact; direct artifact inspection is the decisive evidence here.

### Test Results
- Not run.
- Reason: non-code td:0 prompt task and the required prompt artifact is absent.

### Lint Results
- Not run.
- Reason: `share/prompts/agent-deep-audit.prompt.md` does not exist, so there is no deliverable to lint.

### Coverage
- N/A (td:0 prompt task)

### Changed-File Reconstruction
| Source | Evidence |
|---|---|
| Task AC | `.owlbear/kanban/tasks/1355-p1-02-write-agent-deep-audit-prompt-md.md:25` requires creating `share/prompts/agent-deep-audit.prompt.md` |
| Builder notes | `.owlbear/kanban/tasks/1355-p1-02-write-agent-deep-audit-prompt-md.md:87-92` state "Non-implementation task" and `Files changed: none` |
| Parent brief | `.owlbear/briefs/draft-skill-snr/brief.md:56-79` and `.owlbear/briefs/draft-skill-snr/brief.md:105-122` require a new deep-dive prompt with agent/skill modes, dependency-cluster loading, structured proposal output, section-by-section `askQuestions`, and inline shared taxonomy |
| Workspace inspection | `share/prompts/` currently contains `design-context.prompt.md`, `frontend-audit.prompt.md`, `frontend-normalize.prompt.md`, `frontend-polish.prompt.md`, `ideation-discover.prompt.md`, `ideation-mediate.prompt.md`, `memory-audit.prompt.md`, `orchestrate.prompt.md`, and `test-curation.prompt.md`; `agent-deep-audit.prompt.md` is absent. Direct file search for `share/prompts/agent-deep-audit.prompt.md` returned no matches. |

### Findings
| Severity | Finding | Evidence |
|---|---|---|
| CRITICAL | The required deliverable was not created. The builder treated a file-creation task as pass-through and produced no prompt artifact. | Task AC requires the new file; the parent brief specifies its behavior; live workspace inspection shows the file does not exist. |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Create `share/prompts/agent-deep-audit.prompt.md` (new file) | Required by task AC; file absent from `share/prompts/`; direct file search returned no match | N/A (td:0) | FAIL |
| Two scope modes: agent mode (agent + all referenced skills) and skill mode (skill + all consumer agents) | Brief requires both modes, but no prompt file exists to implement or inspect them | N/A (td:0) | FAIL |
| Pre-analysis: map full dependency cluster, load files, understand unit before evaluating | Brief requires this pre-analysis behavior, but no prompt file exists to inspect | N/A (td:0) | FAIL |
| Core analysis: correctness, completeness, naming/structure, value-per-instruction, signal-to-noise (per-sentence), cross-file coherence | Brief requires these analysis dimensions, but no prompt file exists to inspect | N/A (td:0) | FAIL |
| Output: single structured proposal per target — structural proposals first, compression proposals second, issues third | Brief requires this output contract, but no prompt file exists to inspect | N/A (td:0) | FAIL |
| Interaction model: section-by-section approval via `askQuestions` (grouped by file), batch-approve escape hatch | Brief requires this interaction model, but no prompt file exists to inspect | N/A (td:0) | FAIL |
| Conservative bias: lean toward keeping when uncertain; procedural sequences and institutional memory get extra protection | Brief requires this guardrail, but no prompt file exists to inspect | N/A (td:0) | FAIL |
| Inline the shared 6-category noise taxonomy (matching definitions used in #1354) | Task AC and brief require the inline taxonomy, but no prompt file exists to inspect | N/A (td:0) | FAIL |
| For universal skills (`applyTo: **`): pragmatic sampling — top 3-5 heaviest consumers | Brief requires this rule, but no prompt file exists to inspect | N/A (td:0) | FAIL |

### Loop Detection
- CLEAN: no prior `## Review Evidence` section found in this task before this review.

### Deductions
- -0.75 missing primary deliverable
- -0.10 all behavioral AC lines unreviewable because the artifact does not exist
- -0.03 builder notes misclassified a file-creation task as non-implementation, reducing reviewability

### Verdict
- Confidence: .12
- FAIL -> in-progress
- Reason: implementation miss. The task cannot pass review until `share/prompts/agent-deep-audit.prompt.md` exists and matches Brief AC2 + AC3.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Create `share/prompts/agent-deep-audit.prompt.md` and implement the brief-defined deep-dive contract: agent/skill modes, dependency-cluster loading, structured proposal ordering, section-by-section `askQuestions`, conservative bias, and inline 6-category taxonomy | share/prompts/agent-deep-audit.prompt.md | `.owlbear/briefs/draft-skill-snr/brief.md:56-79`; `.owlbear/briefs/draft-skill-snr/brief.md:105-122`; task AC at `.owlbear/kanban/tasks/1355-p1-02-write-agent-deep-audit-prompt-md.md:25` |
| 2 | builder | Record the actual changed file path in task notes on retry so review can reconstruct scope without guesswork | share/prompts/agent-deep-audit.prompt.md | Current builder notes at `.owlbear/kanban/tasks/1355-p1-02-write-agent-deep-audit-prompt-md.md:87-92` incorrectly state `Files changed: none` |
[[2026-05-05]]
## Builder Notes
- Implementation: created `share/prompts/agent-deep-audit.prompt.md`.
- Scope contract implemented: dual mode (`agent`/`skill`), dependency-cluster pre-analysis, 6 core analysis dimensions, ordered proposal output (structural -> compression -> issues), section-by-section `askQuestions` approval, and batch-approve escape hatch.
- Taxonomy: inlined all 6 required noise categories with matching definitions and compression actions.
- Universal-skill handling: included pragmatic sampling guidance (top 3-5 heaviest consumers) with sampled-vs-total reporting.
- Tests: not run (td:0 prompt-authoring task; no `TestFromAC_*` artifacts and no Python/runtime surface).
- Coverage: N/A (non-executable prompt deliverable).
- Lint: not run (markdown prompt-only change).
- Evidence summary: task-required file now exists and was committed in `5a12dddf` (`feat: add deep audit prompt (#1355, builder)`).

### Reflection
- Prior pass-through treatment was incorrect for this task type; td:0 still required a concrete prompt artifact.
- Directly mirroring sibling prompt patterns plus brief AC sections reduced ambiguity and avoided speculative structure.
- Recording explicit output-order and interaction-contract language in the prompt should improve reviewer traceability.
[[2026-05-05]]
## Review Evidence
### Review Scope
- Second-cycle review of a td:0 prompt-authoring task.
- Reviewed the task AC, parent brief AC2/AC3, the live prompt artifact at `share/prompts/agent-deep-audit.prompt.md`, builder retry notes, local git log entries for the claimed commit, and editor diagnostics for the prompt file.
- `quality-runner` was not dispatched. This task is td:0 with no task-local test artifact, and the current reviewer workflow for td:0 prompt tasks relies on direct artifact inspection rather than an invalid empty `test_paths` run.

### Test Results
- Not run.
- Reason: td:0 prompt-authoring task; no `TestFromAC_*` suite or executable runtime surface is in scope.

### Lint Results
- `quality-runner` lint not run for the same td:0 reason above.
- Editor diagnostics for `share/prompts/agent-deep-audit.prompt.md`: no errors found.

### Coverage
- N/A (td:0 prompt task)

### Changed-File Reconstruction
| Source | Evidence |
|---|---|
| Task AC | Required artifact is `share/prompts/agent-deep-audit.prompt.md`. |
| Builder retry notes | `.owlbear/kanban/tasks/1355-p1-02-write-agent-deep-audit-prompt-md.md:159` records `Implementation: created share/prompts/agent-deep-audit.prompt.md`; line 166 records commit `5a12dddf` (`feat: add deep audit prompt (#1355, builder)`). |
| Workspace state | `share/prompts/agent-deep-audit.prompt.md` exists and `share/prompts/` lists it alongside sibling prompt files. |
| Git log presence | `.git/logs/HEAD:2001` and `.git/logs/refs/heads/dev:1842` both contain commit `5a12dddfdb869dbb7c8bc9dad95c5351f27ba57b` with message `feat: add deep audit prompt (#1355, builder)`. |

### Test-Writer Audit
- N/A. No `TestFromAC_*` classes exist for this td:0 prompt task.

### Test Integrity
- N/A. No task-local tests were authored or modified.

### Builder Process Quality
| Check | Evidence | Status |
|---|---|---|
| Retry count | Two `## Builder Notes` sections exist at task lines 89 and 158 | FRICTION |
| Approach variation | First cycle incorrectly treated td:0 as pass-through; second cycle created the required artifact and recorded a commit | CLEAN enough for pass |
| Loop trigger | Only one review retry; no repeated identical approach after the failure | PASS |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Create `share/prompts/agent-deep-audit.prompt.md` (new file) | File exists in `share/prompts/`; builder retry note at task line 159 records creation | N/A (td:0) | PASS |
| Two scope modes: agent mode (agent + all referenced skills) and skill mode (skill + all consumer agents) | `share/prompts/agent-deep-audit.prompt.md:9-10` define mode/target inputs; `:52-90` defines Agent Mode and Skill Mode loading behavior | N/A (td:0) | PASS |
| Pre-analysis: map full dependency cluster, load files, understand unit before evaluating | `share/prompts/agent-deep-audit.prompt.md:92-101` requires pre-analysis completion, dependency-cluster mapping, full file loading, and operational-purpose summary before judgment | N/A (td:0) | PASS |
| Core analysis: correctness, completeness, naming/structure, value-per-instruction, signal-to-noise (per-sentence), cross-file coherence | `share/prompts/agent-deep-audit.prompt.md:110`, `:116`, `:122`, `:128`, `:134`, and `:144` define those six dimensions explicitly | N/A (td:0) | PASS |
| Output: single structured proposal per target — structural proposals first, compression proposals second, issues third | `share/prompts/agent-deep-audit.prompt.md:150-168` defines the single output package and exact ordering | N/A (td:0) | PASS |
| Interaction model: section-by-section approval via `askQuestions` (grouped by file), batch-approve escape hatch | `share/prompts/agent-deep-audit.prompt.md:172-187` requires `askQuestions`, groups by file, forbids unapproved changes, and offers the batch-approve escape hatch | N/A (td:0) | PASS |
| Conservative bias: lean toward keeping when uncertain; procedural sequences and institutional memory get extra protection | `share/prompts/agent-deep-audit.prompt.md:23-27` encodes conservative bias and explicit protection for procedures and institutional memory | N/A (td:0) | PASS |
| Inline the shared 6-category noise taxonomy (matching definitions used in #1354) | `share/prompts/agent-deep-audit.prompt.md:29-49` inlines all six categories; `share/prompts/agent-broad-audit.prompt.md:149-154` contains the sibling broad-audit taxonomy with the same six category definitions in semantically matching form | N/A (td:0) | PASS |
| For universal skills (`applyTo: **`): pragmatic sampling — top 3-5 heaviest consumers | `share/prompts/agent-deep-audit.prompt.md:84-88` requires pragmatic sampling, heaviest-consumer ranking, top 3-5 loading, and sampled-vs-total reporting | N/A (td:0) | PASS |

### Findings
| Severity | Finding | Evidence |
|---|---|---|
| INFO | AC3 taxonomy wording is not verbatim with the sibling broad-audit prompt, but the category meanings align and no contradictory definition was introduced. | Deep prompt `:31-49` vs broad prompt `:145-154` |
| INFO | Full `git diff` / `git status` contamination checks were not available in the current tool surface, so ownership confidence relies on task notes, live artifact inspection, and `.git/logs` commit presence rather than a commit diff. | `.git/logs/HEAD:2001`; `.git/logs/refs/heads/dev:1842` |

### Deductions
- -0.03 no direct `git diff` / `git status` evidence in current tool surface
- -0.02 taxonomy definition match is semantic rather than verbatim

### Verdict
- Confidence: .93
- PASS -> docs
- Reason: the required prompt artifact now exists, the deep-audit contract from Brief AC2 is implemented end-to-end, AC3's shared taxonomy is present and materially aligned with the sibling prompt, and the file has no editor diagnostics.

### Action
- Advanced to `docs`.
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope doc references `agent-deep-audit`; grep confirmed hits only in kanban task files and doc-index |
| 2 | Module docstrings | No | N/A | No Python files modified |
| 3 | External attribution | No | N/A | No external patterns cited in research or builder notes |
| 4 | Research doc | No | N/A | Research done inline in task body; no `.owlbear/research/` slug produced |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram describes-match for `share/prompts/` files |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in AC |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/prompts/agent-deep-audit.prompt.md | OUT (agent-executable prompt) | N/A — not editable by doc-writer |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1355-*` files found)

No docs impact — all checklist items N/A. Single deliverable is an agent-executable prompt file, outside doc-writer scope.
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---|---|---|
| Create `share/prompts/agent-deep-audit.prompt.md` (new file) | File exists (210 lines); commit `5a12dddf` verified via `git log` | PASS |
| Two scope modes: agent/skill | Lines 52-90 define Agent Mode and Skill Mode with loading rules | PASS |
| Pre-analysis: map dependency cluster, load files, understand unit | Lines 92-101 require pre-analysis completion before evaluation | PASS |
| Core analysis: 6 dimensions | Lines 110-144 define correctness, completeness, naming/structure, value-per-instruction, signal-to-noise, cross-file coherence | PASS |
| Output: structural → compression → issues ordering | Lines 150-168 define single structured proposal with exact ordering | PASS |
| Interaction model: section-by-section askQuestions + batch-approve | Lines 172-187 require askQuestions per-file grouping and batch escape hatch | PASS |
| Conservative bias | Lines 23-27 encode conservative defaults with procedure/memory protection | PASS |
| Inline 6-category noise taxonomy | Lines 29-49 inline all 6 categories with definitions and compression actions | PASS |
| Universal skills: pragmatic sampling top 3-5 | Lines 84-88 require heaviest-consumer ranking and sampled-vs-total reporting | PASS |

### Test Results
- Full suite via quality-runner: pytest collection error (pre-existing `serve/kanban/tests` import issue); vitest 13 failures (all in unrelated cockpit components). None attributable to this task — a `.md` file in `share/prompts/` has zero runtime impact.

### Lint Results
- Ruff: 12 violations (all in `serve/knowledge/` and `serve/tools/` — unrelated)
- ESLint: 4 violations (cockpit — unrelated)
- No lint applies to the task deliverable (markdown prompt).

### Reviewer Evidence
- Second-cycle review is thorough: all 9 AC lines mapped to specific line ranges with PASS verdicts. Process quality checks present. Confidence .93 with documented deductions.

### Commit Integrity
- `5a12dddf feat: add deep audit prompt (#1355, builder)` — verified via `git log --oneline -5`.

### AC Quality Score: 4/5
- AC was specific with clear in/out scope, enumerated behavioral requirements, and explicit taxonomy. Brief filled structural gaps. Minor: could have specified section ordering in AC itself rather than deferring to brief.

### Deductions
- None. All AC lines have specific evidence. Lint/test issues are pre-existing and unrelated. Reviewer section is present and detailed. AC quality > 3.

### Confidence: .99
### Action: ARCHIVE