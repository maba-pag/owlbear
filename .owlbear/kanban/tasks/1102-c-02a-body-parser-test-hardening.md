---
id: 1102
title: 'C-02a: body_parser test hardening'
status: in-progress
priority: important
created: 2026-04-22T01:31:44.721688+00:00
updated: 2026-04-22T03:13:25.582230+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

[[2026-04-22]]
## Brief
Follow-up from #1047 review cycles. Reviewer-identified gaps beyond #1047 AC scope.
Parent: #1043 (Brief C). Tags: phase:storage, brief:c, scope:kanban, test, quality.
Depends on: #1047. Priority: nice-to-have.

## Acceptance Criteria

- [ ] Test: EOF-unclosed fenced code block (opening fence, no closing fence) — heading-like lines inside the unclosed fence do NOT create sections, and fence content is preserved in Section.content
- [ ] Test: Tab-indented code block (`\t## Heading-like`) — heading-like lines inside tab-indented code do NOT create sections (currently only space-indented code is tested)
- [ ] Fix: body_parser.py:18 docstring says empty ATX headings may omit the space, but regex at line 19 requires a space — reconcile docstring and regex

## Context
- Module: serve/kanban/src/owlbear_kanban/body_parser.py
- Fence state machine: lines 75-92 (EOF path at loop exit + _flush)
- Tab-indent regex: line 29 (_INDENT_RE)
- ATX docstring/regex: lines 18-19
- Existing test suites: serve/kanban/tests/test_body_parser.py, tests/test_body_parser_1047.py
[[2026-04-22]]
## Architecture Review

### Refined Acceptance Criteria

The original AC is refined below. Downstream agents: use these refined criteria, not the originals.

- [ ] AC-1: Test — EOF-unclosed fenced code block (opening ``` or ~~~ with NO closing fence). Assert: (a) heading-like lines inside the unclosed fence do NOT create new sections, (b) `Section.content` preserves fence opening marker and all interior lines verbatim (exact string equality), (c) `parse_body(render_body(sections)) == sections` round-trip holds. Test both with and without trailing newline.
- [ ] AC-2: Test — Tab-indented code block (`\t## Heading-like`). Assert: (a) heading-like lines inside tab-indented code do NOT create sections, (b) the tab character and full line content are preserved verbatim in `Section.content` (exact string equality). Mirrors existing space-indented test at `serve/kanban/tests/test_body_parser.py:149-154`.
- [ ] AC-3: Fix — `body_parser.py` line 18 comment says "(or end of line for empty heading)". Remove this clause. The regex at line 19 (`^(#{1,6}) (.*)$`) and `parse_body` docstring (line 39: "space required after #") both intentionally require a space. Updated comment: `# ATX heading: 1-6 '#' followed by a space`. This is a comment correction, not a regex change.

### Test Placement

New tests go in `tests/test_body_parser_1102.py` (task-scoped file, following the `tests/test_body_parser_1047.py` pattern).

### Pass-Through Rationale

AC-1 and AC-2 test parser paths that are already correctly implemented (EOF-unclosed fence at body_parser.py:75-92 + loop exit, tab indent via `_INDENT_RE` at line 29). Tests will PASS on current code — this is test hardening, not bug-driven TDD. AC-3 is a comment fix. No RED-phase tests possible.

**Required tags: `test`, `quality`.** (Architect cannot programmatically add tags — `edit_task` tool unavailable. Orchestrator/user: add tags before dispatching to test-writer.)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Three closely related items in one module, all from same reviewer gap analysis |
| Interface clarity | PASS | Refined ACs specify exact equality, round-trip, and verbatim content preservation |
| Dependency correctness | PASS | #1047 code changes already landed. Remaining #1047 pipeline steps (C11 precision test) don't conflict. No hard `depends_on` needed — items are code-independent. |
| Module layering | PASS | Tests import from owlbear_kanban — correct direction |
| TDD compliance | PASS | Task IS the test addition; tagged for pass-through |
| KISS/YAGNI | PASS | Minimal scope — reviewer-identified gaps only |
| Premise challenge | PASS | Valid gaps from #1047 review cycles 2-3 (EOF-unclosed fence, tab-indent, docstring mismatch) |
| Pattern consistency | PASS | Follows TestFromAC_ + TestBuilderDiscovered pattern |
| Security surface | PASS | Pure in-memory string/regex parser, no system boundaries |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: reconsider (0.68)
- Key challenges: (1) AC-3 direction unspecified in original body, (2) pass-through tags missing from metadata, (3) #1047 dependency not formalized, (4) AC-1/AC-2 assertions too loose, (5) EOF variant unspecified
- Architect response: All 5 addressed via AC refinement in this note. AC-1 now requires exact equality + round-trip + both EOF variants. AC-2 requires exact equality + tab preservation. AC-3 specifies direction (update comment, not regex). Tags documented as required (tool limitation prevents programmatic addition). #1047 dependency justified as soft — code already landed, no conflict.
- Override justified: all substantive concerns addressed in refined AC. Code-level risk genuinely low. Confidence post-refinement: 0.88.

### Priority Note
Brief says "nice-to-have" but metadata says "important". These are reviewer-identified gaps that prevented #1047 approval — "important" is justified.

### Verdict: APPROVE
### Action Taken: Approved to todo with refined AC. Tags `test`, `quality` must be added before test-writer dispatch.
[[2026-04-22]]
## Test-Writer Notes
- Non-implementation task (tagged `test`, `quality`) — pass-through per `w-tdd-red` Step 1a.
- Architect pass-through rationale confirmed: AC-1 and AC-2 test paths already correctly implemented; no failing tests possible for existing behavior (test hardening). AC-3 is a source comment fix.
- Builder deliverables: create `tests/test_body_parser_1102.py` with hardening tests for AC-1 and AC-2; apply comment correction to `body_parser.py:18` for AC-3.

**AC coverage (for builder)**
| AC | Tests to write | Notes |
|----|---------------|-------|
| AC-1 | `TestFromAC_EOFUnclosedFence` — backtick/tilde × no-trailing-newline/with-trailing-newline; assert (a) heading-like lines not sections, (b) exact content equality, (c) round-trip | Both ` ``` ` and `~~~` openers; both EOF variants |
| AC-2 | `TestFromAC_TabIndentedCode` — tab-indented heading-like line; assert (a) not a section, (b) `\t` character preserved verbatim in content | Mirrors space-indented test at `serve/kanban/tests/test_body_parser.py:149` |
| AC-3 | No test — comment-only fix in `body_parser.py:18` | Remove "(or end of line for empty heading)" from inline comment |