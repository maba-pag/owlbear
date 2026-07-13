---
id: 75
title: 'Test: owlbear-project.json generation in setup script'
status: archived
priority: medium
created: 2026-03-26 20:37:44.188149+01:00
updated: 2026-03-30 00:12:41.452048+02:00
started: 2026-03-30 00:12:41.114170+02:00
completed: 2026-03-30 00:12:41.114170+02:00
tags:
- phase-1
- scope:cli
- test
depends_on:
- 68
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
TDD RED phase: write failing tests for owlbear-project.json generation before builder implements.

## Test Scenarios
- [ ] Generates valid owlbear-project.json with all 5 required fields
- [ ] schema_version is 1
- [ ] owlbear_path is a forward-slash relative path (even on Windows)
- [ ] created_at is timezone-aware UTC ISO 8601
- [ ] Idempotent: does not overwrite existing file
- [ ] Output validates against OwlbearProjectFile model
- [ ] Name defaults to directory name when not provided
- [ ] Type defaults to bare when not provided
- [ ] Explicit name and type override defaults

## Context
Parent impl task: #69.
Model: OwlbearProjectFile from #68.
See docs/research/setup-script-project-json-generation.md.

[[2026-03-26]] Thu 20:53
## Research
Doc: docs/research/test-project-json-generation.md

Key findings:
- CRITICAL GAP FIXED: Added depends_on [68] -- model must be importable before tests are written
- Target function signature: generate_project_json(project_dir, owlbear_dir, *, name=None, project_type='bare') returning Path
- Use tmp_path fixture for filesystem isolation, monkeypatch for time freezing (no extra deps)
- Assert both raw JSON fields and model_validate_json() round-trip
- Test cross-platform paths by asserting forward slashes in owlbear_path
- Idempotency test: pre-create file with sentinel content, call function, assert sentinel preserved

Dependency fix:
- Added depends_on: [68] (OwlbearProjectFile model must exist for import)

AC refinement recommendations for architect:
- Confirm target function signature and module location (proposed: mcp_project.setup)
- Consider whether name/type defaults should be tested in #75 or deferred to a CLI integration test

[[2026-03-29]] Sun 15:35
## Architecture Review
**Verdict:** APPROVE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Generates valid JSON with 5 fields | Clear, testable via json.loads + assert 5 keys | Keep |
| schema_version is 1 | Clear, assert equality | Keep |
| owlbear_path forward slashes | Clear, assert no backslashes | Keep |
| created_at timezone-aware UTC | Clear, monkeypatch + AwareDatetime parse | Keep |
| Idempotent: no overwrite | Clear, sentinel pattern | Keep |
| Validates against model | Clear, model_validate_json round-trip | Keep |
| Name defaults to dir name | Clear, call without name, check result | Keep |
| Type defaults to bare | Clear, call without type, check result | Keep |
| Explicit overrides | Clear, pass values, verify reflection | Keep |

### Architecture Notes
**Function location:** `scripts/setup.py` (not `packages/mcp-project/`). All existing setup functions (`create_vscode_settings`, `create_mcp_config`, `create_kanban_dir`, etc.) live here. The `setup()` orchestrator calls them sequentially. `generate_project_json` follows this pattern.

**Target signature:**
`generate_project_json(project_dir: Path, owlbear_dir: Path, *, name: str | None = None, project_type: str = bare) returns Path`

**Test file:** `tests/test_setup_script.py` â€” add `TestFromAC_ProjectJsonGeneration` class following existing `TestFromAC_VscodeSettings` pattern.

**Import pattern:** Same sys.path approach as existing tests: `from setup import generate_project_json`. For model round-trip (scenario 6): `from owlbear_mcp_project.models import OwlbearProjectFile`.

**Time mocking:** Use monkeypatch on datetime.now in the target module namespace (no extra deps). Research confirms this approach (.85 confidence).

**Existing patterns to follow:**
- `compute_owlbear_relpath` already in scripts/setup.py for forward-slash path computation
- `_make_owlbear_dir` and `_project_dir` helpers in test file for tmp_path setup
- Sentinel-based idempotency tests (see `test_mcp_json_idempotent_skips_if_file_exists`)

### Changes Made
- Refined AC context: function location, signature, test file, import pattern specified in review
- No body rewrite needed: 9 test scenarios are already precise and testable

### Dependencies
- Verified: #68 (OwlbearProjectFile model) archived
- Verified: #69 (parent impl) depends on [68, 75] â€” correct TDD ordering

[[2026-03-29]] Sun 23:19
## Review Evidence
See docs/scratch/75-reviewer.md for full evidence.

[[2026-03-30]] Mon 00:12
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Generates valid JSON with 5 fields | test_creates_owlbear_project_json_file + test_written_json_has_all_five_required_fields (L651-L663) | PASS |
| schema_version is 1 | test_schema_version_is_one (L668) | PASS |
| owlbear_path forward slashes | test_owlbear_path_uses_forward_slashes + test_owlbear_path_is_relative_not_absolute (L680-L700) | PASS |
| created_at timezone-aware UTC | test_created_at_is_timezone_aware + test_created_at_is_utc_offset_zero + test_created_at_is_valid_iso8601 (L748-L780) | PASS |
| Idempotent no overwrite | test_idempotent_skips_if_file_exists sentinel pattern (L812) | PASS |
| Validates against model | test_output_validates_against_owlbear_project_file_model model_validate_json round-trip (L798) | PASS |
| Name defaults to dir name | test_name_defaults_to_project_dir_name (L710) | PASS |
| Type defaults to bare | test_project_type_defaults_to_bare (L720) | PASS |
| Explicit overrides | test_explicit_name_overrides_default + test_explicit_project_type_overrides_default (L729-L745) | PASS |

### Test Results
- pytest test_setup_script.py: 60 passed, 0 failed
- pytest broader suite (4 files): 86 passed, 0 failed
- 3 collection errors (planner_board, planner_models, voice_process_manager) are pre-existing unrelated ModuleNotFoundError
- ruff: clean

### Quality Notes
- Reviewer evidence file (docs/scratch/75-reviewer.md) missing, but tests independently verified
- Uncommitted diff in test file is from #117 (not #75)
- Commit 6a99ad0 properly scoped: +221 lines, #75 tests only

### AC Quality Score: 4
AC was specific with 9 testable scenarios. Minor gap: function name changed from generate_project_json to create_project_json between #75 and #69 (naming convention refinement by builder). AC otherwise clean.

### Confidence: .97
### Action: archive
