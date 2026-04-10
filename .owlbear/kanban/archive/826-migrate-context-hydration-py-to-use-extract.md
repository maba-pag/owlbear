---
id: 826
title: Migrate context_hydration.py to use extract_content from content_extractor
status: backlog
priority: nice-to-have
created: 2026-03-15T09:43:03.371593+01:00
updated: 2026-03-26T16:16:33.4500689+01:00
tags:
    - dry
    - scope:core
    - phase-9
blocked: true
block_reason: 'Superseded by #873 chain (#868/#869/#876). Migration already implemented in commit b32ef27. Archive candidate.'
class: standard
---

Replace trafilatura.extract(resp.text, ...) in context_hydration.py L117-123 with extract_content(resp.text, url=url).text. Remove lazy import trafilatura. The wrap_web_content logic duplicated here can also be centralized. See docs/research/centralize-trafilatura.md. AC: (1) context_hydration.py no longer imports trafilatura directly, (2) uses extract_content from content_extractor, (3) existing tests pass.

[[2026-03-20]] Fri 13:15

## Research

- Research doc: docs/research/context-hydration-extract-content.md
- External attribution updated: docs/sources/overview.md
- Key finding: fetch_url() duplicates the same trafilatura.extract(..., output_format=markdown, include_links=True, url=url) call already wrapped by extract_content().
- Key finding: Unlike web_search, fetch_url() has no raw-HTML fallback. The migration should use extract_content(resp.text, url=url).text directly and delete the local wrap_web_content block.
- Key finding: Missing-trafilatura behavior stays equivalent: failure still occurs on first use, now via extract_content() instead of a local import.
- Key finding: Test blast radius is 4 direct trafilatura mocks in tests/test_context_hydration.py and 5 fetch-url-related mocks in tests/test_content_safety_integration.py.
- Follow-up created: #864 - Update context_hydration tests to mock extract_content instead of trafilatura
- No extra architecture split needed: #826 itself remains the implementation task.
- Command executed: kanban\kanban-md.exe create Update context_hydration tests to mock extract_content instead of trafilatura -> #864

[[2026-03-20]] Fri 13:44

## Architecture Review

**Verdict:** BLOCK

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| (1) context_hydration.py no longer imports trafilatura directly | Verifiable, but not sufficient to justify the migration | Keep as intent only |
| (2) uses extract_content from content_extractor | Invalid as written: src/owlbear/core/context_hydration.py would need to import src/owlbear/tools/browser/content_extractor.py, violating the core -> tools dependency rule | Reject current wording |
| (3) existing tests pass | Not actionable yet: paired RED task #864 exists but is still in ideation and no predecessor dependency is defined on #826 | Reject current wording |

### Architecture Notes

- src/owlbear/core/context_hydration.py is in the core layer.
- src/owlbear/tools/browser/content_extractor.py is in the tools layer.
- Per architecture-standards, core/ never imports from tools/. Directly following the researched recommendation would introduce a new upward dependency.
- The accepted web_search precedent (#824) is not equivalent: src/owlbear/tools/web_search.py and src/owlbear/tools/browser/content_extractor.py are both in tools/, so that migration stayed within one layer.
- The sibling bookmark_pipeline migration (#825) is still in ideation, which reinforces that lower-layer callers have not yet been architecturally resolved.
- Research is insufficient because it proves behavioral equivalence but does not evaluate the layering consequence or define a lower-layer shared abstraction/protocol for non-tools callers.

### Changes Made

- Appended architecture review notes
- Prepared task for backlog rejection to ideation
- Recorded the need for re-research on a legal lower-layer extraction abstraction

### Dependencies

- Verified: #864 exists as the RED task candidate, but it is still ideation and cannot satisfy TDD readiness for this implementation task
- Verified: no legal lower-layer shared extraction helper currently exists for core callers

[[2026-03-26]] Thu 16:16
## Research (Re-research)
- Research doc: docs/research/context-hydration-migration-already-implemented.md
- Finding (.97): Migration already implemented via successor chain #868/#869/#876/#873.
- Evidence: commit b32ef27 replaced direct trafilatura.extract with extract_markdown from leaf helper.
- Evidence: context_hydration.py has zero direct trafilatura imports; uses owlbear.web_extract.extract_markdown.
- Evidence: 78/79 tests pass; 1 pre-existing seam-contract mismatch unrelated to migration.
- Lower-layer helper resolved: owlbear.web_extract.extract_markdown (created by #868, archived).
- #826 is superseded by #873 (correctly-scoped GREEN successor). No new implementation needed.
- Recommendation: archive #826 as superseded, advance #873 through auditor verification.
- External attribution updated: docs/sources/overview.md
