---
id: 1286
title: 'P2-02: Extract file-placement and layout sections to .github/copilot-instructions.md'
status: archived
priority: medium
created: 2026-05-02T16:01:17.059804+00:00
updated: 2026-05-03T19:09:32.901596+00:00
tags:
- phase-2
- scope:docs
- shared-layer
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

- [ ] r-project-standards §2 File Placement table extracted; skill retains commit format, attribution, priority, tags
- [ ] h-python-conventions Project Layout section extracted; skill retains coding conventions
- [ ] Extracted content (file placement table + project layout paths) added to .github/copilot-instructions.md
- [ ] No `serve/` paths remain in r-project-standards or h-python-conventions (MCP names excluded)
- [ ] Tests from #1285 pass for these two skills

## Scope

- IN: r-project-standards/SKILL.md, h-python-conventions/SKILL.md, .github/copilot-instructions.md
- OUT: Other P2 skills (#1287–#1291)
[[2026-05-03]]
## Research

**Key findings:** Straightforward content extraction per brief specification. Both target skills already have zero `serve/` references — they use `workspace/*/src/` generic placeholders that are equally confusing for consumers. Extraction removes the project-specific layout info entirely from shared skills and places it (with concrete `serve/` paths) in `.github/copilot-instructions.md`.

**Implementation plan:**
1. Remove §2 File Placement from r-project-standards (renumber remaining sections)
2. Remove `## Project Layout` from h-python-conventions
3. Add §6 File Placement + §7 Project Layout to copilot-instructions.md with concrete OwlBear paths
4. Update r-project-standards frontmatter description

**Cross-reference risk:** r-doc-standards PLC-2 references `r-project-standards § File Placement` — handled by sibling r-doc-standards split task, not this one.

**Tier:** T1 (Autonomous) — content move per approved brief.
**Confidence:** 0.90
**Doc:** `.owlbear/research/file-placement-extraction-1286.md`
**Follow-ups:** None needed (sibling tasks #1287–#1291 cover related work)
[[2026-05-03]]

## Architecture Review

**Verdict:** APPROVE → todo

**AC Assessment:**

| AC line | Depth | Assessment |
|---------|-------|------------|
| AC1: §2 extracted; skill retains commit/attribution/priority/tags | td:1 | Verifiable — assert heading absent + remaining sections intact |
| AC2: Project Layout extracted; skill retains coding conventions | td:1 | Verifiable — assert heading absent + other sections intact |
| AC3: Content added to copilot-instructions.md | td:1 | Verifiable — assert §6/§7 content present |
| AC4: No serve/ paths in the two skills | td:0 | Already satisfied (safety net); covered by #1285 suite |
| AC5: Tests from #1285 pass | td:0 | Run existing suite — no new tests needed |

**Architecture notes:**
- Straightforward content extraction per approved brief
- copilot-instructions.md §2 "Directory Structure" describes *what dirs contain*; new §6 "File Placement" describes *where to put new files* (contributor workflow) — non-overlapping authority
- Section renumbering in r-project-standards (§3→§2, §4→§3, §5→§4) has no live inbound references after extraction
- Cross-ref in r-doc-standards PLC-2 → handled by sibling #1290 (tracked, not blocked)

**Dependency:** #1285 done ✓

**Challenger:** confidence 0.68 (reconsider) — overridden. Concerns are pipeline-by-design (test-writer adds AC1-3 verification), tracked coordination (#1290), or evaluated non-issues (authority overlap is purpose-distinct).

**Builder guidance:** Ensure new §6/§7 in copilot-instructions.md use concrete `serve/` paths (not `workspace/` placeholders). The existing Directory Structure table stays unchanged — complementary, not duplicative.
[[2026-05-03]]
Architecture review complete. APPROVE → todo. Straightforward content extraction per approved brief. AC is verifiable (td:1 for extraction assertions, td:0 for existing safety nets). Challenger override justified — concerns are pipeline-by-design or tracked by sibling tasks.
[[2026-05-03]]
## Test-Writer Notes
- Test file: tests/test_skill_extraction_1286.py
- Classes: TestFromAC_FilePlacementExtraction
- Tests per category: happy 0, edge 0, error 0, boundary 0 (td:1 — smoke tests per AC annotation)
- Total: 4 tests, all FAIL
- ruff: clean

| AC line | Test(s) | Status |
|---------|---------|--------|
| AC1: §2 File Placement extracted; skill retains commit/attribution/priority/tags | test_r_project_standards_file_placement_extracted | FAIL ✓ |
| AC2: Project Layout extracted; skill retains coding conventions | test_h_python_conventions_project_layout_extracted | FAIL ✓ |
| AC3: Content added to copilot-instructions.md | test_copilot_instructions_has_file_placement_section, test_copilot_instructions_has_project_layout_section | FAIL ✓ |
| AC4: No serve/ paths in the two skills | (td:0) — covered by #1285 suite | skipped |
| AC5: Tests from #1285 pass | (td:0) — run existing suite | skipped |

Failure modes:
- tests 1–2: AssertionError — heading still present in skill file
- tests 3–4: AssertionError — section absent from copilot-instructions.md
[[2026-05-03]]
## Builder Notes
- Files changed: `.github/copilot-instructions.md`, `share/skills/r-project-standards/SKILL.md`, `share/skills/h-python-conventions/SKILL.md`
- Implementation: extracted `## 2. File Placement` from r-project-standards and `## Project Layout` from h-python-conventions; added new `## 6. File Placement` and `## 7. Project Layout` sections in copilot instructions with concrete `serve/` paths.
- RED verification: `tests/test_skill_extraction_1286.py` initially failed all 4 TestFromAC tests exactly as expected.
- GREEN verification: quality-runner scoped run passed with 13 tests (`tests/test_skill_extraction_1286.py` + `tests/test_path_neutrality_1285.py`), 0 failed.
- Lint: clean (ruff clean in quality-runner output).
- Coverage: N/A for docs-only scope; quality-runner reported no coverage data captured due plugin-selective environment.
- Evidence summary: AC1 and AC2 validated by removal of target headings while keeping required sections; AC3 validated by added File Placement/Project Layout sections using concrete `serve/` paths; AC5 validated by passing #1285 neutrality test file.
- Commit: `a80bdeae` with message `docs: extract file placement and layout guidance (#1286, builder)`.

### Post-task Reflection
- Problems faced: coverage instrumentation unavailable in quality-runner environment for this scoped run.
- Workaround: relied on scoped pass/fail + lint evidence on task and dependency test files.
- Pattern: for docs extraction tasks, minimal heading/table moves are sufficient and safer than broad rewrites.
- Quality gap: none found in scoped checks.

[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped run: 13 passed, 0 failed, 0 skipped
- Scope included tests/test_skill_extraction_1286.py and tests/test_path_neutrality_1285.py

### Lint
- ruff: clean on the reviewed Python test files

### Coverage
- Not a gating signal for this markdown-only task. quality-runner emitted test-file coverage only, which does not change the review outcome.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: r-project-standards section extracted; commit/attribution/priority/tags retained | test_r_project_standards_file_placement_extracted | Yes for the extraction contract and retained section presence expected at td:1 | COVERED |
| AC2: h-python-conventions Project Layout extracted; coding conventions retained | test_h_python_conventions_project_layout_extracted | Yes for the extraction contract and retained section presence expected at td:1 | COVERED |
| AC3: extracted content added to copilot-instructions.md | test_copilot_instructions_has_file_placement_section; test_copilot_instructions_has_project_layout_section | Yes; missing sections or missing concrete serve paths would fail | COVERED |
| AC4: no serve paths remain in the two skills | test_no_serve_path_refs_in_skill_files from tests/test_path_neutrality_1285.py | Yes; any remaining serve path in either skill would fail the dependency suite | COVERED |
| AC5: tests from #1285 pass for these two skills | quality-runner scoped run including tests/test_path_neutrality_1285.py | Yes; the scoped dependency test file passed in this review run | COVERED |

#### Security Review
- No issues. The builder diff is limited to markdown content moves in three documentation files and introduces no executable surface, secrets, or input handling.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_r_project_standards_file_placement_extracted | No builder change; builder commit a80bdeae touched only the three markdown files | PRESERVED |
| test_h_python_conventions_project_layout_extracted | No builder change; task test file history traces to test-writer commit 82eb77dd | PRESERVED |
| test_copilot_instructions_has_file_placement_section | No builder change; post-builder diff on task files is empty | PRESERVED |
| test_copilot_instructions_has_project_layout_section | No builder change; post-builder diff on task files is empty | PRESERVED |

#### Test Quality
- Assertion specificity: ADEQUATE. The task-local tests are discriminating for a td:1 content-move task: removed headings, retained sections, and required new sections all have direct assertions.
- Negative and edge coverage: ADEQUATE for markdown-only scope; there are no runtime branches, state transitions, or error paths to exercise.
- Manual mutation reasoning: ADEQUATE. Reintroducing either removed heading or deleting either new section would fail immediately. Retained-section content is not asserted row-by-row, so confidence is reduced slightly rather than failing the task.
- Independence: STRONG. Each test reads files independently with no shared mutable state.
- Naming: STRONG. Test names map directly to the AC.

#### Data Safety
- No issues. No persistence, concurrency, or resource-boundary behavior changed.

#### Implementation-Aware Test Gaps
- No significant gaps for this scope. The builder patch is a surgical extraction: git show for a80bdeae removes the File Placement block from share/skills/r-project-standards/SKILL.md, removes Project Layout from share/skills/h-python-conventions/SKILL.md, and adds the moved material to .github/copilot-instructions.md.

#### Necessity Check
- Not applicable. No new dependencies, integrations, or tooling were added.

#### Builder Process Quality
- CLEAN. One builder cycle, no repeated review sections, no loop pattern.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | share/skills/r-project-standards/SKILL.md retains Commit Discipline, Attribution, Priority Scheme, and Tag Taxonomy at lines 11, 33, 45, and 55; removed File Placement block confirmed by builder diff and passing task-local test at tests/test_skill_extraction_1286.py line 32 | test_r_project_standards_file_placement_extracted | PASS |
| AC2 | share/skills/h-python-conventions/SKILL.md retains Package Management, Code Style, and Testing at lines 9, 14, and 22; removed Project Layout block confirmed by builder diff and passing task-local test at tests/test_skill_extraction_1286.py line 64 | test_h_python_conventions_project_layout_extracted | PASS |
| AC3 | .github/copilot-instructions.md adds File Placement at line 74 and Project Layout at line 95, with concrete serve paths at lines 84 and 97 through 99; passing task-local tests at tests/test_skill_extraction_1286.py lines 91 and 113 | test_copilot_instructions_has_file_placement_section; test_copilot_instructions_has_project_layout_section | PASS |
| AC4 | Search of the two shared skills found no remaining serve path matches; dependency suite tests/test_path_neutrality_1285.py passed in the scoped review run | test_no_serve_path_refs_in_skill_files | PASS |
| AC5 | quality-runner scoped run passed all 13 tests, including the dependency file tests/test_path_neutrality_1285.py | quality-runner scoped run | PASS |

### Deductions
- 0.04: td:1 smoke tests verify section movement and required presence, but they do not pin every retained row or paragraph verbatim.

### Verdict
- PASS with confidence 0.94

### Action
- Advance to docs
[[2026-05-03]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are OUT-scope (agent-executable SKILL.md and copilot-instructions.md). No IN-scope prose docs reference SKILL.md internals. |
| 2 | Module docstrings | No | N/A | No Python modules changed. |
| 3 | External attribution | No | N/A | All sources in research doc are internal; no external patterns used. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/file-placement-extraction-1286.md` exists, linked from task body, follow-ups noted as none needed (sibling tasks cover related work). |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/project-overview.excalidraw` has `describes: share/**` which matches `share/skills/r-project-standards/SKILL.md` and `share/skills/h-python-conventions/SKILL.md`. Footer updated to `Last verified: 2026-05-03 (b94454c5)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No IN-scope docs reference deleted features or files. No orphaned docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.github/copilot-instructions.md` | OUT | N/A (agent-executable) |
| `share/skills/r-project-standards/SKILL.md` | OUT | N/A (agent-executable) |
| `share/skills/h-python-conventions/SKILL.md` | OUT | N/A (agent-executable) |
| `tests/test_skill_extraction_1286.py` | OUT | N/A (test file) |
| `share/diagrams/project-overview.excalidraw` | IN | Footer updated (triggered by describes: share/**) |

### Files Updated
- `share/diagrams/project-overview.excalidraw` — footer: `Last verified: 2026-05-03 (b94454c5)` (commit 6af3f3db)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files found for task #1286)
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: §2 File Placement extracted; skill retains commit/attribution/priority/tags | r-project-standards/SKILL.md has no File Placement heading; retains §1 Commit Discipline, §2 Attribution, §3 Priority Scheme, §4 Tag Taxonomy. Builder commit a80bdeae. | PASS |
| AC2: Project Layout extracted; skill retains coding conventions | h-python-conventions/SKILL.md has no Project Layout heading; retains Package Management, Code Style, Testing, Known Gotchas, Patterns. Builder commit a80bdeae. | PASS |
| AC3: Content added to copilot-instructions.md | §6 File Placement at line 74, §7 Project Layout at line 95, concrete serve/ paths confirmed. Builder commit a80bdeae. | PASS |
| AC4: No serve/ paths in the two skills | grep_search of both skill files returned zero matches for "serve/" | PASS |
| AC5: Tests from #1285 pass | quality-runner full run: test_path_neutrality_1285.py and test_skill_extraction_1286.py included in 4778 passed | PASS |

### Test Results
- pytest: 3841 passed, 128 failed (all failures unrelated — mcp-kanban validation, config migration, frontend integration)
- vitest: 937 passed, 13 failed (all failures unrelated — Shell/traffic-light component tests)
- ruff: 1 violation in copilot_auth.py (T201, unrelated)
- eslint: 1 error + 3 warnings (all unrelated)

### Architect Quality: 4/5
AC lines were specific and verifiable. AC4 was pre-satisfied (safety net), not a true work item — minor redundancy.

### Deduction Breakdown
- 0.02: td:1 tests verify heading presence/absence but don't pin every paragraph verbatim

### Confidence: 0.98
### Action: archive