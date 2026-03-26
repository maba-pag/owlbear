---
id: 569
title: Consolidate trafilatura across extras groups
status: archived
priority: someday
created: 2026-03-04T07:39:11.5014884+01:00
updated: 2026-03-22T19:17:45.7094253+01:00
started: 2026-03-07T04:34:58.0499359+01:00
completed: 2026-03-22T19:17:45.7094253+01:00
tags:
    - audit
    - config
    - deps
blocked: true
block_reason: 'Superseded by archived #829; no remaining executable work for builder flow.'
class: standard
---

F-08: trafilatura>=2.0.0 in both crawl and search extras. bookmark_pipeline also needs it but doesnt declare. Consider shared web extra or document which extra provides it. See docs/config-dependency-audit.md.

Research complete -- see docs/research/consolidate-trafilatura-extras.md. Finding: duplication is intentional (1 line, follows httpx/pydantic idiom). After #537 (centralize trafilatura calls), bookmark_pipeline will no longer import trafilatura directly. No structural changes to extras needed. One follow-up task: add clarifying comments to pyproject.toml and update import guard message.

## AC

- [x] Research doc at docs/research/consolidate-trafilatura-extras.md
- [x] Finding: duplication intentional, no structural changes needed
- [x] Follow-up task created (clarifying comments + import guard)

[[2026-03-21]] Sat 13:54
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Research doc at docs/research/consolidate-trafilatura-extras.md | Present and sufficient as historical research evidence. | Keep as traceability only. |
| Finding: duplication intentional, no structural changes needed | Validated by the live repo state: pyproject.toml already carries the intentional-duplication comments and content_extractor.py already advertises both extras through follow-up #829. | Keep as a concluded finding, not as new builder work. |
| Follow-up task created (clarifying comments + import guard) | Already satisfied and superseded as executable work: #829 exists and is archived. No remaining implementation contract is attached to #569 itself. | Do not route #569 into test-writer/builder flow. |

### Architecture Notes
- #569 is a research/traceability card, not a valid backlog implementation contract.
- The only concrete changes recommended by the research were captured separately in #829, and the repository already reflects them in pyproject.toml and src/owlbear/tools/browser/content_extractor.py.
- TDD gate: not applicable to #569 because there is no remaining implementation surface to pair with a RED task. Approving this card would create a builder handoff with no executable scope.
- Related trafilatura consolidation work belongs to other tasks (#537 is already blocked as stale, with successor chain tracked elsewhere) and should not be revived through #569.

### Changes Made
- Appended this architecture review.
- Returning #569 to ideation with a block reason because the task has no remaining executable work after archived follow-up #829.

### Dependencies
- Verified: #829 archived and implemented the only concrete follow-up from this research.
- Verified: pyproject.toml and src/owlbear/tools/browser/content_extractor.py already match the research recommendation.
- No new dependencies or follow-up tasks required from this review.
