---
id: 184
title: Create v2 ErrorJournal module with append-only JSONL persistence
status: todo
priority: nice-to-have
created: 2026-03-29T20:23:15.50196+02:00
updated: 2026-03-30T10:20:48.4316832+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 189
blocked: true
block_reason: 'TestFromAC interface contradiction: cannot satisfy both TestFromAC_ErrorJournalLog (positional log(entry) must work) and TestFromAC_ErrorJournalLogV2 (positional log(entry) must raise TypeError) simultaneously. Test-writer must reconcile.'
class: standard
---

## Objective
Port ErrorJournal to v2 as a standalone module with inline JSONL persistence.

## AC
- [ ] ErrorEntry(BaseModel) with ConfigDict(frozen=True) and fields: timestamp (str, ISO-8601), category (str), method (str), message (str), session_id (str)
- [ ] Module-level TypeAdapter[ErrorEntry] instance (create once, reuse in log/load)
- [ ] ErrorJournal.__init__(self, path: Path, *, max_entries: int = 5000) stores file path and rotation limit; does not create file eagerly
- [ ] ErrorJournal.log(self, *, category: str, method: str, message: str, session_id: str) -> None appends single JSONL line with auto-generated ISO-8601 timestamp
- [ ] ErrorJournal.load(self) -> list[ErrorEntry] reads all entries; returns [] if file missing or empty
- [ ] Rotation: after log(), if entry count exceeds max_entries, load all, keep most recent max_entries, rewrite file
- [ ] No JsonlStore[T] base class (inline JSONL persistence, YAGNI)
- [ ] File at packages/orchestrator/src/owlbear_orchestrator/error_journal.py
- [ ] All tests from #189 pass (GREEN)

Blocks #148. See docs/research/errorjournal-acpclient-wiring.md and docs/research/v2-errorjournal-module.md for reference.

[[2026-03-29]] Sun 20:55
## Architecture Review
**Verdict:** APPROVED (after refinement)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| ErrorEntry model | Was missing frozen + field types | Refined: added ConfigDict(frozen=True), explicit str types, ISO-8601 |
| TypeAdapter | Was not in AC (only in research notes) | Added: module-level TypeAdapter[ErrorEntry] |
| ErrorJournal.__init__ | Signature unspecified | Refined: explicit Path + max_entries=5000 keyword-only |
| log() | Params unspecified | Refined: keyword-only category/method/message/session_id, auto timestamp |
| load() | Return type unspecified | Refined: returns list[ErrorEntry], [] for missing/empty |
| Rotation | Vague 'configurable max' | Refined: via max_entries constructor param, keeps most recent |
| No JsonlStore base | Clear negative constraint | Keep |
| Unit tests in impl AC | TDD violation - bundled tests with impl | Removed: created #189 as TDD RED test task |
| File path | Clear | Keep |
| Tests from #189 pass | New AC line linking GREEN phase | Added |

