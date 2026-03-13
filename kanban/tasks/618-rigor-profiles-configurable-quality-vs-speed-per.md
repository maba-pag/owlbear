---
id: 618
title: 'Rigor profiles: configurable quality-vs-speed per task type'
status: archived
priority: important
created: 2026-03-07T05:20:49.5381093+01:00
updated: 2026-03-09T19:25:39.8378611+01:00
started: 2026-03-07T06:31:08.0652413+01:00
completed: 2026-03-09T19:25:39.8378611+01:00
tags:
    - scope:core
    - config
class: standard
---

Add rigor profile config model to OwlBearSettings. Profiles define quality-vs-speed presets that downstream consumers (orchestrator, agent turn loop) read from deps. This task covers the data model, config wiring, and resolution from kanban tags  NOT enforcement (turn limiting, review gate toggling).

See docs/research/orchestration-agent-frameworks.md S3.2 and docs/research/nwave.md S3.3 P1.

AC:
- [ ] `RigorProfile` frozen dataclass in `config.py` with fields: `review_enabled: bool`, `tdd_depth: Literal['full', 'smoke', 'none']`, `turn_budget: int`
- [ ] 3 preset module-level constants: `RIGOR_LEAN` (review_enabled=False, tdd_depth='smoke', turn_budget=15), `RIGOR_STANDARD` (review_enabled=True, tdd_depth='full', turn_budget=30), `RIGOR_THOROUGH` (review_enabled=True, tdd_depth='full', turn_budget=50)
- [ ] `rigor_profiles: dict[str, RigorProfile]` field on `OwlBearSettings` defaulting to `{'lean': RIGOR_LEAN, 'standard': RIGOR_STANDARD, 'thorough': RIGOR_THOROUGH}`
- [ ] `default_rigor: str` field on `OwlBearSettings` defaulting to `'standard'`; validated that key exists in `rigor_profiles`
- [ ] `resolve_rigor_profile(settings: OwlBearSettings, task_tags: Sequence[str]) -> RigorProfile` function in `config.py`  extracts first `rigor:*` tag, returns matching profile or default
- [ ] `rigor_profile: RigorProfile | None` field added to `OwlBearDeps` (default None)
- [ ] Bootstrap wires `settings.rigor_profiles[settings.default_rigor]` into `OwlBearDeps.rigor_profile`

Out of scope (follow-up tasks):
- Turn budget enforcement in agent turn loop
- Review gate toggling based on profile
- Per-agent-type rigor overrides

Architecture notes:
- Extends OwlBearSettings (pydantic-settings)  follows existing config patterns
- RigorProfile is a frozen dataclass (not a pydantic model) to stay in config.py's leaf position
- resolve_rigor_profile lives in config.py (pure function, no upward imports)
- OwlBearDeps gains one field  minimal change to injection surface
- Bootstrap reads settings and resolves default profile into deps at startup

[[2026-03-09]] Mon 15:27
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 3 preset profiles in config | Vague: no fields, no types, no values | Rewritten with exact fields/types/values |
| Per-task override via kanban tag | Missing: no function signature, no resolution semantics | Rewritten as `resolve_rigor_profile` with clear inputs/outputs |
| Profile affects turn budget and review gate | SRP violation: bundles enforcement with data model | Removed from scope; enforcement is follow-up task |
| Default profile: standard | Clear but insufficient: no validation that key exists in dict | Rewritten with field_validator |

### Architecture Notes
- **config.py is leaf**: `RigorProfile` must be a frozen dataclass (not a pydantic model) to avoid importing pydantic-settings classes upward. Matches existing pattern where config.py has no deps on other owlbear modules.
- **Existing config pattern**: `OwlBearSettings` already has ~40 fields with sensible defaults, field_validators for numeric constraints, and model_validators for cross-field rules. Adding `rigor_profiles` dict + `default_rigor` str follows this pattern exactly.
- **OwlBearDeps injection**: Currently has 4 fields (hooks, tracker, agent_registry, delegation_depth). Adding `rigor_profile` is minimal. Bootstrap already constructs deps from settings  adding one more field is a 2-line change.
- **resolve_rigor_profile in config.py**: Pure function, no upward imports. Takes settings + tags list, returns RigorProfile. Keeps resolution logic co-located with the profile definitions.
- **KISS compliance**: Research warns against over-engineering (nWave DES is ~60 files). This task is config-only  enforcement stays out of scope.
- **Module layering verified**: config.py (leaf) -> deps.py (core/) -> bootstrap.py (assembly). No layering violations.

### Changes Made
- Rewrote body with precise AC (7 verifiable items)
- Removed enforcement from scope (turn budget, review gate toggling)
- Added architecture notes about frozen dataclass, module layering, and config patterns
- Created test task #710 (RED phase)

