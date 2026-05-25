---
id: 1851
title: 'P1-01: Pydantic models for structured decision requests'
status: archived
priority: needed
created: 2026-05-24T20:57:55.018006+02:00
updated: 2026-05-25T02:03:37.807966+02:00
tags:
  - phase-1
  - scope:kanban
  - model
parent: 1850
depends_on: []
ac:
  - RequestOption model validates option_id matching 
    ^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$, label max 120 chars, confidence in [0.0, 
    1.0], rationale max 500 chars; invalid inputs raise ValidationError.
  - DecisionRequest model with kind='decision' requires options with 2-10 items 
    and rejects fewer than 2 or more than 10; ActionRequest model with 
    kind='action' rejects non-empty options; all four models (RequestOption, 
    Resolution, DecisionRequest, ActionRequest) use extra='forbid' and reject 
    unknown fields with ValidationError.
  - 'At-most-one recommended=true constraint: model raises ValidationError when two
    or more options have recommended=true.'
  - "Resolution model has three optional fields: selected_option_id (str|None), free_text
    (str|None), and resolved_at (str|None); all default to None; extra='forbid' rejects
    any additional fields."
  - 'DecisionRequest and ActionRequest share required fields: task_id (int), request_id
    (UUID4-format string), title (str, max 120 chars), summary (str), agent (str),
    created_at (timezone-aware ISO 8601 datetime string; timezone-less ISO 8601 values
    raise ValidationError); and optional resolution (Resolution, defaults to all-None);
    non-UUID4 request_id, title exceeding 120 chars, or malformed/timezone-less created_at
    raises ValidationError.'
  - "Request.model_validate(data) dispatches on kind field via an internal discriminated
    Annotated union: kind='decision' returns DecisionRequest, kind='action' returns
    ActionRequest; invalid or missing kind raises ValidationError."
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- `RequestOption`, `Resolution`, `DecisionRequest`, `ActionRequest` Pydantic models
- Kind-discriminated union type for request creation
- Field constraints per Brief data model table
- `extra="forbid"` on models
- `resolution` block with nullable fields (present but null in pending files)

**Out of scope:**
- File I/O, engine API functions (P1-02)
- MCP or Cockpit layers
- Storage format writing (handled by engine)

## Test scope
`serve/kanban/tests/`

