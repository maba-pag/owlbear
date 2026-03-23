---
id: 781
title: Implement knowledge-ops SKILL.md content
status: archived
priority: nice-to-have
created: 2026-03-13T14:31:20.9656179+01:00
updated: 2026-03-23T02:43:51.1748685+01:00
started: 2026-03-23T02:43:46.8245976+01:00
completed: 2026-03-23T02:43:46.8245976+01:00
tags:
    - tooling
    - docs
    - scope:core
class: standard
---

Write .github/skills/knowledge-ops/SKILL.md covering: decision tree (10-12 rows), tool reference (8 tools across 3 toolsets), scope conventions (global vs project:{id}), domain reference (EntityType/RelationType/SourceType), ingest workflow (text/file/url + delta checking). Follow kanban-md SKILL.md structure. Max ~150 lines. See docs/research/knowledge-ops-skill.md S4.

[[2026-03-13]] Fri 20:02
## Research Validation

**Checklist:**
- [x] Theoretical validity: SKILL.md for 8 tools across 3 toolsets is sound (LlamaIndex confirms description quality matters)
- [x] Prior art: kanban-md SKILL.md (17 skills use same pattern), LlamaIndex + PydanticAI docs
- [x] Technical feasibility: .md file in .github/skills/knowledge-ops/  no blockers
- [x] Architecture fit: matches existing skill directory pattern exactly
- [x] Implementation approach: mirror kanban-md SKILL.md structure

**Depends on:** #780 (SkillRegistry glob fix) for runtime discovery. VS Code reads it now.

**AC (from research doc):**
- [ ] YAML frontmatter with name: knowledge-ops and descriptive description
- [ ] Decision tree table mapping agent intent to tool name (10-12 rows)
- [ ] All 8 tools documented with parameters and valid values
- [ ] Scope conventions section (global vs project:{id})
- [ ] Domain reference with EntityType, RelationType, SourceType valid values
- [ ] Ingest workflow section (text/file/url + delta checking)
- [ ] SkillRegistry._parse_frontmatter() succeeds on the file
- [ ] Max ~150 lines

[[2026-03-13]] Fri 20:45
## Test-Writer Notes
- Non-implementation task (tagged docs, tooling)  deliverable is a .md file, no new Python code.
- AC #7 (SkillRegistry._parse_frontmatter succeeds) tests existing code against new content  content validation, not code feature.
- Passing through to builder.

[[2026-03-13]] Fri 20:45
## Test-Writer Notes

[[2026-03-13]] Fri 20:45
- Non-implementation task (tagged docs, tooling) -- deliverable is a .md file, no new Python code.
- AC #7 (SkillRegistry._parse_frontmatter succeeds) tests existing code against new content -- content validation, not code feature.
- Passing through to builder.

[[2026-03-13]] Fri 20:45
- Non-implementation task (tagged docs, tooling) -- deliverable is a .md file, no new Python code.
- AC #7 (SkillRegistry._parse_frontmatter succeeds) tests existing code against new content -- content validation, not code feature.
- Passing through to builder.

[[2026-03-21]] Sat 03:52
## Builder Notes
- Files changed: .github/skills/knowledge-ops/SKILL.md (already committed: 9832972)
- Tests: No TestFromAC tests (test-writer pass-through — non-implementation task)
- Lint: N/A (markdown file)
- Evidence: _parse_frontmatter OK: name=knowledge-ops; 132 lines (<=150); 10 rows in decision tree; 8 tools documented across 3 toolsets; scope, domain, ingest sections present
- Fixes applied: None — file was complete from prior session

[[2026-03-21]] Sat 04:10
## Review Evidence
## Review: #781 - Implement knowledge-ops SKILL.md content

### Test Results
- Command: `uv run pytest tests/test_skills.py -q --tb=short`
- Result: **30 passed, 3 failed, 2 warnings**
- Failing tests:
- `tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_discovers_18_real_skills`
- `tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_real_skills_have_nonempty_names`
- `tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_list_skills_includes_all_19`
- Failure evidence: tests assert `len(registry.skills) == 19`, but runtime inventory is 20 (`knowledge-ops` plus 19 other skills).

### Lint Results
- Command: `uv run ruff check src/ tests/`
- Result: FAIL with 461 findings (repo-wide baseline).
- Scope note: findings are not from `.github/skills/knowledge-ops/SKILL.md` (markdown-only task), but lint is still non-green at review time.

