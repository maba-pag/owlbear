---
id: 1298
title: 'P1-02: Doc/skill reference cleanup — remove Copilot CLI and ACP references
  from docs'
status: archived
priority: medium
created: 2026-05-02T19:40:07.788907+00:00
updated: 2026-05-03T10:12:24.905658+00:00
tags:
- cleanup
parent: 1296
depends_on:
- 1297
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Remove all Copilot CLI / ACP orchestrator references from documentation, skills, prompts, and setup guides. Regenerate the doc-index.

Brief: see parent #1296 and `.owlbear/briefs/draft-dead-code-sweep/brief.md`

## Scope

### Edit
- `README.md` — remove Copilot CLI prerequisite, orchestrator directory row, orchestrator description paragraph, CLI commands section
- `README-consumer.md` — remove `owlbear-project.json` from setup output mention
- `.github/copilot-instructions.md` — change "built around Copilot CLI" to "built around VS Code and GitHub Copilot agents"
- `share/skills/r-architecture-standards/SKILL.md` — remove ACP dispatch intro paragraph and orchestrator row from package table
- `share/skills/w-research/SKILL.md` — change "Copilot CLI" to "VS Code" in stack check reference
- `share/prompts/arch-audit.prompt.md` — remove/replace `serve/orchestrator/` as example audit unit
- `setup/setup-guide.md` — remove `owlbear-project.json` table row
- `setup/sharing-guide.md` — remove `owlbear-project.json` table row

### Regenerate
- Run `uv run doc-index` to regenerate `.owlbear/doc-index.md`