### Dependencies
- Created: #710 (test task, RED phase)  depends on #618 AC
- No upstream dependencies required
- Follow-up needed: turn budget enforcement task, review gate toggle task

-t

[[2026-03-09]] Mon 16:33
## Architecture Review (2nd pass)
**Verdict:** APPROVED

### AC Assessment

All 7 AC items evaluated individually -- each is precise and mechanically verifiable.

- RigorProfile frozen dataclass: fields, types specified. Frozen DC keeps config.py leaf.
- 3 preset constants: names, values, types exact.
- rigor_profiles dict: default with 3 presets. Matches OwlBearSettings pattern.
- default_rigor validator: validates key exists. Matches existing field_validator pattern.
- resolve_rigor_profile(): precise signature, extraction, fallback semantics.
- OwlBearDeps.rigor_profile: Optional, default None. Minimal injection change.
- Bootstrap wiring: behavioral spec. Builder follows tracker/agent_registry precedent.

### Architecture Notes

Module layering verified: config.py (leaf) -> deps.py (core/) -> agent.py -> bootstrap.py (assembly). RigorProfile in config.py as frozen dataclass, imported under TYPE_CHECKING. No cycles.

Research divergence (intentional): tdd_depth (3-valued) replaces docs_gate_enabled (bool). YAGNI -- docs gate follows review gate in lockstep.

KISS: 1 dataclass, 3 constants, 2 settings fields, 1 pure function, 1 deps field. No enforcement.

### Changes Made
- Added test AC to #710: OwlBearDeps.rigor_profile field test
- Moved #618 to todo

### Dependencies
- No upstream deps required
- #710 (test RED phase) ready for test-writer

[[2026-03-09]] Mon 16:51
## Test-Writer Notes
- Test file: tests/test_rigor_profile.py
- Classes: TestFromACRigorProfileDataclass, TestFromACRigorPresets, TestFromACRigorSettings, TestFromACResolveRigorProfile, TestFromACOwlBearDepsRigor, TestFromACBootstrapRigorWiring
- Tests per category: happy 18, edge 5, error 1, boundary 4
- Total: 28 tests, all FAIL (ImportError)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| RigorProfile frozen DC | test_create_with_all_fields, test_is_frozen, test_is_dataclass | happy, edge |
| 3 preset constants | 9 field-value tests (lean/standard/thorough x 3 fields) | happy |
| rigor_profiles dict | test_rigor_profiles_has_three_keys, 3 match tests, test_custom_profile_accepted | happy, edge |
| default_rigor validated | test_default_rigor_is_standard, test_unknown_default_rigor_rejected | happy, error |
| resolve_rigor_profile() | 6 tests (lean tag, thorough tag, no tag, non-rigor, empty, mixed) | happy, edge, boundary |
| OwlBearDeps.rigor_profile | test_rigor_profile_default_none, test_rigor_profile_accepts_value | happy, edge |
| Bootstrap wiring | test_bootstrap_deps_has_default_rigor_profile | happy |

[[2026-03-09]] Mon 17:10
## Builder Notes
- Files changed: src/owlbear/config.py, src/owlbear/core/deps.py, src/owlbear/core/agent.py, src/owlbear/bootstrap/__init__.py
- Tests: 28 passed (test_rigor_profile.py), 251 passed on related modules (no regressions)
- Coverage: config.py 86%, deps.py 100%, bootstrap/__init__.py 83%
- Lint: ruff clean on all 5 files
- Implementation: RigorProfile frozen dataclass + 3 presets + 2 settings fields + validator + resolve_rigor_profile() + OwlBearDeps field + bootstrap wiring
- No TestFromAC classes modified
- No new dependencies added

[[2026-03-09]] Mon 17:36
## Review Evidence (reviewer, 2026-03-09)

