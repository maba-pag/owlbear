---
id: 1459
title: 'B1-agent: Update code-reader agent to match new w-code-review contract'
status: archived
priority: medium
created: 2026-05-08T19:47:13.556859+00:00
updated: 2026-05-09T10:23:26.801346+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
- agent
parent: 1403
depends_on:
- 1458
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Update `share/agents/code-reader.agent.md` to align with the new w-code-review consumer contract. The 8-section output (test_writer-audit, security_review, test_integrity, test_quality, data_safety, test_gaps, necessity_check, informational) is replaced by the 3-item checklist model. Update persona, critical_rules, output_format, and examples.


## Acceptance Criteria

- [ ] `output_format` section in `share/agents/code-reader.agent.md` specifies exactly 4 required output sections matching the w-code-review consumer contract: `## ac_to_code_mapping`, `## test_to_ac_alignment`, `## proof_sufficiency`, `## observations` — old 8-section list removed (td:1)
- [ ] `critical_rules` references the 3-item checklist (Steps 4.1–4.3 of w-code-review: AC→Code Mapping, Test→AC Alignment, Proof Sufficiency) — old §5.0–5.7 / §6.1–6.4 references removed (td:1)
- [ ] All references to the old 8-section model (`test_writer-audit`, `security_review`, `test_integrity`, `test_quality`, `data_safety`, `test_gaps`, `necessity_check`, `informational`) removed from `share/agents/code-reader.agent.md` (td:1)
- [ ] Examples demonstrate findings in the new 4-section format — old 8-section examples replaced (td:1)
- [ ] Persona and boundaries remain adversarial + read-only; no new tools or kanban access added (td:0)

## Builder Guidance

- The authoritative consumer contract is in `share/skills/w-code-review/SKILL.md` → `### Code-Reader Consumer Contract` (input fields unchanged; output sections changed to 4)
- The `<required_reading>` reference to `w-code-review` stays — that's the contract source
- The `description` and `argument-hint` in YAML frontmatter may need minor wording updates but are not load-bearing
- Scope is strictly `share/agents/code-reader.agent.md` — do NOT modify research docs, archived tasks, or w-code-review itself
[[2026-05-09]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single agent file update to match its consumer contract |
| Interface clarity | PASS | AC explicitly names all 4 output sections and the 3-item checklist references |
| Dependency correctness | PASS | #1458 (w-code-review rewrite) is archived/done — contract already landed |
| Module layering | PASS | Agent file reads skill via required_reading — correct direction |
| TDD compliance | PASS | Non-impl task tagged `agent` for test-writer pass-through |
| KISS/YAGNI | PASS | Minimal scope — align one agent file to its already-landed contract |
| Premise challenge | PASS | code-reader.agent.md references 8-section model that no longer exists in w-code-review; update is necessary |
| Pattern consistency | PASS | Follows agent file structure conventions |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Pipeline/agents domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.47)
- Key challenges: (1) task artifact needed explicit AC — addressed via REFINE, (2) missing `agent` pass-through tag — added, (3) AC scope ambiguity on "remove old references" — scoped to target file
- Architect response: accepted all three; refined AC and tags before approving. Challenger confidence was low because the task artifact hadn't been refined yet at evaluation time.

### Test Depth
- Max depth: td:1 (4 lines) + td:0 (1 line)
- Test-writer: SKIP (non-impl task, `agent` tag triggers pass-through)

### Verdict: APPROVE
### Action Taken: Refined AC with explicit 4-section output contract, scoped file boundaries, and builder guidance. Added `agent` pass-through tag. Advanced to todo.
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- Scope is strictly `share/agents/code-reader.agent.md` (agent file update); no Python or TypeScript interfaces to test.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Files changed: `share/agents/code-reader.agent.md`
- Implementation summary:
  - Updated `critical_rules` to reference the new 3-item checklist in `w-code-review` Step 4.1-4.3 (AC->Code Mapping, Test->AC Alignment, Proof Sufficiency), removing legacy section references.
  - Updated `output_format` to require exactly the 4 contract sections: `## ac_to_code_mapping`, `## test_to_ac_alignment`, `## proof_sufficiency`, `## observations`.
  - Removed all legacy 8-section model names from the agent file.
  - Reworked examples to demonstrate findings in the new 4-section format.
  - Preserved adversarial/read-only persona and boundaries; no tool or kanban capability changes.
- Quality evidence:
  - quality-runner (scoped lint-only): markdownlint PASS on `share/agents/code-reader.agent.md` (exit code 0, clean=true).
  - Tests: not applicable for this non-code agent contract update.
  - Coverage: not applicable.
