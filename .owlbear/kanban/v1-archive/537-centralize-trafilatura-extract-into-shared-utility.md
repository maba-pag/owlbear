---
id: 537
title: Centralize trafilatura.extract into shared utility
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:42.2569434+01:00
updated: 2026-03-22T19:20:06.624644+01:00
started: 2026-03-07T00:29:37.9506144+01:00
completed: 2026-03-22T19:20:06.624644+01:00
tags:
    - audit
    - dry
    - scope:core
blocked: true
block_reason: 'Superseded by #868/#867/#825; original extract_content-for-all-callers contract is stale and violates memory->tools layering for bookmark_pipeline.'
class: standard
---

DRY-09: trafilatura.extract() wrapped in web_search.py, browser/content_extractor.py, bookmark_pipeline.py with slightly different fallback logic. See docs/software-design-audit.md.

Research complete -- see docs/research/centralize-trafilatura.md. Finding: content_extractor.py already has the correct shared utility (extract_content + ExtractionResult). The other two call sites should import-and-delegate. Two follow-up implementation tasks created.

## AC

- [x] Research doc at docs/research/centralize-trafilatura.md
- [x] Identified shared utility and call sites
- [x] Follow-up implementation tasks created

[[2026-03-21]] Sat 04:35
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Research doc at docs/research/centralize-trafilatura.md | Valid historical research, but no longer sufficient as a builder contract. Current repo state and successor task reviews supersede its main recommendation. | Keep as traceability only; do not route this task into builder flow. |
| Identified shared utility and call sites | Partial and stale. src/owlbear/tools/web_search.py already delegates to extract_content(), but src/owlbear/memory/knowledge/bookmark_pipeline.py cannot legally import src/owlbear/tools/browser/content_extractor.py because memory/ must not depend on tools/. | Reject the original shared-utility contract for all callers; lower-layer reuse must go through the leaf helper seam. |
| Follow-up implementation tasks created | Superseded by a newer, architecture-correct chain. The active contracts are #868 (leaf helper), #867 (RED tests), and #825 (bookmark_pipeline GREEN). | Point future work at #868 -> #867 -> #825 instead of reviving #537. |

### Architecture Notes
- src/owlbear/tools/web_search.py already imports and calls extract_content(...), so half of the original consolidation is already implemented.
- src/owlbear/memory/knowledge/bookmark_pipeline.py still performs direct trafilatura.extract(...), but the architecture-correct reuse target for lower layers is the package-root leaf seam captured by #868 / src/owlbear/web_extract.py, not tools/browser/content_extractor.py.
- Existing architected successor tasks already encode the correct layering: #868 creates the leaf helper, #867 supplies the paired RED tests, and #825 performs the bookmark_pipeline GREEN migration.
- Atomicity: #537 is an umbrella DRY tracker spanning tools/ and memory/ concerns. Its executable work is already decomposed elsewhere.

### Changes Made
- Appended this architecture review.
- Returned #537 to ideation with a block reason because the original contract is stale and partially violates the memory -> tools boundary.

### Dependencies
- Verified: src/owlbear/tools/web_search.py already uses extract_content().
- Verified successor chain: #868 -> #867 -> #825.
- No new follow-up tasks created; existing tasks already carry the executable contract.