### Architecture Notes
- Placement at owlbear_orchestrator/error_journal.py is correct: sits beside its consumer acp_client.py (#148)
- Frozen model + TypeAdapter pattern matches voice/protocol.py and knowledge/models.py
- Inline JSONL matches audit log #163 approach (YAGNI, extract JsonlStore[T] when 2nd consumer exists)
- 5 fields align with _ErrorLogger Protocol in wiring research (docs/research/errorjournal-acpclient-wiring.md S3.3)
- No new dependencies: Pydantic available via ACP SDK

### Changes Made
- Rewrote AC: 7 vague lines replaced with 9 precise, signature-level AC lines
- Created #189 (Test: ErrorJournal module) at todo status (TDD RED phase)
- Added depends_on: [189] to #184
- Removed 'Unit tests' AC from impl task (moved to #189)

### Dependencies
- Added: #189 (test task, TDD RED phase) - must complete before #184
- Verified: #148 (wiring) depends on #184 - correct direction

[[2026-03-30]] Mon 05:31
## Test-Writer Notes
- Test file: tests/test_error_journal.py (extended, not new)
- New classes for #184: TestFromAC_ErrorJournalInitV2, TestFromAC_ErrorJournalLogV2
- Tests per category: happy 2, edge 0, error 2, boundary 2
- Total new: 6 tests, all FAIL (TypeError / AssertionError) - existing 20 from #189 still pass
- ruff: clean
- AC coverage:
  AC3 (init keyword-only max_entries=5000): test_default_max_entries_no_kwarg_required, test_max_entries_is_keyword_only
  AC4 (log keyword-only, auto-timestamp): test_log_accepts_keyword_args_no_entry_object, test_log_auto_generates_iso8601_timestamp, test_log_stores_all_four_caller_fields, test_log_rotation_with_keyword_interface
- Note: AC9 (All tests from #189 pass) conflicts with the new log() interface. The #189 tests call log(entry: ErrorEntry) positionally, but #184 AC specifies log(*, category, method, message, session_id). Builder must reconcile this in GREEN phase.

[[2026-03-30]] Mon 05:31
## Test-Writer Notes
- Test file: tests/test_error_journal.py (extended, not new)
- New classes for #184: TestFromAC_ErrorJournalInitV2, TestFromAC_ErrorJournalLogV2
- Tests per category: happy 2, edge 0, error 2, boundary 2
- Total new: 6 tests, all FAIL (TypeError / AssertionError) - existing 20 from #189 still pass
- ruff: clean
- AC coverage:
  AC3 (init keyword-only max_entries=5000): test_default_max_entries_no_kwarg_required, test_max_entries_is_keyword_only
  AC4 (log keyword-only, auto-timestamp): test_log_accepts_keyword_args_no_entry_object, test_log_auto_generates_iso8601_timestamp, test_log_stores_all_four_caller_fields, test_log_rotation_with_keyword_interface
- Note: AC9 (All tests from #189 pass) conflicts with the new log() interface. The #189 tests call log(entry: ErrorEntry) positionally, but #184 AC specifies log(*, category, method, message, session_id). Builder must reconcile this in GREEN phase.

[[2026-03-30]] Mon 05:31
## Test-Writer Notes
- Test file: tests/test_error_journal.py (extended, not new)
- New classes for #184: TestFromAC_ErrorJournalInitV2, TestFromAC_ErrorJournalLogV2
- Tests per category: happy 2, edge 0, error 2, boundary 2
- Total new: 6 tests, all FAIL (TypeError / AssertionError) - existing 20 from #189 still pass
- ruff: clean
- AC coverage:
  AC3 (init keyword-only max_entries=5000): test_default_max_entries_no_kwarg_required, test_max_entries_is_keyword_only
  AC4 (log keyword-only, auto-timestamp): test_log_accepts_keyword_args_no_entry_object, test_log_auto_generates_iso8601_timestamp, test_log_stores_all_four_caller_fields, test_log_rotation_with_keyword_interface
- Note: AC9 (All tests from #189 pass) conflicts with the new log() interface. The #189 tests call log(entry: ErrorEntry) positionally, but #184 AC specifies log(*, category, method, message, session_id). Builder must reconcile this in GREEN phase.

[[2026-03-30]] Mon 06:21
## Builder Notes
- Files changed: packages/orchestrator/src/owlbear_orchestrator/error_journal.py
- Tests: 26 passed (20 from #189 + 6 new from #184), coverage 100% on error_journal.py
- Lint: ruff clean
- Evidence: all TestFromAC_ErrorJournalInitV2 and TestFromAC_ErrorJournalLogV2 GREEN
- Fixes applied: max_entries keyword-only with default 5000; log() accepts positional ErrorEntry OR keyword-only category/method/message/session_id with auto-UTC timestamp; UTC import for ruff UP017

[[2026-03-30]] Mon 06:42
## Review Evidence
See docs/scratch/184-reviewer.md for full evidence.

[[2026-03-30]] Mon 06:42
## Review Evidence
See docs/scratch/184-reviewer.md for full evidence.

[[2026-03-30]] Mon 06:42
## Review Evidence
See docs/scratch/184-reviewer.md for full evidence.

[[2026-03-30]] Mon 07:02
## Test-Writer Notes (retry)
- Retry reason: reviewer cited missing test (AC4 strict keyword-only interface unverified)
- Added: 1 new failing test: test_log_positional_entry_object_raises_type_error
- Gap addressed: journal.log(ErrorEntry(...)) must raise TypeError per AC4 (no positional after self)
- Preserved: 26 existing tests (all PASS)
- ruff: clean
- Commit: 806602f

[[2026-03-30]] Mon 10:20
## Builder Notes (BLOCK)
BLOCK: TestFromAC interface contradiction.
- TestFromAC_ErrorJournalLog (x3) and TestFromAC_ErrorJournalRotation (x2) call journal.log(entry) positionally expecting it to work.
- TestFromAC_ErrorJournalLogV2::test_log_positional_entry_object_raises_type_error expects journal.log(entry) positionally to raise TypeError.
- Both are TestFromAC classes - cannot modify either. Contradiction is unsatisfiable.
AC suggestion: test-writer update TestFromAC_ErrorJournalLog + Rotation to use keyword-only interface, OR remove the positional TypeError test and verify AC4 via function signature inspection alone.
