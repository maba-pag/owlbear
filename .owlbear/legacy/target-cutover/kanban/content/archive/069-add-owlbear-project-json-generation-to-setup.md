---
id: 69
title: Add owlbear-project.json generation to setup script
status: archived
priority: medium
created: 2026-03-26 20:05:10.730334+01:00
updated: 2026-03-30 02:46:05.522949+02:00
started: 2026-03-30 02:46:00.627571+02:00
completed: 2026-03-30 02:46:00.627571+02:00
tags:
- phase-1
- scope:cli
depends_on:
- 68
- 75
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Setup script (#12) must write owlbear-project.json using the OwlbearProjectFile model.

## Acceptance Criteria
- [ ] Function `create_project_json(project_dir: Path, owlbear_dir: Path, *, name: str | None = None, project_type: str = bare) -> None` added to `scripts/setup.py`
- [ ] Writes `{project_dir}/owlbear-project.json` with all 5 fields: schema_version, name, type, owlbear_path, created_at
- [ ] owlbear_path uses existing `compute_owlbear_relpath()` (POSIX forward slashes)
- [ ] name defaults to `project_dir.name`; project_type defaults to `bare`
- [ ] created_at is timezone-aware UTC (`datetime.now(tz=UTC)`)
- [ ] Constructs `OwlbearProjectFile` (from `owlbear_mcp_project.models`) for validation; serializes with `model_dump_json(indent=2)`
- [ ] Idempotent: skips if file already exists (print message, no overwrite)
- [ ] Called from `setup()` function
- [ ] All #75 tests pass GREEN

## Context
Depends on OwlbearProjectFile model task (#68, archived). See docs/research/owlbear-project-json-schema.md.
Test task: #75 (TDD RED phase).
Research: docs/research/setup-script-project-json-generation.md.

### Implementation Notes
- Reuse existing `compute_owlbear_relpath()` in setup.py for owlbear_path (already produces POSIX paths)
- Follow construct-then-serialize pattern: `OwlbearProjectFile(...)` validates on construction, `model_dump_json(indent=2)` serializes
- Pattern follows existing `create_copilot_instructions()` and `create_mcp_config()` in setup.py
- Windows cross-drive constraint: `os.path.relpath` raises ValueError if owlbear and project are on different drives (known limitation, not handled)

[[2026-03-29]] Sun 15:34
## Architecture Review
**Verdict:** APPROVE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Function signature with name/project_type params | Precise: matches test task #75 expectations and research recommendations | Refined from original (no signature specified) |
| Writes 5 fields | Clear enumeration of all fields | Keep |
| owlbear_path via compute_owlbear_relpath | Reuses existing function, POSIX guarantee testable | Refined: added forward-slash requirement |
| name/type defaults | Testable defaults matching existing setup() pattern | Added (was missing from original AC) |
| created_at timezone-aware UTC | AwareDatetime enforced by model, testable | Refined from vague ISO 8601 |
| Construct OwlbearProjectFile for validation | Pydantic validates on construction, no separate step | Refined: specified import path and serialization method |
| Idempotent skip | Matches existing create_mcp_config() pattern | Keep |
| Called from setup() | Integration point specified | Added |
| #75 tests pass GREEN | TDD compliance | Added |

### Architecture Notes
Single domain: scope:cli (scripts/). Follows existing setup.py patterns exactly. compute_owlbear_relpath() already handles cross-platform POSIX normalization. OwlbearProjectFile import from owlbear_mcp_project.models requires mcp-project package available at runtime (valid: setup runs via uv run from owlbear dir). No new security surface (local file write only, confined to project_dir). No module layering concerns (scripts/ is assembly-level, may import from packages).

### Changes Made
- Rewrote AC: added function signature, forward-slash requirement, name/type defaults, import path, TDD line
- Preserved objective, context, and research references
- Added implementation notes for builder guidance

### Dependencies
- Verified: #68 (OwlbearProjectFile model) archived
- Verified: #75 (test task) in backlog, depends_on [68] correct
- #69 depends_on [68, 75] correct: impl waits for both model and tests

[[2026-03-29]] Sun 15:51
## Test-Writer Notes
- Test file: tests/test_setup_script.py
- Classes: TestFromAC_ProjectJsonGeneration
- Tests per category: happy 6, edge 2, error 1, boundary 6
- Total: 15 tests, all FAIL (14 ImportError + 1 AssertionError)
- ruff: clean
- Note: function name corrected from generate_project_json (prior draft) to create_project_json per AC #69
- AC coverage:
  AC1 (5 fields written): test_creates_owlbear_project_json_file, test_written_json_has_all_five_required_fields
  AC2 (schema_version=1): test_schema_version_is_one
  AC3 (POSIX forward slashes): test_owlbear_path_uses_forward_slashes, test_owlbear_path_is_relative_not_absolute
  AC4 (name/type defaults + overrides): test_name_defaults_to_project_dir_name, test_project_type_defaults_to_bare, test_explicit_name_overrides_default, test_explicit_project_type_overrides_default
  AC5 (created_at UTC): test_created_at_is_timezone_aware, test_created_at_is_utc_offset_zero, test_created_at_is_valid_iso8601
  AC6 (model validation): test_output_validates_against_owlbear_project_file_model
  AC7 (idempotent): test_idempotent_skips_if_file_exists
  AC8 (called from setup()): test_setup_creates_owlbear_project_json

-t

[[2026-03-30]] Mon 01:17
## Review Evidence
Reviewer: reviewer | Task #69 | Date: 2026-03-30

### Test Results
- pytest TestFromAC_ProjectJsonGeneration: 15/15 passed
- pytest full test_setup_script.py: 60/60 passed (0 regressions)
- ruff scripts/setup.py tests/test_setup_script.py: All checks passed

### Test-Writer Coverage Table
| AC Line | Mapped Tests | Would Fail If Violated? | Verdict |
|---------|-------------|------------------------|---------|
| AC1 - 5 fields written | test_creates_owlbear_project_json_file, test_written_json_has_all_five_required_fields | Yes - checks all 5 by name | COVERED |
| AC2 - schema_version=1 | test_schema_version_is_one | Yes - asserts == 1 | COVERED |
| AC3 - POSIX forward slashes via compute_owlbear_relpath | test_owlbear_path_uses_forward_slashes, test_owlbear_path_is_relative_not_absolute | Yes - checks no backslash, not absolute | COVERED |
| AC4 - name/type defaults + overrides | 4 tests: default name, default bare, explicit name, explicit type | Yes - exact value checks | COVERED |
| AC5 - created_at UTC aware | test_created_at_is_timezone_aware, test_created_at_is_utc_offset_zero, test_created_at_is_valid_iso8601 | Yes - checks tzinfo not None AND utcoffset==0 | COVERED |
| AC6 - OwlbearProjectFile validation + model_dump_json | test_output_validates_against_owlbear_project_file_model | Yes - round-trip via model_validate_json | COVERED |
| AC7 - Idempotent skip | test_idempotent_skips_if_file_exists | Yes - sentinel check | COVERED |
| AC8 - Called from setup() | test_setup_creates_owlbear_project_json | Yes - integration via setup() | COVERED |

### TestFromAC Comparison Table
| Test | Change | Assessment |
|------|--------|------------|
| All 15 TestFromAC_ProjectJsonGeneration tests | No modifications by builder | PRESERVED |

### Security Review
- No hardcoded secrets
- No injection vulnerabilities (path construction uses Path operations, no shell)
- No path traversal risk (project_dir is caller-controlled, not user text input)
- No insecure deserialization (only serializing via model_dump_json)
- Pydantic validation before write: correct boundary check

### Test Quality
- Assertion specificity: STRONG - all assertions check exact values, not just existence
- Negative/error path coverage: STRONG - idempotent test uses sentinel, UTC offset test specifically checks offset==0 not just non-None tzinfo
- Test independence: STRONG - all use tmp_path fixture, no shared state
- Descriptive test names: STRONG - all names describe scenario and expected outcome

### Implementation Review (untested complexity check)
create_project_json is 15 LOC. Single branch (exists check). All branches tested.
Print message on idempotent skip is untested but is pure UX output, not a correctness concern (follows existing pattern in create_mcp_config). No hidden complexity.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Function signature create_project_json(project_dir, owlbear_dir, *, name=None, project_type=bare) | setup.py L113-120 | PASS |
| Writes 5 fields: schema_version, name, type, owlbear_path, created_at | test_written_json_has_all_five_required_fields PASS | PASS |
| owlbear_path via compute_owlbear_relpath (POSIX) | test_owlbear_path_uses_forward_slashes PASS | PASS |
| name defaults to project_dir.name; project_type defaults to bare | 4 default/override tests PASS | PASS |
| created_at timezone-aware UTC | test_created_at_is_utc_offset_zero PASS (offset==0) | PASS |
| OwlbearProjectFile + model_dump_json | setup.py L130-138; test_output_validates PASS | PASS |
| Idempotent: skips if exists (print + no overwrite) | test_idempotent_skips_if_file_exists PASS | PASS |
| Called from setup() | setup.py L172; test_setup_creates PASS | PASS |
| All #75 tests pass GREEN | 15/15 TestFromAC GREEN | PASS |

### Verdict: PASS (confidence .96)

[[2026-03-30]] Mon 01:23
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Distribution row: added owlbear-project.json to setup.py artifact list |
| 2 | Docstrings complete | Yes | Pass | create_project_json has one-liner docstring consistent with project style |
| 3 | docs/sources/overview.md | Yes | Pass | Sources logged at lines 574-576 (os.path.relpath, PurePath.as_posix, npm init) |
| 4 | README.md | No | N/A | No CLI surface change |
| 5 | Research docs linked | Yes | Pass | docs/research/setup-script-project-json-generation.md and owlbear-project-json-schema.md both exist and linked from task body |

### Files Updated
- .github/copilot-instructions.md (Distribution row â€” added owlbear-project.json)

### Scratch Files Cleaned
- None found

[[2026-03-30]] Mon 02:45
## Audit
### AC Verification (spot-check, trusting reviewer .96 evidence)
| AC Line | Evidence | Status |
|---------|----------|--------|
| Function signature create_project_json(...) | setup.py L113-120, matches spec exactly | PASS |
| Writes 5 fields | 16/16 tests GREEN incl test_written_json_has_all_five_required_fields | PASS |
| owlbear_path via compute_owlbear_relpath (POSIX) | setup.py L131, reuses existing helper | PASS |
| name/type defaults | Reviewer evidence: 4 default/override tests PASS | PASS |
| created_at timezone-aware UTC | Reviewer evidence: utcoffset==0 test PASS | PASS |
| OwlbearProjectFile + model_dump_json | setup.py L128-138, import at L12 confirmed | PASS |
| Idempotent skip | Reviewer evidence: sentinel check PASS | PASS |
| Called from setup() | setup.py L172, integration test PASS | PASS |
| All #75 tests GREEN | 16/16 passed (15 AC + 1 builder) | PASS |

### Test Results
- pytest test_setup_script.py: 16/16 passed
- Full suite: 1051 passed, 133 failed (all unrelated RED-phase: #194, #196, rename, infra)
- ruff: All checks passed

### Upstream Commits
| Commit | Type | Files | Task |
|--------|------|-------|------|
| 902a00d | test | tests/test_setup_script.py | #69 |
| 6701b95 | feat | scripts/setup.py | #69 |
| c13897c | docs | .github/copilot-instructions.md | #69 |

### AC Quality Score: 5/5
AC was specific, complete, testable. Builder needed no improvisation.

### Confidence: .97
### Action: archive