### Test Results
- pytest tests/test_rigor_profile.py: 28 passed, 0 failed (2.24s)
- pytest tests/test_bootstrap*.py: 163 passed, 1 failed (pre-existing slack_sdk ImportError, unrelated)
- ruff check (config.py, deps.py, agent.py, bootstrap/__init__.py, test_rigor_profile.py): All checks passed!
- Coverage: tool hangs prevented independent verification. Builder reports config.py 86%, deps.py 100%.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| RigorProfile frozen DC in config.py | config.py L21-28: @dataclasses.dataclass(frozen=True) class RigorProfile with review_enabled:bool, tdd_depth:Literal, turn_budget:int | test_create_with_all_fields, test_is_frozen, test_is_dataclass | PASS |
| 3 preset constants (LEAN/STANDARD/THOROUGH) | config.py L30-32: exact values match AC spec | 9 field-value tests (lean/standard/thorough x 3 fields) | PASS |
| rigor_profiles dict on OwlBearSettings | config.py L293-299: dict[str, RigorProfile] Field with 3 presets | test_rigor_profiles_has_three_keys + 3 match tests | PASS |
| default_rigor validated | config.py L301-303 + L312-319: field_validator checks key exists in rigor_profiles | test_default_rigor_is_standard, test_unknown_default_rigor_rejected | PASS |
| resolve_rigor_profile() | config.py L431-445: extracts first rigor:* tag, falls back to default | 6 tests (lean tag, thorough tag, no tag, non-rigor, empty, mixed) | PASS |
| OwlBearDeps.rigor_profile | deps.py L32: rigor_profile: RigorProfile `|` None = field(default=None), TYPE_CHECKING import L13 | test_rigor_profile_default_none, test_rigor_profile_accepts_value | PASS |
| Bootstrap wiring | bootstrap/__init__.py L164: rigor_profile=settings.rigor_profiles[settings.default_rigor] passed to OwlBearAgent, agent.py L67+L78 forwards to OwlBearDeps | test_bootstrap_deps_has_default_rigor_profile | PASS |

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | All assertions check exact values (bools, strings, ints). test_is_frozen asserts FrozenInstanceError. test_is_dataclass uses dataclasses.is_dataclass(). No lazy assert result patterns. |
| Negative/error paths | ADEQUATE | test_unknown_default_rigor_rejected (ValidationError), test_is_frozen (FrozenInstanceError). Minor gap: no test for rigor:nonexistent tag (gracefully falls back to default in code). |
| Mutation reasoning | STRONG | Flipping review_enabled -> fails preset tests. Changing turn_budget values -> fails specific tests. Removing frozen=True -> fails test_is_frozen. Removing validator -> fails test_unknown_default_rigor_rejected. Removing rigor_profile from deps -> fails 2 OwlBearDeps tests. |
| Test independence | STRONG | Each test uses fresh instances or default_settings fixture (clears OWLBEAR_ env vars). No shared mutable state. |
| Descriptive names | STRONG | All names describe scenario + expectation: test_lean_review_disabled, test_returns_lean_for_rigor_lean_tag, test_bootstrap_deps_has_default_rigor_profile. |

### Security: No issues. Pure data model + pure function. No secrets, no injection surfaces, no path traversal, no deserialization, no new dependencies. Error messages in validator expose only key names (non-sensitive).

### Test Writer vs Builder Comparison
Builder notes state 'No TestFromAC classes modified'. Verified: git shows test file is untracked (single creation point by test-writer). All 6 TestFromAC classes (28 methods) are PRESERVED -- no modifications, deletions, or weakening.

### Verdict: PASS confidence .93

[[2026-03-09]] Mon 17:36
## Review Evidence (reviewer, 2026-03-09)

### Test Results
- pytest tests/test_rigor_profile.py: 28 passed, 0 failed (2.24s)
- pytest tests/test_bootstrap*.py: 163 passed, 1 failed (pre-existing slack_sdk ImportError, unrelated)
- ruff check (config.py, deps.py, agent.py, bootstrap/__init__.py, test_rigor_profile.py): All checks passed!
- Coverage: tool hangs prevented independent verification. Builder reports config.py 86%, deps.py 100%.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| RigorProfile frozen DC in config.py | config.py L21-28: @dataclasses.dataclass(frozen=True) class RigorProfile with review_enabled:bool, tdd_depth:Literal, turn_budget:int | test_create_with_all_fields, test_is_frozen, test_is_dataclass | PASS |
| 3 preset constants (LEAN/STANDARD/THOROUGH) | config.py L30-32: exact values match AC spec | 9 field-value tests (lean/standard/thorough x 3 fields) | PASS |
| rigor_profiles dict on OwlBearSettings | config.py L293-299: dict[str, RigorProfile] Field with 3 presets | test_rigor_profiles_has_three_keys + 3 match tests | PASS |
| default_rigor validated | config.py L301-303 + L312-319: field_validator checks key exists in rigor_profiles | test_default_rigor_is_standard, test_unknown_default_rigor_rejected | PASS |
| resolve_rigor_profile() | config.py L431-445: extracts first rigor:* tag, falls back to default | 6 tests (lean tag, thorough tag, no tag, non-rigor, empty, mixed) | PASS |
| OwlBearDeps.rigor_profile | deps.py L32: rigor_profile: RigorProfile `|` None = field(default=None), TYPE_CHECKING import L13 | test_rigor_profile_default_none, test_rigor_profile_accepts_value | PASS |
| Bootstrap wiring | bootstrap/__init__.py L164: rigor_profile=settings.rigor_profiles[settings.default_rigor] passed to OwlBearAgent, agent.py L67+L78 forwards to OwlBearDeps | test_bootstrap_deps_has_default_rigor_profile | PASS |

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | All assertions check exact values (bools, strings, ints). test_is_frozen asserts FrozenInstanceError. test_is_dataclass uses dataclasses.is_dataclass(). No lazy assert result patterns. |
| Negative/error paths | ADEQUATE | test_unknown_default_rigor_rejected (ValidationError), test_is_frozen (FrozenInstanceError). Minor gap: no test for rigor:nonexistent tag (gracefully falls back to default in code). |
| Mutation reasoning | STRONG | Flipping review_enabled -> fails preset tests. Changing turn_budget values -> fails specific tests. Removing frozen=True -> fails test_is_frozen. Removing validator -> fails test_unknown_default_rigor_rejected. Removing rigor_profile from deps -> fails 2 OwlBearDeps tests. |
| Test independence | STRONG | Each test uses fresh instances or default_settings fixture (clears OWLBEAR_ env vars). No shared mutable state. |
| Descriptive names | STRONG | All names describe scenario + expectation: test_lean_review_disabled, test_returns_lean_for_rigor_lean_tag, test_bootstrap_deps_has_default_rigor_profile. |

