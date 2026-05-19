---
id: 875
title: Refactor content_extractor to reuse web_extract.extract_markdown
status: archived
priority: nice-to-have
created: 2026-03-20T14:58:50.167833+01:00
updated: 2026-03-25T19:58:34.9296782+01:00
started: 2026-03-25T19:58:34.2595692+01:00
completed: 2026-03-25T19:58:34.9296782+01:00
tags:
    - dry
    - type:build
    - scope:core
    - phase-9
depends_on:
    - 868
    - 881
class: standard
---

After #868, make src/owlbear/tools/browser/content_extractor.py delegate its raw markdown text extraction to owlbear.web_extract.extract_markdown while preserving extract_metadata, ExtractionResult, and wrap_web_content behavior. Source: docs/research/leaf-markdown-extraction-helper.md. AC: (1) content_extractor no longer duplicates the raw trafilatura.extract markdown/include_links/url call, (2) metadata extraction and wrapping semantics stay unchanged, (3) existing tests in tests/test_content_extractor.py and relevant integration coverage pass, (4) no new upward dependency is introduced.

[[2026-03-24]] Tue 02:55

## Research

- Doc: docs/research/content-extractor-refactor-already-implemented.md

- Finding: All 4 AC items are already satisfied in the current codebase.

- Commit 83eb7a9 (attributed to #881 builder) implemented the delegation: content_extractor.py line 18 imports extract_markdown from owlbear.web_extract, line 83 delegates text = extract_markdown(html, url=url).

- No raw trafilatura.extract call remains for markdown extraction; only trafilatura.extract_metadata is called locally.

- 12 tests pass in tests/test_content_extractor.py including TestFromAC_ExtractMarkdownDelegation.

- Recommendation (.97): close #875 as already-implemented; unblock #881 (its blocking reason no longer applies).

- No new follow-up tasks needed.

[[2026-03-24]] Tue 13:20

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: no raw trafilatura.extract markdown/include_links/url call | SOUND â€” content_extractor.py:82 calls extract_markdown(html, url=url); grep for trafilatura.extract returns only extract_metadata refs | Kept |
| AC2: metadata extraction and wrapping semantics unchanged | SOUND â€” extract_metadata at line 86, wrap_untrusted_content at line 107 remain local | Kept |
| AC3: existing tests pass | SOUND â€” 12 passed in tests/test_content_extractor.py (verified by architect) | Kept |
| AC4: no new upward dependency | SOUND â€” web_extract.py is explicitly a leaf module with no imports from core/tools/agents/memory | Kept |

### Architecture Notes

- Module layering verified: tools/browser/content_extractor.py imports from owlbear.web_extract (leaf module). No upward dependency. Consistent with architecture-standards module layering diagram.
- Pattern consistency: extract_markdown is a thin wrapper around trafilatura.extract with lazy import and error handling. content_extractor delegates the raw call while retaining extract_metadata and wrap_untrusted_content locally. Clean DRY separation.
- Implementation already exists: commit 83eb7a9 (scope breach from #881 builder) already implemented all AC items. 12 tests pass. The builder for this task should verify the existing code rather than re-implement.
- #881 (RED test task) AC5 states tests should fail before #875 is implemented, which is no longer achievable since the implementation is already in HEAD. The test-writer for #881 should adapt accordingly.
- Security surface: no new system boundary introduced. Existing wrap_untrusted_content tagging in content_extractor.py remains intact.

### Changes Made

- Added depends_on #881 for TDD compliance (test task precedes impl task)

### Dependencies

- Verified: #868 (create extract_markdown helper) â€” archived
- Added: #881 (RED test task) â€” currently at todo, architect-approved

[[2026-03-25]] Wed 19:58

## Board Triage (2026-03-25)

Archived as already-implemented: content_extractor.py:18 imports extract_markdown, line 77 delegates. 12/12 tests pass. No work remaining.