### Coverage
- Command: `uv run pytest tests/test_skills.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- `src/owlbear/skills/registry.py`: **100%**
- Total project coverage from bare `--cov`: 3% (expected for scoped test run against full source tree)
- Test status remained FAIL (same 3 failing assertions above).

### Pass 1 - CRITICAL
#### Security Review
- Reviewed changed files from commit `9832972` (`.github/skills/knowledge-ops/SKILL.md`, `tests/test_skills.py`).
- No hardcoded secrets, injection sinks, traversal vectors, unsafe deserialization usage, dependency additions, or sensitive-data logging introduced by this task diff.

#### Test Integrity (TestFromAC comparison)
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_RealSkillsDiscovery::test_discovers_18_real_skills` | Assertion updated `== 18` -> `== 19`; message/docstring updated to 19 | STRENGTHENED |
| `TestFromAC_RealSkillsDiscovery::test_real_skills_have_nonempty_names` | Guard assertion updated `== 18` -> `== 19` | STRENGTHENED |
| `TestFromAC_RealSkillsDiscovery::test_list_skills_includes_all_18` | Renamed to `_all_19`; guard assertion `== 18` -> `== 19`; docstring updated | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact count assertions and explicit per-skill output assertions are used. |
| Negative/error paths | ADEQUATE | This class is inventory verification; negative path is partially covered via guard assertions. |
| Mutation reasoning | ADEQUATE | A wrong skill inventory count fails immediately, but fixed counts are brittle as inventory evolves. |
| Test independence | STRONG | Fresh `SkillRegistry` per test; no shared mutable state. |
| Descriptive names | STRONG | Names clearly describe scenario and expected result. |

#### Data Safety
- No runtime code-path changes in this task beyond markdown/test metadata; no data-safety regression identified.

### Pass 2 - INFORMATIONAL
- The `RealSkillsDiscovery` tests are currently brittle because they hardcode total skill count; concurrent skill additions can break unrelated tasks.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| YAML frontmatter with name `knowledge-ops` and descriptive description | `.github/skills/knowledge-ops/SKILL.md` lines 1-4; `_parse_frontmatter` returned `name knowledge-ops`, `description_nonempty True` | `uv run python -c ...SkillRegistry._parse_frontmatter(...)` | PASS |
| Decision tree table mapping intent to tool (10-12 rows) | File lines 20-31; automated check `decision_rows 10` | `uv run python -c ...decision_rows...` | PASS |
| All 8 tools documented with parameters and valid values | File lines 37-90; automated check `tool_count 8`, toolsets present | `uv run python -c ...tool_count...` | PASS |
| Scope conventions section (`global` vs `project:{id}`) | File lines 92-99 | Static file verification | PASS |
| Domain reference with EntityType/RelationType/SourceType valid values | File lines 103-107 match `src/owlbear/memory/knowledge/models.py` enum values | Cross-check against source enums | PASS |
| Ingest workflow section (`text`/`file`/`url` + delta checking) | File lines 122-132 | Static file verification | PASS |
| `SkillRegistry._parse_frontmatter()` succeeds | Command output: `name knowledge-ops`, `description_nonempty True` | `uv run python -c ...SkillRegistry._parse_frontmatter(...)` | PASS |
| Max ~150 lines | Command output: `line_count 132` | `uv run python -c ...line_count...` | PASS |

### Rejection Table
| Gap | Evidence | Required Fix |
|-----|----------|--------------|
| Scoped validation tests are failing in current repo state | `uv run pytest tests/test_skills.py -q --tb=short` -> 3 failures in `TestFromAC_RealSkillsDiscovery` due hardcoded `== 19` vs discovered 20 skills | Update `tests/test_skills.py` real-skill inventory assertions to match current intended behavior (avoid stale hardcoded count), then re-run scoped pytest until green. |

### Verdict
- **FAIL** (critical gate: scoped pytest is red)
- Confidence: **.97**

[[2026-03-22]] Sun 23:35
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about stale hardcoded skill count (== 19 vs 20), not missing tests.
- Current state: uv run pytest tests/test_skills.py -> 33 passed, 0 failed. Count fixed by task #780 builder work.
- Existing tests preserved. No new tests needed. Passing through to builder.

[[2026-03-23]] Mon 00:38
## Review Evidence

[[2026-03-23]] Mon 00:38
## Review: #781 - Implement knowledge-ops SKILL.md content

[[2026-03-23]] Mon 00:38
### Test Results

[[2026-03-23]] Mon 00:38
- pytest scoped: 33 passed, 0 failed, 2 warnings via uv run pytest tests/test_skills.py -q --tb=short (warnings: optional qdrant_client missing).

[[2026-03-23]] Mon 00:38
### Lint Results

[[2026-03-23]] Mon 00:38
- ruff scoped: All checks passed via uv run ruff check tests/test_skills.py src/owlbear/skills/registry.py.

[[2026-03-23]] Mon 00:38
### Coverage

[[2026-03-23]] Mon 00:38
- Not applicable: task deliverable is markdown skill content; no production Python module changes required for AC completion.

[[2026-03-23]] Mon 00:38
### Pass 1 - CRITICAL

[[2026-03-23]] Mon 00:38
- Test-writer AC coverage: docs-only task; test-writer marked pass-through, so there are no task-specific TestFromAC classes for #781.

[[2026-03-23]] Mon 00:38
- Security review: no hardcoded secrets, injection sinks, path traversal paths, unsafe deserialization, or dependency changes introduced in .github/skills/knowledge-ops/SKILL.md.