### Security: No issues. Pure data model + pure function. No secrets, no injection surfaces, no path traversal, no deserialization, no new dependencies. Error messages in validator expose only key names (non-sensitive).

### Test Writer vs Builder Comparison
Builder notes state 'No TestFromAC classes modified'. Verified: git shows test file is untracked (single creation point by test-writer). All 6 TestFromAC classes (28 methods) are PRESERVED -- no modifications, deletions, or weakening.

### Verdict: PASS confidence .93

[[2026-03-09]] Mon 17:44
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Added `rigor:` prefix row to tag taxonomy table |
| 2 | Docstrings complete | Yes | Pass | RigorProfile (L22), resolve_rigor_profile (L431), OwlBearDeps (L20), OwlBearSettings fields have descriptions |
| 3 | sources/overview.md | Yes | Pass | Already has 'Rigor Profiles (Task #618)' section with nWave + Conductor sources |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/rigor-profiles.md exists; task body references orchestration + nwave research |

### Files Updated
- .github/copilot-instructions.md (added rigor: prefix to tag taxonomy)

### Scratch Files Cleaned
- None (no docs/scratch/618-* files found)

[[2026-03-09]] Mon 17:44
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | Updated | Added `rigor:` prefix row to tag taxonomy table |
| 2 | Docstrings complete | Yes | Pass | RigorProfile (L22), resolve_rigor_profile (L431), OwlBearDeps (L20), OwlBearSettings fields have descriptions |
| 3 | sources/overview.md | Yes | Pass | Already has 'Rigor Profiles (Task #618)' section with nWave + Conductor sources |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/rigor-profiles.md exists; task body references orchestration + nwave research |

### Files Updated
- .github/copilot-instructions.md (added rigor: prefix to tag taxonomy)

### Scratch Files Cleaned
- None (no docs/scratch/618-* files found)

[[2026-03-09]] Mon 19:25
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| RigorProfile frozen DC | config.py L21-28: @dataclasses.dataclass(frozen=True) with review_enabled:bool, tdd_depth:Literal, turn_budget:int | PASS |
| 3 preset constants | config.py L31-33: RIGOR_LEAN(False,smoke,15), RIGOR_STANDARD(True,full,30), RIGOR_THOROUGH(True,full,50) | PASS |
| rigor_profiles dict on Settings | config.py L293-299: dict[str,RigorProfile] Field with 3 presets default | PASS |
| default_rigor validated | config.py L301-303 field + L312-319 field_validator checks key in rigor_profiles | PASS |
| resolve_rigor_profile() | config.py L431-445: extracts first rigor:* tag, returns profile or default | PASS |
| OwlBearDeps.rigor_profile | deps.py L33: RigorProfile or None = field(default=None), TYPE_CHECKING import L13 | PASS |
| Bootstrap wiring | bootstrap/__init__.py L160: settings.rigor_profiles[settings.default_rigor] -> OwlBearAgent -> OwlBearDeps | PASS |

### Test Results
- pytest tests/test_rigor_profile.py: 28 passed (1.85s)
- pytest tests/ full suite: 1315 passed, 2 failed (pre-existing: slack_sdk ImportError, Windows PermissionError), 20 skipped
- ruff check (task files): All checks passed

### Confidence: .97
All 7 AC items verified with exact match. 28 tests comprehensive. No deviations.
### Action: archive

### Commit Note
Uncommitted work from multiple tasks is intermingled (bootstrap split #480, research doc moves, etc.). #618 files cannot be cleanly committed in isolation without #480 bootstrap/ directory. Recommend batch commit after other done tasks are also audited.
