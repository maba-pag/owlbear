---
id: 100
title: 'Test: owlbear-voice workspace package scaffolding'
status: archived
priority: medium
created: 2026-03-28 04:10:07.825246+01:00
updated: 2026-03-29 04:59:25.287435+02:00
started: 2026-03-29 04:59:20.473326+02:00
completed: 2026-03-29 04:59:20.473326+02:00
tags:
- phase-3
- scope:voice
- test
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Verify owlbear-voice package scaffolding meets AC from task #52.

## Acceptance Criteria
- [ ] Test pyproject.toml exists at packages/voice/pyproject.toml
- [ ] Test pyproject.toml declares name=owlbear-voice, version=0.1.0, requires-python>=3.12
- [ ] Test pyproject.toml declares hatchling build-backend
- [ ] Test hatch wheel config targets packages = [src/owlbear_voice]
- [ ] Test base dependencies listed (moonshine-voice, numpy, pyttsx3, sounddevice)
- [ ] Test [kokoro] optional extra declared with kokoro and soundfile
- [ ] Test entry point owlbear-voice declared
- [ ] Test __init__.py stub exists at packages/voice/src/owlbear_voice/__init__.py
- [ ] Test main.py stub exists with callable main()
- [ ] Test packages/voice/tests/__init__.py exists
- [ ] Test root pyproject.toml ruff src includes packages/voice/src
- [ ] Test owlbear_voice is importable

## Test Pattern
Follow TestFromAC_* class pattern from tests/test_monorepo_skeleton.py.
Parse pyproject.toml with tomllib for metadata assertions (name, version, requires-python, build-system, hatch config, dependencies, optional-dependencies, scripts).
Use Path existence checks for file stubs. Use importlib for importability.

## Context
See task #52 for implementation AC. See docs/research/voice-addon-architecture.md.

[[2026-03-28]] Sat 21:43
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
| pyproject.toml exists | Clear, testable | Keep |
| name, version, requires-python | Tightened from original (added version, requires-python) | Refined |
| hatchling build-backend | Split from metadata line for clarity | Refined |
| hatch wheel config | NEW: covers #52 AC gap | Added |
| base deps | Clear, testable | Keep |
| kokoro optional extra | Tightened: now specifies kokoro + soundfile | Refined |
| entry point | Clear, testable | Keep |
| __init__.py stub | Clear, testable | Keep |
| main.py callable | Clear, testable | Keep |
| tests/__init__.py | Clear, testable | Keep |
| ruff src | Clear, testable | Keep |
| importable | Clear, testable | Keep |

### Architecture Notes
- Pattern: follow TestFromAC_* class pattern from tests/test_monorepo_skeleton.py
- Use tomllib for pyproject.toml parsing (not string matching) for metadata assertions
- Existing package pattern confirmed: packages/knowledge/pyproject.toml uses hatchling with [tool.hatch.build.targets.wheel]
- No security surface (test-only task)
- Single domain: scope:voice (test scaffolding)

### Changes Made
- Refined AC from 10 lines to 12 lines (added version/requires-python, hatch wheel config, kokoro contents)
- Added Test Pattern section with implementation guidance

### Dependencies
- Verified: #52 (implementation) at todo with depends_on #100

[[2026-03-28]] Sat 22:56
## Test-Writer Notes
- Test file: tests/test_voice_package_scaffolding.py
- Classes: TestFromAC_VoicePackageFiles, TestFromAC_VoiceProjectMetadata, TestFromAC_VoiceBuildSystem, TestFromAC_VoiceHatchWheelConfig, TestFromAC_VoiceBaseDependencies, TestFromAC_VoiceKokoroOptionalExtra, TestFromAC_VoiceEntryPoint, TestFromAC_VoiceMainCallable, TestFromAC_VoiceRootRuffConfig, TestFromAC_VoiceImportability
- Tests per category: happy 14, edge 3, error 0, boundary 4
- Total: 21 tests, all FAIL
- ruff: clean
- AC coverage:
  AC1 (pyproject.toml exists): test_voice_pyproject_toml_exists
  AC2 (name/version/requires-python): test_package_name_is_owlbear_voice, test_package_version_is_0_1_0, test_requires_python_gte_3_12
  AC3 (hatchling build-backend): test_build_backend_is_hatchling, test_hatchling_in_build_requires
  AC4 (hatch wheel config): test_hatch_wheel_packages_targets_owlbear_voice
  AC5 (base deps): test_base_deps_moonshine_voice, test_base_deps_numpy, test_base_deps_pyttsx3, test_base_deps_sounddevice
  AC6 (kokoro optional extra): test_kokoro_optional_extra_key_declared, test_kokoro_extra_includes_kokoro_package, test_kokoro_extra_includes_soundfile
  AC7 (entry point): test_entry_point_owlbear_voice_declared
  AC8 (__init__.py stub): test_voice_init_stub_exists
  AC9 (main.py callable): test_voice_main_stub_exists, test_main_py_defines_main_function
  AC10 (tests/__init__.py): test_voice_tests_init_exists
  AC11 (ruff src): test_root_ruff_src_includes_voice
  AC12 (importable): test_owlbear_voice_importable

[[2026-03-29]] Sun 03:50
## Builder Notes
- Files changed: packages/voice/pyproject.toml, packages/voice/src/owlbear_voice/__init__.py, packages/voice/src/owlbear_voice/main.py, packages/voice/tests/__init__.py, pyproject.toml (ruff src)
- Tests: 21 passed, all TestFromAC_* green
- Lint: ruff clean
- Evidence: 21/21 passed, 0 failures
- Fixes applied: None

[[2026-03-29]] Sun 04:31
## Review Evidence
See docs/scratch/100-reviewer.md for full evidence.
