---
id: 864
title: Update context_hydration tests to mock extract_content instead of trafilatura
status: archived
priority: nice-to-have
created: 2026-03-20T13:12:36.5414148+01:00
updated: 2026-03-22T19:17:56.5670117+01:00
started: 2026-03-22T19:17:56.5670117+01:00
completed: 2026-03-22T19:17:56.5670117+01:00
tags:
    - test
    - type:test
    - scope:core
    - phase-9
    - dry
blocked: true
block_reason: 'Superseded by #869: current AC assumes illegal core->tools extract_content seam; review #868 then use extract_markdown-based RED task instead.'
class: standard
---

TDD RED phase for #826. Update fetch_url-related tests in tests/test_context_hydration.py and tests/test_content_safety_integration.py that currently patch trafilatura via sys.modules to patch owlbear.core.context_hydration.extract_content instead. Source: docs/research/context-hydration-extract-content.md. AC: (1) 4 trafilatura mocks in tests/test_context_hydration.py are replaced with extract_content or ExtractionResult-based mocks, (2) 5 fetch_url-related trafilatura mocks in tests/test_content_safety_integration.py are replaced likewise, (3) wrapping assertions are preserved by controlling ExtractionResult.text values, (4) scoped tests pass.

[[2026-03-20]] Fri 14:00

## Research

- Research doc: docs/research/context-hydration-extract-markdown-test-seam.md
- External attribution updated: docs/sources/overview.md
- Key finding: #864 is stale as written. `context_hydration.py` cannot legally import `tools.browser.content_extractor.extract_content`; #826 was already architect-blocked for the resulting core -> tools dependency.
- Key finding: official mocking guidance says to patch the name used by the module under test, not the original library or a guessed future symbol.
- Key finding: after #868 lands, the correct RED seam is `owlbear.core.context_hydration.extract_markdown`; helper mocks can return raw markdown and preserve the existing wrapping assertions.
- Existing prerequisite: #868 - Create leaf markdown extraction helper for cross-layer callers
- Follow-up created: #869 - Update context_hydration tests to mock extract_markdown instead of trafilatura
- Recommendation: architect should treat #869 as the valid RED task and close or supersede #864.
- Command executed: kanban\kanban-md.exe create Update context_hydration tests to mock extract_markdown instead of trafilatura -> #869

[[2026-03-20]] Fri 14:33

## Architecture Review

**Verdict:** BLOCK

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| (1) 4 trafilatura mocks in tests/test_context_hydration.py are replaced with extract_content or ExtractionResult-based mocks | Invalid seam: src/owlbear/core/context_hydration.py is in core and cannot legally import tools.browser.content_extractor.extract_content. | Reject current wording; superseded by #869 after #868. |
| (2) 5 fetch_url-related trafilatura mocks in tests/test_content_safety_integration.py are replaced likewise | Same invalid seam for the fetch_url integration tests. | Reject current wording; superseded by #869 after #868. |
| (3) wrapping assertions are preserved by controlling ExtractionResult.text values | Incorrect abstraction: fetch_url() still owns wrapping locally, so raw helper-return mocks are sufficient and ExtractionResult is unnecessary. | Rewrite in successor task to use raw markdown returns. |
| (4) scoped tests pass | Verifiable, but premature because the legal helper seam in #868 does not exist yet and the corrected RED task #869 is still in ideation. | Keep intent only; do not advance this task. |

### Architecture Notes

- src/owlbear/core/context_hydration.py currently lazy-imports trafilatura inside fetch_url() and performs wrapping locally after extraction.
- tests/test_context_hydration.py still contains 4 sys.modules trafilatura patches, and tests/test_content_safety_integration.py still contains 5 fetch_url-related sys.modules patches.
- Changing this test seam to owlbear.core.context_hydration.extract_content would require a core -> tools import, which violates the architecture-standards layer rule.
- The legal seam is the leaf helper proposed in #868. Task #869 already captures the corrected RED work: patch owlbear.core.context_hydration.extract_markdown after that prerequisite exists.
- Single-domain is still core test-seam work, but this specific backlog task is stale and must not move to todo.

### Changes Made

- Claimed #864 for architecture review.
- Verified the current extraction seam in src/owlbear/core/context_hydration.py.
- Verified the affected sys.modules patches in tests/test_context_hydration.py and tests/test_content_safety_integration.py.
- Checked related tasks #826, #868, and #869 to confirm the blocked parent, missing prerequisite, and corrected successor task.

### Dependencies

- Verified missing prerequisite: #868 is still in ideation.
- Verified successor RED task: #869 exists in ideation.
- Verified parent implementation task #826 is already architect-blocked for the same layer violation.