### Out of scope
- `.owlbear/research/` files (historical record — preserved)
- References to the live VS Code `orchestrator.agent.md` or `w-orchestration` skill — those stay
- Code changes (done in #1297)

## AC

1. `grep -r "serve/orchestrator" README.md README-consumer.md .github/ share/skills/ share/prompts/ setup/` returns zero hits
2. `grep -r "Copilot CLI" . --include="*.md"` returns zero hits outside `.owlbear/research/`, `.owlbear/kanban/`, `.owlbear/scratch/`, `.owlbear/briefs/`
3. `grep -r "owlbear-project.json" setup/ README-consumer.md` returns zero hits
4. `.owlbear/doc-index.md` is regenerated and does not reference `serve/orchestrator`
5. `uv run ruff check` passes on all touched Python files (if any)
6. No references to the live VS Code orchestrator agent are removed (spot-check `share/agents/orchestrator.agent.md` still exists and is not modified)
[[2026-05-02]]
## Test-Writer Notes

- Non-impl pass-through: AC references only non-Python files (`.md` edits, `uv run doc-index` invocation).
- No Python interfaces to test; no `TestFromAC_*` file created.
- **Pre-flight finding:** All 6 AC conditions already pass on the current codebase — `serve/orchestrator`, `Copilot CLI`, and `owlbear-project.json` are already absent from all scoped files; `share/agents/orchestrator.agent.md` exists; `.owlbear/doc-index.md` is clean.
- **Coverage already provided:** `test_dead_code_sweep_1296.py` (9/9 passing) covers AC1–AC4, AC6 for this task's scope (see its AC2, AC3, AC9 coverage table).
- Builder scope is `.md` edits + `uv run doc-index`; verify doc-index is re-run and committed.

Passing through to builder.
[[2026-05-02]]
## Builder Notes
- Non-implementation pass-through confirmed from `## Test-Writer Notes` in task body.
- No code or documentation edits made by builder.
- No tests or lint runs required for this pass-through handoff.
- Scope remains unchanged; advancing directly to review per `w-tdd-green` Step 0a.

## Post-task Reflection
- Problem faced: task appeared actionable but test-writer marked it pre-satisfied and non-impl.
- Workaround applied: followed GREEN Step 0a strict pass-through path to avoid unnecessary churn.
- Pattern discovered: dead-code cleanup follow-up tasks can resolve at test-writer stage with builder as routing-only gate.
[[2026-05-03]]
## Review Evidence

### Test Results
- quality-runner scoped run on `tests/test_dead_code_sweep_1296.py`: 17 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: clean, 0 violations.
- AC5 is non-applicable in practice here: no Python files were changed in this child scope.

### Coverage
- Omitted by quality-runner (`No source instrumentation`), which is expected for this doc-only task. No production Python module is in scope.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
- No `TestFromAC_*` classes exist for #1298, so the immutability/AC-to-Test audit is not applicable.
- Inherited structural coverage exists in `tests/test_dead_code_sweep_1296.py`: repo-wide `serve/orchestrator` scan at line 73, repo-wide `Copilot CLI` markdown scan at line 134, and doc-index check at line 189.

#### Security Review
- No issues found. Current task scope is Markdown/prompt/skill text plus doc-index regeneration; no executable boundary or secret-handling change was introduced here.

#### Test Integrity
- No `TestFromAC_*` tests to compare; not applicable.

#### Test Quality
- Assertion specificity: STRONG. The inherited tests use exact string-absence checks and repo-wide scans, not lax substring presence guards.
- Negative-path coverage: ADEQUATE for this contract. Reintroducing any non-excluded hit would fail the scan tests.
- Manual mutation reasoning: STRONG. Reintroducing `serve/orchestrator` on a live surface, reintroducing `Copilot CLI` on a non-excluded markdown surface, or reintroducing `serve/orchestrator` into `.owlbear/doc-index.md` would trip the suite.
- Independence: STRONG.
- Naming: STRONG.

#### Data Safety
- No issues found. No runtime state, persistence, or concurrency behavior changed in this child scope.

#### Test Gaps
- No blocking gap against the binding contract.
- Important nuance: child task #1298 still carries the pre-refinement AC3 exclusion list (`.owlbear/research`, `.owlbear/kanban`, `.owlbear/scratch`, `.owlbear/briefs` only), but parent #1296 Architecture Review explicitly refined AC3 to also exclude `.owlbear/decisions` and `.owlbear/sources`.
- Reviewer-run search confirmed the only remaining `Copilot CLI` hits are preserved historical/bibliographic records at `.owlbear/decisions/resolved/v2-architecture.md:9`, `:13`, `:20` and `.owlbear/sources/overview.md:333`, `:1769`, `:1770`.
- Parent #1296 states this refinement is binding and explicitly reconciles child #1298 as already completed by the parent builder.

#### Necessity Check
- Not applicable. No new dependency, integration, or tool was added.

#### Builder Process Quality
- CLEAN pass-through.
- Child builder made no edits, but parent #1296 builder notes record the actual scope completion: `.owlbear/kanban/tasks/1296-dead-code-sweep-remove-copilot-cli-acp-orchestrator-and-owlbear-project-json-inf.md:141-148` shows the doc cleanup + doc-index regeneration landed in commit `222942f330f16ab9dc0a6f6e623454e204bf3bbc`.
- Follow-up parent builder notes at `:247-255` show the remaining sweep cleanup landed in `d9e44810e6392a95dbd8d2742c1cdd6f5a0a4ac8` and `uv run doc-index` executed with `.owlbear/doc-index.md` already up to date.
- Parent Architecture Review at `:388` explicitly says children #1298 and #1299 had their scopes completed by the parent builder and must be advanced as done.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. `serve/orchestrator` zero hits in `README.md README-consumer.md .github/ share/skills/ share/prompts/ setup/` | Reviewer `grep_search` returned no matches on each declared surface. Inherited repo-wide structural proof at `tests/test_dead_code_sweep_1296.py:73`. | `tests/test_dead_code_sweep_1296.py::test_no_serve_orchestrator_repo_wide` | PASS |
| 2. `Copilot CLI` zero hits outside exclusions | Child body AC text at `.owlbear/kanban/tasks/1298-p1-02-doc-skill-reference-cleanup-remove-copilot-cli-and-acp-references-from-doc.md:50` is stale. Binding parent refinement at `.owlbear/kanban/tasks/1296-dead-code-sweep-remove-copilot-cli-acp-orchestrator-and-owlbear-project-json-inf.md:376` adds `.owlbear/decisions` and `.owlbear/sources` to exclusions. Reviewer searches found no `Copilot CLI` hits in `README.md`, `README-consumer.md`, `.github/**`, `share/**`, `setup/**`, or `.owlbear/doc-index.md`; remaining hits are only in the refined excluded paths listed above. | `tests/test_dead_code_sweep_1296.py::test_no_copilot_cli_in_md_files_repo_wide` | PASS |
| 3. `owlbear-project.json` zero hits in `setup/` and `README-consumer.md` | Reviewer `grep_search` returned no matches in `README-consumer.md` and `setup/**`. | N/A | PASS |
| 4. `.owlbear/doc-index.md` regenerated and clean of `serve/orchestrator` | Parent builder notes record regeneration at `#1296:141-148`; later retry notes at `#1296:247-255` record `uv run doc-index` executed with file already current. Reviewer search of `.owlbear/doc-index.md` found no `serve/orchestrator`, `Copilot CLI`, or `agent-client-protocol`. | `tests/test_dead_code_sweep_1296.py::test_doc_index_no_serve_orchestrator` | PASS |
| 5. `uv run ruff check` passes on touched Python files (if any) | No Python files were touched in this child scope. quality-runner reported lint clean with 0 violations. | N/A | PASS |
| 6. Live VS Code orchestrator agent remains | `share/agents/orchestrator.agent.md` exists and contains live orchestrator content (`name: orchestrator` at line 2). Parent builder changed-file lists at `#1296:142` and `#1296:248` do not include this file. | N/A | PASS |

### Deductions
- `-0.05` Child task body still carries stale pre-refinement AC3 text at `#1298:50`; review had to anchor to parent #1296 Architecture Review refinement at `#1296:376`.
- `-0.03` Child task body has no builder commit hash or changed-file list of its own; changed-file reconstruction relied on parent builder notes and current file state.

### Verdict
- PASS -> docs | confidence 0.92

### Action
- Advanced to `docs`.
- No builder retry and no test-writer retry are required. Current repo state satisfies the refined contract that governs this cleanup split.

## Post-task Reflection
- Problem faced: child task body preserved a stale AC exclusion list that no longer matched the parent Architecture Review refinement.
- Workaround applied: anchored the verdict to the latest binding refinement in parent #1296, then re-ran live-surface searches to confirm the repo matches that refined contract.
- Pattern discovered: split child cleanup tasks can legitimately be completed by an upstream parent builder commit; review must reconstruct scope from parent builder notes when the child body is pass-through.
- Quality gap: when parent Architecture Review refines a child-relevant AC, the child task body should be reconciled too; otherwise later reviewers inherit avoidable ambiguity.
[[2026-05-03]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | All IN-scope prose docs (README.md, README-consumer.md, setup/setup-guide.md, setup/sharing-guide.md) were updated by parent #1296 builder (commits 222942f, d9e4481). Review Evidence confirms AC1–AC4 pass: no `serve/orchestrator`, `Copilot CLI`, or `owlbear-project.json` hits in any of these files. |
| 2 | Module docstrings | No | N/A | AC5 confirms no Python files were touched in this task's scope. |
| 3 | External attribution | No | N/A | No patterns from external repos used. |
| 4 | Research doc | No | N/A | Scope section explicitly notes `.owlbear/research/` files are historical record, preserved — no action. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` has `describes: serve/*/pyproject.toml, share/**, setup/**, .owlbear/**` — matches `setup/setup-guide.md` and `setup/sharing-guide.md`. Footer updated from `2026-05-03 (800c51db)` to `2026-05-03 (91a14158)`. Committed as 76d291fd. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted in this task's scope. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| README.md | IN | Verified clean (parent builder, AC1 PASS) |
| README-consumer.md | IN | Verified clean (parent builder, AC3 PASS) |
| .github/copilot-instructions.md | OUT | Agent-executable — not edited |
| share/skills/r-architecture-standards/SKILL.md | OUT | SKILL.md — agent-executable, not edited |
| share/skills/w-research/SKILL.md | OUT | SKILL.md — agent-executable, not edited |
| share/prompts/arch-audit.prompt.md | OUT | .prompt.md — agent-executable, not edited |
| setup/setup-guide.md | IN | Verified clean (parent builder, AC3 PASS) |
| setup/sharing-guide.md | IN | Verified clean (parent builder, AC3 PASS) |
| .owlbear/doc-index.md | IN | Regenerated by parent builder; confirmed no `serve/orchestrator` reference (AC4 PASS) |
| share/diagrams/project-overview.excalidraw | IN | Footer updated → commit 76d291fd |

### Files Updated
- share/diagrams/project-overview.excalidraw (footer: 800c51db → 91a14158)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files matching `1298-*` found)
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. `serve/orchestrator` zero hits in scoped files | Auditor grep: exit=1 (no matches). Test `test_dead_code_sweep_1296.py::test_no_serve_orchestrator_repo_wide` passes | PASS |
| 2. `Copilot CLI` zero hits outside exclusions | Reviewer searches confirmed; test `test_no_copilot_cli_in_md_files_repo_wide` passes | PASS |
| 3. `owlbear-project.json` zero hits | Reviewer grep confirmed; task-scoped tests pass | PASS |
| 4. `.owlbear/doc-index.md` clean | Auditor grep: zero `serve/orchestrator` hits (exit=1). Test `test_doc_index_no_serve_orchestrator` passes | PASS |
| 5. `ruff check` passes | No Python files touched; quality-runner lint clean for scope | PASS |
| 6. Live orchestrator agent intact | Auditor confirmed `share/agents/orchestrator.agent.md` exists | PASS |

### Test Results
- pytest (task-scoped): 17 passed, 0 failed
- pytest (full suite): 3714 passed, 165 failed, 4 skipped — all failures in `test_engine_accessor_migration.py` / `test_engine_coverage_1068.py`, pre-existing and unrelated
- ruff: 1 pre-existing violation in `copilot_auth.py`, not in scope

### Architect Quality: 4/5
Specific, grep-verifiable AC. Minor gap: parent #1296 Architecture Review refined AC3 exclusion list was not back-propagated to child task body, creating avoidable reviewer overhead.

### Deduction Breakdown
- 6/6 AC lines with specific evidence: no deduction
- Lint violations in scope: none → no deduction
- AC quality 4/5: no deduction (threshold ≤3)
- Reviewer evidence section: present, detailed, PASS → no deduction
- Full-suite failures outside task scope: no deduction

### Confidence: .98
### Action: archive