- Commits:
  - `1d828ead` feat: align code-reader output contract (#1459, builder)
  - `36c734d6` chore: lint-safe code-reader examples (#1459, builder)
[[2026-05-09]]
## Review Evidence
### Scoped Evidence
- Reviewed file: `share/agents/code-reader.agent.md`
- Changed-file scope reconstructed from task AC + builder notes (`Files changed: share/agents/code-reader.agent.md`).
- Builder commit presence confirmed in git logs: `.git/logs/refs/heads/dev:2237-2238` and `.git/logs/HEAD:2422-2423` show `1d828ead` and `36c734d6` for task `#1459`.
- Independent quality-runner rerun: Tests `passed: 0`, `failed: []`, `skipped: 0`; Lint `clean: true`, `violations: []`; Coverage `N/A`; Errors `none`.
- Problems check: no editor errors for `share/agents/code-reader.agent.md`.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| `output_format` specifies exactly 4 required sections (`ac_to_code_mapping`, `test_to_ac_alignment`, `proof_sufficiency`, `observations`) and removes old 8-section list | `share/agents/code-reader.agent.md:52` references the 4-section contract only; consumer contract matches at `share/skills/w-code-review/SKILL.md:78-84` | PASS |
| `critical_rules` references the 3-item checklist (Step 4.1-4.3) and removes old §5/§6 references | `share/agents/code-reader.agent.md:41-43` cites Step 4.1-4.3 and the 3-item checklist; source workflow defines the checklist at `share/skills/w-code-review/SKILL.md:98-114` and verifies it at `share/skills/w-code-review/SKILL.md:160-161` | PASS |
| All references to the old 8-section model removed from `share/agents/code-reader.agent.md` | Search for `test_writer-audit|security_review|test_integrity|test_quality|data_safety|test_gaps|necessity_check|informational` in `share/agents/code-reader.agent.md` returned no matches | PASS |
| Examples demonstrate findings in the new 4-section format | Example blocks start at `share/agents/code-reader.agent.md:77` and `share/agents/code-reader.agent.md:101`; section headings appear at `share/agents/code-reader.agent.md:78,82,86,90,102,106,110,114`; old-model bad-example replaced at `share/agents/code-reader.agent.md:95` | PASS |
| Persona and boundaries remain adversarial + read-only; no new tools or kanban access added | Adversarial/read-only persona preserved at `share/agents/code-reader.agent.md:19,23,29`; read-only / no kanban rules at `share/agents/code-reader.agent.md:42,56,63-64`; tool allowlist remains read/search-only at `share/agents/code-reader.agent.md:8-9` | PASS |

### Test / Lint / Coverage Summary
- Tests: Not applicable for this non-implementation agent-contract update. Independent quality-runner rerun found no scoped executable tests to run.
- Lint: PASS (`clean: true`, `violations: []`).
- Coverage: Not applicable.

### Deductions
- `-0.03` No direct `git diff` / `git status` tool surface here, so changed-file scope and contamination check were reconstructed from task notes and current file evidence; commit existence was verified via `.git/logs/**` rather than full diff inspection.

### Verdict
- PASS `#1459 -> docs | code-reader.agent.md matches the live 4-section consumer contract; legacy 8-section references are gone; lint is clean.`
- Confidence: `0.95`

## Observations
- This task is correctly treated as a non-code agent-file contract update. File inspection plus lint is sufficient evidence here because the ACs are documentation/agent-configuration only, not runtime behavior.
- The live workspace `share/skills/w-code-review/SKILL.md` is already on the new 4-section contract, so the agent file and its consumer are aligned.
[[2026-05-09]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `share/README.md` lines 66 and 74 mention `code-reader` by name (T4 tier listing and ND3 agents list) — neither references its output format or section contract; both remain accurate after contract change. No prose update needed. |
| 2 | Module docstrings | No | N/A | No Python modules changed |
| 3 | External attribution | No | N/A | No external patterns referenced in builder notes |
| 4 | Research doc | No | N/A | No research doc mentioned in task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/pipeline.excalidraw` has `describes: ..., share/agents/*.agent.md` — glob matches `share/agents/code-reader.agent.md`. Footer updated from `(41ece747)` to `(90edd62c)`. Commit: `fafa9147`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request |
| 7 | Deletion detection | No | N/A | No files deleted; `share/agents/code-reader.agent.md` updated, not removed |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `share/agents/code-reader.agent.md` | OUT (agent-executable) | No edit — changed by builder |
| `share/diagrams/pipeline.excalidraw` | IN (diagram) | Footer updated (describes-match) |

### Files Updated
- `share/diagrams/pipeline.excalidraw` — footer timestamp updated to `2026-05-09 (90edd62c)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1459-*` scratch files existed)
[[2026-05-09]]
## Audit
### Regression Detection
- quality-runner mode full: Python 4871 passed / 572 failed, Frontend 1215 passed / 9 failed, Lint violations present
- All failures in cockpit cache/SSE/decisions/error-envelope modules — pre-existing, unrelated to this task's single markdown file change
- regression verdict: PASS (no regressions attributable to #1459)

### Intent Verification
- scope alignment: PASS (changed files: `share/agents/code-reader.agent.md`, `share/diagrams/pipeline.excalidraw` footer — both in pipeline/agents domain)
- purpose match: PASS (4-section output contract aligned with live `w-code-review` consumer contract; 3-item checklist references present; legacy 8-section model fully removed)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
- AC lines name exact output sections, reference exact checklist steps, scope to single file
- Minor: AC4 slightly vague on "demonstrate" but adequately handled by builder/reviewer

### Commit Integrity
- upstream commit presence: PASS (`1d828ead` feat, `36c734d6` lint-fix, `fafa9147` doc-writer — all verified in git log)
- kanban commit packaging: pending (this audit)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive