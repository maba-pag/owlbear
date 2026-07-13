---
id: 61
title: Implement voice protocol Pydantic models
status: archived
priority: medium
created: 2026-03-26 19:33:36.008518+01:00
updated: 2026-03-30 03:38:25.619138+02:00
started: 2026-03-30 03:38:25.293551+02:00
completed: 2026-03-30 03:38:25.293551+02:00
tags:
- phase-3
- scope:voice
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Define the NDJSON protocol models for voice addon communication.

## Acceptance Criteria

### Models (all frozen, Literal discriminator on `type` field)

**VoiceOutMessage union (addon to orchestrator):**

- [ ] TranscriptMsg(type: Literal[transcript], text: str, line_idx: int, final: bool) â€” frozen=True
- [ ] PartialMsg(type: Literal[partial], text: str, line_idx: int) â€” frozen=True
- [ ] StatusMsg(type: Literal[status], state: VoiceState) â€” frozen=True
- [ ] ErrorMsg(type: Literal[error], code: str, message: str) â€” frozen=True

**VoiceInMessage union (orchestrator to addon):**

- [ ] SpeakMsg(type: Literal[speak], text: str, interrupt: bool) â€” frozen=True, interrupt is required (no default)
- [ ] ConfigMsg(type: Literal[config], settings: dict[str, Any]) â€” frozen=True
- [ ] ShutdownMsg(type: Literal[shutdown]) â€” frozen=True, no additional fields

### Type aliases and adapters

- [ ] VoiceState = Literal[ready, listening, speaking, idle, shutdown]
- [ ] VoiceOutMessage = Annotated[Union of 4 out-models, Field(discriminator=type)]
- [ ] VoiceInMessage = Annotated[Union of 3 in-models, Field(discriminator=type)]
- [ ] out_adapter: TypeAdapter[VoiceOutMessage] at module level (public name)
- [ ] in_adapter: TypeAdapter[VoiceInMessage] at module level (public name)

### Serialization contract

- [ ] Each model serializable via model_dump_json() (returns str)
- [ ] Deserialization via out_adapter.validate_json() / in_adapter.validate_json()
- [ ] Unknown type values rejected with ValidationError
- [ ] Missing required fields rejected with ValidationError

### File location

- [ ] packages/orchestrator/src/owlbear/voice/__init__.py (empty or minimal)
- [ ] packages/orchestrator/src/owlbear/voice/protocol.py

### Patterns to follow

- ConfigDict(frozen=True) per model (see packages/knowledge/src/owlbear_knowledge/models.py)
- Module-level TypeAdapter instances (see v1/src/owlbear/memory/session.py)
- No base class hierarchy â€” 7 flat models with shared type field (KISS)

## Test task
#112 (in-progress) â€” tests at tests/test_voice_protocol.py (25 tests)

## Context
See docs/research/voice-protocol-models.md and docs/research/voice-stdio-protocol.md S3.3, S3.7

## Research
Validated implementation approach (.90 confidence). See docs/research/voice-protocol-models.md.

Key findings:
- Pattern confirmed: Pydantic Literal discriminated unions + module-level TypeAdapter instances. Matches MCP SDK and v1 codebase patterns.
- Dependency gap: Added depends_on #7 (monorepo skeleton must exist for package structure).
- Location: packages/orchestrator/src/owlbear/voice/protocol.py (owlbear namespace in orchestrator package).
- model_dump_json() returns str (ready for stdin.write). TypeAdapter.validate_json() accepts str or bytes.
- All 7 message types are pure data models. No mocks needed for tests.

[[2026-03-29]] Sun 14:56
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| VoiceOutMessage union (4 models) | Original vague, now has exact fields per model | Refined |
| VoiceInMessage union (3 models) | Original vague, now has exact fields, interrupt required | Refined |
| Serialize via model_dump_json() | Correct, matches existing patterns | Keep |
| Location src/owlbear/voice/protocol.py | Ambiguous path, clarified to packages/orchestrator/src/owlbear/voice/protocol.py | Refined |
| Unit tests AC line | Belongs in test task #112, removed from impl AC | Removed |
| frozen=True | Added per researcher recommendation, matches knowledge/models.py | Added |
| Module-level adapters | Added: out_adapter, in_adapter (public names per test expectations) | Added |
| VoiceState type alias | Added per researcher recommendation | Added |
| __init__.py for voice subpackage | Added to ensure owlbear.voice is importable | Added |
| Validation error behavior | Added: unknown type and missing field rejection | Added |

### Architecture Notes
- Single domain: scope:voice. Pure Pydantic models, no layer violations.
- Location in packages/orchestrator/src/owlbear/voice/ is correct: orchestrator ships the owlbear namespace (confirmed in pyproject.toml wheel config). Voice subprocess can import these models if it depends on the orchestrator package.
- Pattern consistency: ConfigDict(frozen=True) matches packages/knowledge/src/owlbear_knowledge/models.py. Module-level TypeAdapter matches v1/src/owlbear/memory/session.py.
- No base class hierarchy (KISS). 7 flat models with shared type field.
- No security surface: pure data models with no I/O, no user input, no external APIs.
- Adapter names are public (out_adapter, in_adapter) per existing test expectations in tests/test_voice_protocol.py.

### Dependencies
- Verified: #7 (monorepo skeleton) archived
- Verified: #112 (test task) in-progress, tests written at tests/test_voice_protocol.py (25 tests)
- TDD ordering correct: #112 precedes #61

### Changes Made
- Rewrote AC body with exact model fields, type aliases, adapter names, file paths, pattern references
- Removed test AC line (covered by #112)
- Added __init__.py requirement for voice subpackage
- Added validation error behavior AC lines

[[2026-03-29]] Sun 15:20
## Test-Writer Notes
- Test file: tests/test_voice_protocol.py
- Written under companion task #112 (test-writer pass-through)
- Classes: TestFromAC_RoundTrip, TestFromAC_DiscriminatorField, TestFromAC_TypeSelect, TestFromAC_UnknownTypeRejection, TestFromAC_MissingRequiredField
- Tests per category: happy 7 (round-trip), edge 7 (discriminator), happy 7 (type-select), error 2 (unknown-type), error 2 (missing-field)
- Total: 25 tests, all FAIL (ImportError: No module named 'owlbear.voice') checked
- ruff: clean
- AC coverage: all 16 AC lines covered across 5 test classes

[[2026-03-29]] Sun 15:55
## Builder Notes
- Files changed: packages/orchestrator/src/owlbear/voice/__init__.py, packages/orchestrator/src/owlbear/voice/protocol.py
- Tests: 25 passed, coverage 100% on voice/protocol.py
- Lint: ruff clean
- Evidence: uv run pytest tests/test_voice_protocol.py -- 25 passed in 0.17s
- Fixes applied: Replaced Union[] with X | Y operator syntax per ruff UP007

[[2026-03-29]] Sun 16:08
## Review Evidence
See docs/scratch/61-reviewer.md for full evidence.

[[2026-03-29]] Sun 19:08
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL — frozen=True AC had no behavioral tests (all 7 models marked LAX)
- Added: 7 new tests in TestFromAC_FrozenImmutability (one per model, each attempts attribute mutation and expects ValidationError)
- Preserved: 25 existing tests — all PASS
- New tests: PASS (frozen=True already implemented by builder; tests enforce the contract)
- ruff: clean
- Total now: 32 tests

[[2026-03-30]] Mon 03:20
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | New submodule in orchestrator; directory table unchanged |
| 2 | Docstrings | Yes | Pass | All 7 model classes + module have docstrings in protocol.py |
| 3 | sources/overview.md | Yes | Pass | Task #61 section present (line 2237) with 4 source rows |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/voice-protocol-models.md exists, linked in task body |

### Files Updated
- None

### Scratch Files Cleaned
- Deleted docs/scratch/61-reviewer.md

[[2026-03-30]] Mon 03:38
## Audit
### AC Verification
All 16 AC items verified. See auditor spot-check:
- 7 models: all present with correct fields and frozen=True (protocol.py L22-L89)
- VoiceState alias: correct 5-state Literal (L14)
- Discriminated unions: both correct (L95-L103)
- Module-level adapters: out_adapter, in_adapter (L109-L110)
- Serialization/deserialization: 14 round-trip + type-select tests
- Validation rejection: 4 tests (unknown type + missing field)
- __init__.py: exists, minimal

### Test Results
- pytest (task-specific): 32 passed, 0 failed
- pytest (full suite, excl. 3 unrelated collection errors): 874 passed, 140 failed (all pre-existing)
- ruff: 2 errors in unrelated test_necessity_check_196.py

### Architect Quality
Score: 5/5. AC specific, complete, led to clean implementation. No builder improvisation needed.

### Reviewer Evidence
Detailed review conducted. Caught frozen=True coverage gap, triggered retry that added 7 immutability tests. Pipeline worked as designed.

### Commits Verified
- `e106554` test: add failing tests (#61, test-writer)
- `6464ccf` feat: implement voice protocol models (#61, builder)
- `90f7f5a` feat: add frozen immutability tests (#61, builder)

### Confidence: .97
### Action: archive