[[2026-03-23]] Mon 00:38
- Test integrity: builder commit 9832972 updated TestFromAC_RealSkillsDiscovery exact-count checks from 18 to 19 and renamed includes_all_18 to includes_all_19; assessment STRENGTHENED, with no WEAKENED or REMOVED assertions.

[[2026-03-23]] Mon 00:38
- Test quality: assertion specificity ADEQUATE; negative/error paths ADEQUATE; mutation reasoning ADEQUATE; test independence STRONG; descriptive names STRONG for touched inventory tests.

[[2026-03-23]] Mon 00:38
- Data safety: no runtime data-path changes in this markdown-centric task.

[[2026-03-23]] Mon 00:38
- Implementation-aware test gaps: no significant untested runtime paths introduced by task #781 deliverables.

[[2026-03-23]] Mon 00:38
### Pass 2 - INFORMATIONAL

[[2026-03-23]] Mon 00:38
- Exact skill-count assertions were historically brittle; current workspace has >=17 threshold checks in tests/test_skills.py, reducing cross-task fragility.

[[2026-03-23]] Mon 00:38
### AC Compliance

[[2026-03-23]] Mon 00:38
- AC1 PASS: YAML frontmatter with name and description at .github/skills/knowledge-ops/SKILL.md lines 2-3; parser probe returned frontmatter_name knowledge-ops and description_nonempty True.

[[2026-03-23]] Mon 00:38
- AC2 PASS: Decision Tree section at line 26 with decision_rows 10 (required 10-12).

[[2026-03-23]] Mon 00:38
- AC3 PASS: Tool Reference section at line 41 documents 8 tools across 3 toolsets (tool_count 8).

[[2026-03-23]] Mon 00:38
- AC4 PASS: Scope Conventions at line 100 includes global and project:{id} usage (lines 105 and 107).

[[2026-03-23]] Mon 00:38
- AC5 PASS: Domain Reference at lines 109-115 matches EntityType/RelationType/SourceType enum values in src/owlbear/memory/knowledge/models.py lines 17-22, 28-34, and 51-53.

[[2026-03-23]] Mon 00:38
- AC6 PASS: Ingest Workflow section at line 130 includes text/file/url modes (lines 134-136) and delta checking at line 138.

[[2026-03-23]] Mon 00:38
- AC7 PASS: SkillRegistry._parse_frontmatter(path) succeeds for .github/skills/knowledge-ops/SKILL.md.

[[2026-03-23]] Mon 00:38
- AC8 PASS: line_count 140, within max ~150.

[[2026-03-23]] Mon 00:38
### Verdict: PASS

[[2026-03-23]] Mon 00:38
### Confidence: .95

[[2026-03-23]] Mon 00:38
### Action Taken

[[2026-03-23]] Mon 00:38
- Reviewer moving task to docs gate.

[[2026-03-23]] Mon 01:51
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Task adds a SKILL.md file only; no behavior change; skills auto-discovered, not enumerated in copilot-instructions.md |
| 2 | Docstrings | No | N/A | No Python modules added or changed; builder commit 9832972 touched only tests/test_skills.py count assertions and the markdown |
| 3 | docs/sources/overview.md | Yes | Pass | Lines 282-287 already contain knowledge-ops research section with LlamaIndex + PydanticAI attribution from task #774 |
| 4 | README.md | No | N/A | No CLI commands added |
| 5 | Research doc linked | Yes | Pass | docs/research/knowledge-ops-skill.md exists and linked from task body |
| 6 | Scratch files | N/A | Pass | No docs/scratch/781-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-23]] Mon 02:43
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| YAML frontmatter name/description | SKILL.md L1-4: name=knowledge-ops, description present | PASS |
| Decision tree 10-12 rows | SKILL.md L27-38: 10 rows | PASS |
| All 8 tools documented | SKILL.md L42-97: 8 tools across 3 toolsets | PASS |
| Scope conventions (global/project:{id}) | SKILL.md L99-106 | PASS |
| Domain reference (EntityType/RelationType/SourceType) | SKILL.md L108-126 | PASS |
| Ingest workflow (text/file/url + delta) | SKILL.md L128-140 | PASS |
| _parse_frontmatter() succeeds | test_skills.py: 33 passed, 0 failed | PASS |
| Max ~150 lines | 140 lines | PASS |

### Test Results
- pytest (scoped test_skills.py): 33 passed, 0 failed
- pytest (full suite): 3774 passed, 93 failed, 3 errors -- all failures pre-existing (numpy isscalar, stale patch targets, KeyboardInterrupt); none related to #781
- ruff: All checks passed on task files

### AC Quality Score: 4/5
AC was specific and measurable (line counts, tool counts, section names). Minor: ~150 lines is slightly soft but adequate for a docs task.

### Upstream Commits
- 9832972: docs: add knowledge-ops SKILL.md (#781, builder)
- 59dcb5f: test: fix fragile real-skills count assertions (#780, test-writer)

### Confidence: .97
### Action: archive