[[2026-05-24T22:01:46+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Models only — no I/O, no engine logic |
| Interface clarity | PASS | AC defines all fields, types, constraints, and error paths |
| Dependency correctness | PASS | No dependencies; foundation task |
| Module layering | PASS | kanban package internal; no upward imports |
| TDD compliance | PASS | Test scope: serve/kanban/tests/ |
| KISS/YAGNI | PASS | Minimal model definitions per Brief spec |
| Premise challenge | PASS | Brief-driven; replaces unstructured prose DR system |
| Pattern consistency | PASS | Follows existing ConfigDict(extra=\"forbid\") on domain sub-models (PathsConfig, PipelineConfig, etc.) |
| Security surface | PASS | Pure in-memory validation, no system boundaries |
| Single domain | PASS | kanban domain only |

### AC Refinement Applied
- resolved_at fix: Moved from \"excluded from model\" to optional field in Resolution (str|None, default None). Required for parsing resolved files with extra=\"forbid\".
- created_at format: Added ISO 8601 format validation constraint (new model, no legacy precision concern).
- extra=\"forbid\" observable: Added explicit \"reject unknown fields with ValidationError\" failure path.
- Scope leakage removed: Eliminated serialization language from AC4 (belongs in P1-02).
- Field coverage added (AC5): Required fields with constraints for DecisionRequest/ActionRequest.
- Union type added (AC6): Discriminated union behavior is testable.

### Challenge Results
- Challenger: reconsider (confidence 0.33)
- Findings: (1) resolved_at schema contradiction, (2) created_at under-spec, (3) serialization scope leakage, (4) AC overload, (5) evidence mismatch
- Architect response: accepted findings 1-3, revised AC accordingly. Finding 4 (minor overload) accepted as risk but AC lines remain independently testable. Finding 5 (evidence mismatch) resolved by writing refined AC to task before approval.
- Challenger alternative angle on extra=\"allow\" for top-level objects: rebutted — Brief explicitly mandates extra=\"forbid\" as architectural invariant for the new DR system.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC from 4 to 6 lines addressing challenger findings, advanced to todo.

[[2026-05-24T23:57:53+02:00]]
## Test-Writer Notes
- Test file: tests/test_request_models_1851.py
- Classes: TestFromAC_RequestOption, TestFromAC_OptionsCountAndForbid, TestFromAC_RecommendedConstraint, TestFromAC_Resolution, TestFromAC_SharedRequiredFields, TestFromAC_DiscriminatedUnion
- Tests per category: happy 18, edge 7, error 22, boundary 8
- Total: 55 tests, all FAIL (ModuleNotFoundError: owlbear_kanban.request_models — expected)
- ruff: clean

## AC Coverage
| AC | Tests |
|----|-------|
| AC1 RequestOption field constraints | test_valid_option_all_fields, test_option_id_minimum_length_two, test_option_id_maximum_length_63, test_option_id_single_char_raises, test_option_id_length_64_raises, test_option_id_starts_with_dash_raises, test_option_id_ends_with_dash_raises, test_option_id_uppercase_raises, test_option_id_spaces_raises, test_label_exactly_120_chars_valid, test_label_121_chars_raises, test_confidence_zero_valid, test_confidence_one_valid, test_confidence_below_zero_raises, test_confidence_above_one_raises, test_rationale_exactly_500_chars_valid, test_rationale_501_chars_raises, test_extra_field_raises |
| AC2 Options count + extra='forbid' | test_decision_request_with_two_options_valid, test_decision_request_with_ten_options_valid, test_decision_request_one_option_raises, test_decision_request_eleven_options_raises, test_decision_request_zero_options_raises, test_action_request_no_options_valid, test_action_request_empty_list_valid, test_action_request_with_options_raises, test_decision_request_extra_field_raises, test_action_request_extra_field_raises |
| AC3 At-most-one recommended | test_zero_recommended_valid, test_exactly_one_recommended_valid, test_two_recommended_raises, test_three_recommended_raises |
| AC4 Resolution model | test_resolution_all_fields_default_to_none, test_resolution_selected_option_id_set, test_resolution_free_text_set, test_resolution_all_fields_set, test_resolution_null_values_explicit, test_resolution_extra_field_raises |
| AC5 Shared required fields | test_decision_request_all_required_fields, test_action_request_all_required_fields, test_non_uuid4_request_id_raises, test_non_uuid4_sequential_uuid_raises, test_title_exactly_120_chars_valid, test_title_121_chars_raises, test_action_request_title_121_chars_raises, test_malformed_created_at_raises, test_malformed_created_at_on_action_raises, test_resolution_defaults_to_all_none_when_absent, test_resolution_can_be_set_explicitly, test_task_id_must_be_int, test_missing_required_field_raises |
| AC6 Discriminated union | test_kind_decision_resolves_to_decision_request, test_kind_action_resolves_to_action_request, test_invalid_kind_raises, test_missing_kind_raises, test_union_decision_preserves_options, test_union_action_has_no_options |

[[2026-05-25T00:13:31+02:00]]
## Builder Notes
- Files changed:
  - `serve/kanban/src/owlbear_kanban/request_models.py` (new)
- Implementation summary:
  - Added `RequestOption`, `Resolution`, `DecisionRequest`, and `ActionRequest` Pydantic models with `extra="forbid"`.
  - Enforced field constraints from ACs: option_id regex/length, label max 120, confidence [0.0,1.0], rationale max 500.
  - Added shared required-field validation for `task_id`, UUID4-format `request_id`, title max 120, summary, agent, and ISO 8601 timezone-aware `created_at`.
  - Added decision/action option semantics: decision requires 2-10 options; action allows only empty options.
  - Added at-most-one `recommended=true` constraint for decision options.
  - Added discriminated union validation surface via `Request.model_validate(...)` dispatching on `kind`.
- RED verification evidence:
  - `quality-runner` confirmed RED before implementation: test file failed with `ModuleNotFoundError: owlbear_kanban.request_models` (collection error expected), task test lint clean.
- GREEN verification evidence:
  - Scoped tests: `tests/test_request_models_1851.py` -> 57 passed, 0 failed.
  - Lint: clean (`ruff` clean on source + task test file).
  - Coverage: `owlbear_kanban.request_models` 97% (>= 90% gate).
  - Durable module-level test visibility: `No module-level test file — skip`.
- Fixes applied during verification:
  - Resolved ruff violations (TRY003/EM101/PLR2004/I001) by introducing constants/messages and import ordering cleanup.
- Commit:
  - `026067aa` — `feat: add structured request models (#1851, builder)`

[[2026-05-25T00:31:18+02:00]]
## Review Evidence
- Verdict: FAIL
- AC1 through AC4 map cleanly to the implementation and task tests in the current slice.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC5 | Contract authority drift on `created_at`: the approved AC says `ISO 8601 datetime string`, the scoped brief table says `ISO 8601 with timezone`, the implementation rejects timezone-less datetimes, and the tests only prove malformed-string rejection. The approved contract and proof surface are inconsistent. | `.owlbear/kanban/tasks/1851-p1-01-pydantic-models-for-structured-decision-requests.md:30-31`, `.owlbear/kanban/tasks/1851-p1-01-pydantic-models-for-structured-decision-requests.md:50`, `.owlbear/briefs/draft-decision-request-data-model/brief.md:56`, `serve/kanban/src/owlbear_kanban/request_models.py:75-83`, `tests/test_request_models_1851.py:349-355` | backlog |
| 2 | AC6 | The accepted contract says `Request` is the Annotated discriminated union, but the code defines `RequestType` as the union and `Request` as a wrapper class. The task tests only prove the wrapper API, not the stated `Request` union contract. | `.owlbear/kanban/tasks/1851-p1-01-pydantic-models-for-structured-decision-requests.md:33-34`, `serve/kanban/src/owlbear_kanban/request_models.py:108-117`, `tests/test_request_models_1851.py:385-412` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Clarify AC5 by reconciling the frontmatter wording with the brief table and explicitly state whether timezone-less ISO 8601 timestamps are valid plus the required negative proof case. | `.owlbear/kanban/tasks/1851-p1-01-pydantic-models-for-structured-decision-requests.md`, `.owlbear/briefs/draft-decision-request-data-model/brief.md`, `tests/test_request_models_1851.py` | AC5/task scope and current tests diverge: task `:30-31`, `:50`; brief `:56`; tests `:349-355` |
| 2 | architect | Clarify AC6 by specifying whether `Request` itself must be the Annotated union or whether a validator wrapper is acceptable, then restate the expected proof surface accordingly. | `.owlbear/kanban/tasks/1851-p1-01-pydantic-models-for-structured-decision-requests.md`, `serve/kanban/src/owlbear_kanban/request_models.py`, `tests/test_request_models_1851.py` | Contract names `Request` as union, implementation/tests use `RequestType` plus wrapper: task `:33-34`; source `:108-117`; tests `:385-412` |

## Observations
- Builder evidence was otherwise sufficient for scoped tests, lint, and coverage, and AC1 through AC4 map cleanly to code and tests.
- `get_errors` reports no current editor errors in `serve/kanban/src/owlbear_kanban/request_models.py` or `tests/test_request_models_1851.py`.
- The test-writer note says 55 tests, but the current task test file contains 57 `test_` functions. That count mismatch is non-blocking, but the evidence packet should be kept aligned on retry.

[[2026-05-25T00:45:02+02:00]]
## Architecture Review (Re-review after FAIL)
### Reviewer Findings Addressed
| # | Finding | Resolution |
|---|---------|------------|
| 1 | AC5 contract drift: \"ISO 8601 datetime string\" vs Brief's \"ISO 8601 with timezone\" | Refined AC5 to explicitly require timezone-aware ISO 8601; added explicit negative case for timezone-less values |
| 2 | AC6 naming mismatch: AC says `Request` is union, code has wrapper class | Refined AC6 to describe public API `Request.model_validate(data)` dispatching via internal discriminated union — accepts wrapper pattern (standard Pydantic v2 TypeAdapter idiom) |

### AC Changes
- AC5: \"ISO 8601 datetime string\" → \"timezone-aware ISO 8601 datetime string; timezone-less ISO 8601 values raise ValidationError\"
- AC6: \"A discriminated union type Request (Annotated union on kind field)\" → \"Request.model_validate(data) dispatches on kind field via an internal discriminated Annotated union\"

### Implementation Gap
Builder must add one test: a valid ISO 8601 datetime WITHOUT timezone (e.g. `\"2026-05-23T12:00:00\"`) must raise ValidationError. The implementation already handles this (line 78-80 `ERR_CREATED_AT_TZ`), but no test covers that specific code path.

### Evaluation (unchanged from prior review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Models only — no I/O, no engine logic |
| Interface clarity | PASS | AC now precisely defines timezone requirement and wrapper API |
| Dependency correctness | PASS | No dependencies |
| Module layering | PASS | kanban package internal |
| TDD compliance | PASS | Test scope: serve/kanban/tests/ |
| KISS/YAGNI | PASS | Minimal models per Brief |
| Premise challenge | PASS | Brief-driven |
| Pattern consistency | PASS | Follows existing ConfigDict(extra=\"forbid\") pattern |
| Security surface | PASS | Pure validation, no system boundaries |
| Single domain | PASS | kanban only |

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Challenge Results
- Challenger: SKIPPED — re-review of reviewer findings, no new design decisions; prior challenge results still apply

### Verdict: APPROVE (REFINE applied)
### Action Taken: Refined AC5 and AC6 to resolve reviewer findings, advanced to todo.

[[2026-05-25T01:00:14+02:00]]
## Test-Writer Notes
- Retry: added 2 tests for AC5 timezone-less created_at gap (reviewer finding #1 after architect re-review).
- New tests: `test_timezone_less_created_at_on_decision_raises`, `test_timezone_less_created_at_on_action_raises` — added to `TestFromAC_SharedRequiredFields`.
- AC6 finding resolved by architect re-review (wrapper pattern acceptable); existing tests unmodified.
- quality-runner: 59 passed, 0 failed, ruff clean.
- Builder skip: test-only retry, all 59 tests green against current impl.
- Commit: dd942f50

[[2026-05-25T01:16:59+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1851 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: task notes report scoped green proof at `.owlbear/kanban/tasks/1851-p1-01-pydantic-models-for-structured-decision-requests.md:133` and `.owlbear/kanban/tasks/1851-p1-01-pydantic-models-for-structured-decision-requests.md:135`, plus retry proof at `.owlbear/kanban/tasks/1851-p1-01-pydantic-models-for-structured-decision-requests.md:209-210` after the AC5 gap was closed.
- Challenger cross-check: reconsider at 0.76 confidence, but no remaining blocker after the AC5/AC6 refinements; residual concerns are non-blocking contract/evidence hygiene only.
- Safety/security: PASS. `serve/kanban/src/owlbear_kanban/request_models.py` is pure validation code with no I/O, shell, SQL, path, or logging surface.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/kanban/src/owlbear_kanban/request_models.py:21`, `:24`, `:27-28` | `tests/test_request_models_1851.py:test_valid_option_all_fields`; `test_option_id_single_char_raises`; `test_label_121_chars_raises`; `test_confidence_above_one_raises`; `test_rationale_501_chars_raises` | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/request_models.py:24`, `:40`, `:50`, `:91`, `:105` | `tests/test_request_models_1851.py:test_decision_request_with_two_options_valid`; `test_action_request_with_options_raises`; explicit extra-field rejection cases in `TestFromAC_OptionsCountAndForbid` | PASS |
| AC3 | `serve/kanban/src/owlbear_kanban/request_models.py:87`, `:94` | `tests/test_request_models_1851.py:test_zero_recommended_valid`; `test_two_recommended_raises` | PASS |
| AC4 | `serve/kanban/src/owlbear_kanban/request_models.py:37`, `:40` | `tests/test_request_models_1851.py:test_resolution_all_fields_default_to_none`; `test_resolution_all_fields_set`; `test_resolution_extra_field_raises` | PASS |
| AC5 | `serve/kanban/src/owlbear_kanban/request_models.py:52`, `:58`, `:62`, `:75` | `tests/test_request_models_1851.py:test_non_uuid4_request_id_raises`; `test_non_uuid4_sequential_uuid_raises`; `test_malformed_created_at_raises`; `test_timezone_less_created_at_on_decision_raises`; `test_timezone_less_created_at_on_action_raises`; `test_task_id_must_be_int`; `test_missing_required_field_raises` | PASS |
| AC6 | `serve/kanban/src/owlbear_kanban/request_models.py:108`, `:111`, `:117` | `tests/test_request_models_1851.py:test_kind_decision_resolves_to_decision_request`; `test_kind_action_resolves_to_action_request`; `test_invalid_kind_raises`; `test_missing_kind_raises` | PASS |

## Observations
- AC5 currently proves UUID4 parsing/version rejection, but not canonical text normalization of `request_id`. That is not a blocker under the refined AC wording; if filename-stem semantics require canonical form, the follow-on storage task should state it explicitly.
- The task body's AC coverage matrix at `.owlbear/kanban/tasks/1851-p1-01-pydantic-models-for-structured-decision-requests.md:116` and the test header in `tests/test_request_models_1851.py:10-11` still reflect pre-refinement `created_at` wording. The runtime proof is sufficient, but the audit trail should be tightened in a later cleanup.

[[2026-05-25T01:22:47+02:00]]
## Docs Gate

**Verdict: PASS — docs gate passed**

### Changed Files
- `serve/kanban/src/owlbear_kanban/request_models.py` (new) → maps to `serve/kanban/README.md`

### Checklist

| Item | Status | Evidence |
|------|--------|----------|
| 1. README Verification | N/A | `request_models.py` adds internal Pydantic models (`RequestOption`, `Resolution`, `DecisionRequest`, `ActionRequest`). None are re-exported via `__init__.py` — package public API is unchanged. README usage examples and method table remain accurate. No grep matches for new symbols in README. |
| 2. External Attribution | N/A | Task is Brief-driven, no external sources referenced in builder or architect notes. |
| 3. Research Doc | N/A | No research artifact exists for this task; task scope was spec/Brief only. |
| 4. Deletion Detection | N/A | No files deleted. One new file created; no orphaned references. |

### Scratch Cleanup
No `.owlbear/scratch/1851-*` files found — nothing to clean.

[[2026-05-25T02:03:37+02:00]]
## Audit

### Regression Detection
quality-runner full kanban domain: 1417 passed, 0 failed, ruff clean.

### Intent Verification
Changed files: `serve/kanban/src/owlbear_kanban/request_models.py` (new), `tests/test_request_models_1851.py`. Both in kanban domain, matching stated purpose (Pydantic models for structured decision requests). No extraneous scope.

### Architect Quality
Score: 4/5. Six AC lines with specific testable constraints. Minor gaps (timezone-less datetime edge case, union wrapper naming ambiguity) caught by reviewer and resolved via architect re-review. Challenger was engaged effectively.

### Commit Integrity
- `b17ffad1` — test: add failing tests for request models (#1851, test-writer)
- `026067aa` — feat: add structured request models (#1851, builder)
- `dd942f50` — test: add retry tests for timezone-less created_at (#1851, test-writer)

All deliverables committed before advancement. No orphaned or unauthorized changes.

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
