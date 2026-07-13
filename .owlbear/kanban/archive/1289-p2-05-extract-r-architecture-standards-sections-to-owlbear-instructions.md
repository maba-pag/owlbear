---
id: 1289
title: 'P2-05: Extract r-architecture-standards sections to .owlbear/instructions/'
status: archived
priority: medium
created: 2026-05-02T16:01:17.102347+00:00
updated: 2026-05-03T19:08:23.365506+00:00
tags:
- phase-2
- scope:docs
- shared-layer
- docs
parent: 1280
depends_on:
- 1285
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1280 and `.owlbear/briefs/draft-neutral-shared/brief.md`

## Acceptance Criteria

- [ ] New file .owlbear/instructions/architecture.instructions.md created with applyTo: "serve/**"
- [ ] Contains extracted v2 overview, namespace table, domain taxonomy, package dependency rules from r-architecture-standards
- [ ] r-architecture-standards/SKILL.md retains only generic MCP server conventions, module-quality rules, error handling patterns
- [ ] No `serve/` paths remain in the shared r-architecture-standards skill (MCP names excluded)
- [ ] Tests from #1285 pass for r-architecture-standards assertions

## Scope

- IN: r-architecture-standards/SKILL.md, .owlbear/instructions/architecture.instructions.md (new)
- OUT: Other skill genericizations (#1286–#1288), doc-standards chain (#1290)
[[2026-05-03]]
## Research

**Key findings:** The shared skill has already been path-neutralized (serve/ → workspace/, legacy headers renamed) — both test assertions pass. Remaining work is the actual extraction: move Architecture Overview, Dependency Rules, and Domain Scope Map to `.owlbear/instructions/architecture.instructions.md` (applyTo: "serve/**") with concrete serve/ paths restored. Retain intro + Module Quality Vocabulary + MCP Server Conventions + Configuration in the shared skill.

**Tier:** T1 — Autonomous (docs restructuring, no new capability).
**Doc:** `.owlbear/research/extract-arch-standards-1289.md`
**Follow-ups:** None — task itself advances to backlog for implementation.
[[2026-05-03]]

## Architecture Review

### Refined AC

Original AC used legacy terminology. Refined to match current section names in dev:

- [ ] New file `.owlbear/instructions/architecture.instructions.md` created with frontmatter `applyTo: "serve/**"` (td:1)
- [ ] Contains sections extracted from `share/skills/r-architecture-standards/SKILL.md`: `## Architecture Overview` (with `workspace/` paths restored to `serve/`), `## Dependency Rules`, `## Domain Scope Map` (with `workspace/` paths restored to `serve/`) (td:1)
- [ ] `share/skills/r-architecture-standards/SKILL.md` retains ONLY: intro paragraph, `## Module Quality Vocabulary` (+ subsections), `## MCP Server Conventions` (+ all subsections), `## Configuration` (td:1)
- [ ] No `serve/` paths remain in the shared `r-architecture-standards/SKILL.md` after extraction (MCP server names like `mcp-kanban` excluded) (td:0 — covered by existing `test_r_arch_standards_no_serve_path_refs`)
- [ ] Existing tests `test_r_arch_standards_no_serve_path_refs` and `test_r_arch_standards_no_legacy_section_headers` still pass (td:0 — regression gate only)

Test-writer: td:1 lines require new smoke tests verifying: (a) new file exists with correct frontmatter, (b) new file contains `serve/` paths in Architecture Overview and Domain Scope Map, (c) shared skill no longer contains `## Architecture Overview`, `## Dependency Rules`, or `## Domain Scope Map` sections.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One extraction — 3 sections out, 1 new file in |
| Interface clarity | PASS | After AC refinement — exact section names, exact retention list |
| Dependency correctness | PASS | #1285 completed (tests exist + code neutralized) |
| Module layering | N/A | Docs/config only |
| TDD compliance | PASS | #1285 tests exist for regression; td:1 lines for new verification |
| KISS/YAGNI | PASS | Minimal mechanical split per brief D7 |
| Premise challenge | PASS | Brief decision D7 locked this target; discovery configured |
| Pattern consistency | PASS | Follows .owlbear/instructions/ convention (settings.json line 39) |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | agent-config domain |

### Challenger Results

Confidence: 0.29. Raised: (1) AC drift from current section names, (2) missing td annotations, (3) non-discriminating tests, (4) behavioral change understatement, (5) artifact-type justification gap.

**Override:** All concerns resolved by AC rewrite above. Points 1-3 fixed by refined AC with exact names + td annotations + explicit test-writer guidance for discriminating checks. Point 4: instruction-loading change is the stated goal (brief D7). Point 5: artifact type locked at brief level — not architect's re-decision.

### Verdict

APPROVE — AC refined, architecture sound, pass-through tag `docs` added.

[[2026-05-03]]
Architecture review complete. AC refined to use exact current section names (Architecture Overview, Dependency Rules, Domain Scope Map). Test-depth annotated (3x td:1, 2x td:0). Pass-through tag `docs` added. Challenger override justified — all concerns were AC clarity issues resolved by rewrite. Moved to todo.
[[2026-05-03]]
## Test-Writer Notes

- **Test file:** `tests/test_arch_standards_extraction_1289.py`
- **Classes:** `TestFromAC_ArchInstructionsFile`, `TestFromAC_ArchSkillRetention`
- **Total:** 10 tests, all FAIL ✓
- **Ruff:** clean

### Test categories

| Category | Count | Tests |
|----------|-------|-------|
| Existence / frontmatter (AC1) | 2 | file_exists, apply_to_serve |
| Section content (AC2) | 5 | arch_overview_section, dep_rules_section, domain_scope_section, overview_serve_paths, domain_scope_serve_paths |
| Skill retention (AC3) | 3 | no_arch_overview, no_dep_rules, no_domain_scope |

### AC coverage

| AC line | td | Tests |
|---------|----|-------|
| New file `.owlbear/instructions/architecture.instructions.md` with `applyTo: "serve/**"` | 1 | test_architecture_instructions_file_exists, test_architecture_instructions_has_apply_to_serve |
| Contains Architecture Overview, Dependency Rules, Domain Scope Map; serve/ paths restored | 1 | 5 content tests |
| SKILL.md retains only intro+Module Quality Vocabulary+MCP Server Conventions+Configuration | 1 | 3 section-absence tests |
| No serve/ paths in shared skill | 0 | covered by existing test_r_arch_standards_no_serve_path_refs |
| Existing 1285 tests pass | 0 | regression gate only |
[[2026-05-03]]
## Builder Notes
- Implementation: extracted `## Architecture Overview`, `## Dependency Rules`, and `## Domain Scope Map` from `share/skills/r-architecture-standards/SKILL.md` into new `.owlbear/instructions/architecture.instructions.md` with frontmatter `applyTo: "serve/**"`.
- Files changed: `.owlbear/instructions/architecture.instructions.md`, `share/skills/r-architecture-standards/SKILL.md`.
- Tests: 19 passed, 0 failed (`tests/test_arch_standards_extraction_1289.py` + `tests/test_path_neutrality_1285.py`).
- Coverage: N/A for doc-only change in scoped verification run.
- Ruff: clean.
- Commit: `6836927d` — `docs: extract architecture sections to local instructions (#1289, builder)`.

## Post-task Reflection
- AC wording used legacy labels initially; anchoring to refined Architecture Review section names avoided mismatched extraction.
- Creating `.owlbear/instructions/` was required because the directory did not exist in this workspace snapshot.
- Scoped quality-runner verification remained discriminating and fast for this docs-only extraction task.
- Existing workspace noise required explicit file scoping at commit time to preserve atomicity.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner pytest: 19 passed, 0 failed
- Command: `uv run pytest tests/test_arch_standards_extraction_1289.py tests/test_path_neutrality_1285.py -q --tb=short`

### Lint
- quality-runner ruff: clean
- Command: `uv run ruff check tests/test_arch_standards_extraction_1289.py tests/test_path_neutrality_1285.py`

### Coverage
- N/A for gate purposes. Builder changed only `.owlbear/instructions/architecture.instructions.md` and `share/skills/r-architecture-standards/SKILL.md`; no Python or TypeScript source module changed.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| New file `.owlbear/instructions/architecture.instructions.md` created with frontmatter `applyTo: "serve/**"` | `test_architecture_instructions_file_exists` ([tests/test_arch_standards_extraction_1289.py:35](tests/test_arch_standards_extraction_1289.py#L35)), `test_architecture_instructions_has_apply_to_serve` ([tests/test_arch_standards_extraction_1289.py:42](tests/test_arch_standards_extraction_1289.py#L42)) | Yes. Missing file or wrong frontmatter fails directly. | COVERED |
| Extracted `## Architecture Overview`, `## Dependency Rules`, `## Domain Scope Map`; `serve/` paths restored | `test_architecture_instructions_has_architecture_overview_section` ([tests/test_arch_standards_extraction_1289.py:55](tests/test_arch_standards_extraction_1289.py#L55)), `test_architecture_instructions_has_dependency_rules_section` ([tests/test_arch_standards_extraction_1289.py:65](tests/test_arch_standards_extraction_1289.py#L65)), `test_architecture_instructions_has_domain_scope_map_section` ([tests/test_arch_standards_extraction_1289.py:75](tests/test_arch_standards_extraction_1289.py#L75)), `test_architecture_instructions_overview_has_serve_paths` ([tests/test_arch_standards_extraction_1289.py:85](tests/test_arch_standards_extraction_1289.py#L85)), `test_architecture_instructions_domain_scope_has_serve_paths` ([tests/test_arch_standards_extraction_1289.py:100](tests/test_arch_standards_extraction_1289.py#L100)) | Yes for the refined td:1 smoke contract: missing section headings or un-restored `serve/` paths fail directly. | COVERED |
| Shared `r-architecture-standards/SKILL.md` retains only intro + `## Module Quality Vocabulary` + `## MCP Server Conventions` + `## Configuration` | `test_r_arch_standards_no_architecture_overview_section` ([tests/test_arch_standards_extraction_1289.py:121](tests/test_arch_standards_extraction_1289.py#L121)), `test_r_arch_standards_no_dependency_rules_section` ([tests/test_arch_standards_extraction_1289.py:132](tests/test_arch_standards_extraction_1289.py#L132)), `test_r_arch_standards_no_domain_scope_map_section` ([tests/test_arch_standards_extraction_1289.py:143](tests/test_arch_standards_extraction_1289.py#L143)) | Yes. Any retained extracted section fails directly; current heading scan also shows only `## Module Quality Vocabulary`, `## MCP Server Conventions`, and `## Configuration` remain in the skill. | COVERED |
| No `serve/` paths remain in shared skill | `test_r_arch_standards_no_serve_path_refs` ([tests/test_path_neutrality_1285.py:92](tests/test_path_neutrality_1285.py#L92)) | Yes. Any non-excluded `serve/` path in the shared skill fails directly. | COVERED |
| Existing `test_r_arch_standards_no_serve_path_refs` and `test_r_arch_standards_no_legacy_section_headers` still pass | `test_r_arch_standards_no_serve_path_refs` ([tests/test_path_neutrality_1285.py:92](tests/test_path_neutrality_1285.py#L92)), `test_r_arch_standards_no_legacy_section_headers` ([tests/test_path_neutrality_1285.py:127](tests/test_path_neutrality_1285.py#L127)) | Yes. Both were executed in the scoped green run. | COVERED |

#### Security Review
- No issues. The builder diff is markdown-only and adds no executable code paths, dependencies, secrets, or input-handling surface.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_arch_standards_extraction_1289.py` | None. `git show --name-only 6836927d` listed only `.owlbear/instructions/architecture.instructions.md` and `share/skills/r-architecture-standards/SKILL.md`. | PRESERVED |
| `tests/test_path_neutrality_1285.py` | None. Not present in builder diff. | PRESERVED |

#### Test Quality
- Assertion specificity: ADEQUATE. Task tests use exact file existence, exact section-header substrings, exact path substrings, and exact section-absence assertions.
- Negative/error-path coverage: ADEQUATE for a docs-extraction task. The meaningful failure modes are missing file, missing headings, missing restored paths, or retained extracted sections, and each is asserted directly.
- Manual mutation reasoning: ADEQUATE. Removing any extracted section heading, restoring `workspace/` instead of `serve/`, or leaving extracted headings in the shared skill would fail the scoped suite.
- Test independence: STRONG. No shared mutable state; tests read repo files only.
- Test names: STRONG. Names are explicit and AC-mapped.

#### Data Safety
- No issues. No persisted data, concurrency surface, or resource-bound behavior changed.

#### Implementation-Aware Test Gap Analysis
- No significant gap for the refined AC. Direct file inspection confirms the extracted bodies are present in the new instructions file at `.owlbear/instructions/architecture.instructions.md:8`, `:24`, and `:34`, and the shared skill now exposes only the retained top-level sections at `share/skills/r-architecture-standards/SKILL.md:11`, `:38`, and `:117`.

#### Necessity Check
- N/A. This task is a docs/config extraction, not a new dependency or integration.

#### Builder Process Quality
- CLEAN. One `## Builder Notes` section in the task body ([.owlbear/kanban/tasks/1289-p2-05-extract-r-architecture-standards-sections-to-owlbear-instructions.md:114](.owlbear/kanban/tasks/1289-p2-05-extract-r-architecture-standards-sections-to-owlbear-instructions.md#L114)); no prior `## Review Evidence` sections.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| New file `.owlbear/instructions/architecture.instructions.md` created with frontmatter `applyTo: "serve/**"` | `.owlbear/instructions/architecture.instructions.md:3` declares `applyTo: "serve/**"`; file exists and is exercised by the scoped green run. | `test_architecture_instructions_file_exists`, `test_architecture_instructions_has_apply_to_serve` | PASS |
| Contains extracted `## Architecture Overview`, `## Dependency Rules`, `## Domain Scope Map` with `serve/` paths restored | New file contains the three extracted sections at `.owlbear/instructions/architecture.instructions.md:6`, `:22`, `:32`; extracted body text appears at `:8`, `:24`, `:34`; restored `serve/` paths appear at `:13`, `:17`, `:38`, `:39`; no `workspace/` residue found. | Five task tests in `tests/test_arch_standards_extraction_1289.py` | PASS |
| Shared `r-architecture-standards/SKILL.md` retains only intro + `## Module Quality Vocabulary` + `## MCP Server Conventions` + `## Configuration` | Current top-level heading scan shows only `## Module Quality Vocabulary` (`:11`), `## MCP Server Conventions` (`:38`), and `## Configuration` (`:117`); intro paragraph remains at `:9`. Extracted headings are absent. | Three skill-retention tests in `tests/test_arch_standards_extraction_1289.py` | PASS |
| No `serve/` paths remain in shared `r-architecture-standards/SKILL.md` | Direct search found no `serve/` matches in `share/skills/r-architecture-standards/SKILL.md`; scoped regression test passed. | `test_r_arch_standards_no_serve_path_refs` | PASS |
| Existing `test_r_arch_standards_no_serve_path_refs` and `test_r_arch_standards_no_legacy_section_headers` still pass | quality-runner executed both inherited #1285 regression tests in the 19/19 green run. | `test_r_arch_standards_no_serve_path_refs`, `test_r_arch_standards_no_legacy_section_headers` | PASS |

### Deductions
- None.

### Verdict
- PASS — confidence 0.97. Refined td:1 AC is fully satisfied; task-local and inherited regression tests are green; builder did not alter TestFromAC files; no security or data-safety concerns.
- Action: advance to docs.

## Post-task Reflection
- Builder-owned diff was sufficiently narrow to clear TestFromAC immutability quickly.
- For td:1 docs extraction, heading scans plus smoke tests were enough; no deeper runtime surface existed.
- Coverage is not a meaningful gate when the diff is limited to markdown artifacts.
[[2026-05-03]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope docs (README.md, setup guides, share/README.md) reference `r-architecture-standards` or `architecture.instructions`; confirmed via grep. |
| 2 | Module docstrings | No | N/A | Builder diff is markdown-only — no Python modules changed. |
| 3 | External attribution | No | N/A | Pure internal extraction; no external sources cited. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/extract-arch-standards-1289.md` exists and is linked from task body; follow-ups noted as "None". |
| 5 | Diagram maintenance (describes match) | Yes | N/A | `share/diagrams/project-overview.excalidraw` describes `share/**` and `.owlbear/**` — both changed files match. Footer already reads `Last verified: 2026-05-03 (b94454c5)` (current HEAD). No update needed. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; sections moved between two OUT-scope agent-executable files. No IN-scope docs reference the extracted sections. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/instructions/architecture.instructions.md` | OUT (agent-executable `.instructions.md`) | N/A |
| `share/skills/r-architecture-standards/SKILL.md` | OUT (`share/skills/*/SKILL.md`) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1289-*` files found)
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| New file `.owlbear/instructions/architecture.instructions.md` with `applyTo: "serve/**"` | File exists; frontmatter L3 `applyTo: "serve/**"` | PASS |
| Contains Architecture Overview, Dependency Rules, Domain Scope Map; serve/ paths restored | Sections at L6, L22, L32; serve/ paths at L13, L17, L38, L39 | PASS |
| Shared skill retains only intro + Module Quality Vocabulary + MCP Server Conventions + Configuration | `grep '^## '` → 3 headings exact match | PASS |
| No serve/ paths in shared skill | `grep -c 'serve/'` → 0 | PASS |
| Existing #1285 tests pass | Full-suite run; 19/19 scoped green per reviewer | PASS |

### Test Results
- pytest: 3841 passed, 128 failed (none in task scope — pre-existing: accessor migration, storage timestamps, cockpit events)
- vitest: 937 passed, 13 failed (none in task scope — shell polling tests)
- ruff: 1 violation in copilot_auth.py (unrelated)

### Architect Quality: 4/5
Initial AC used legacy section names; architecture review refined with exact headings and td annotations. Minor upstream gap resolved before test-writer.

### Deduction Breakdown
- None applied. All AC lines have specific evidence; reviewer evidence detailed with PASS; no task-scope failures; no lint violations in scope.

### Confidence: 0.98
### Action: archive

### Commit Integrity
- Builder commit `6836927d`: exactly 2 files (`.owlbear/instructions/architecture.instructions.md`, `share/skills/r-architecture-standards/SKILL.md`) — matches AC scope.