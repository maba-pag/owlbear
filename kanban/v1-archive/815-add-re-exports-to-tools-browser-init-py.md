---
id: 815
title: Add re-exports to tools/browser/__init__.py
status: archived
priority: nice-to-have
created: 2026-03-15T05:11:39.50715+01:00
updated: 2026-03-22T18:59:30.3424505+01:00
started: 2026-03-16T14:43:32.6599493+01:00
completed: 2026-03-16T14:43:32.6599493+01:00
tags:
    - architecture
    - scope:core
depends_on:
    - 813
class: standard
---

Add eager re-exports for browser types to tools/browser/__init__.py. See docs/research/init-re-exports.md section 3.2. Skip internal extractors/utils. Exclude WebCrawler (chains to optional trafilatura dep at module level — see Research section).

## AC

- [ ] tools/browser/__init__.py re-exports: BrowserToolset, BrowserConfig, BrowserManager, URLSafetyGuard, BlockedURLError, CrawlConfig
- [ ] __all__ tuple defined (6 entries)
- [ ] No circular import (test: python -c 'import owlbear.tools.browser')
- [ ] Ruff clean, all tests pass
- [ ] WebCrawler intentionally excluded (optional trafilatura dep)

[[2026-03-15]] Sun 05:52

## Research

Research validated from parent doc: docs/research/init-re-exports.md (section 3.2).

### Research Checklist

1. __Theoretical validity:__ Sound. Eager re-exports with __all__ is standard Python.
2. __Prior art:__ core/__init__.py (15 re-exports), PydanticAI. Both use from-import + __all__.
3. __Technical feasibility:__ 6 of 7 types import cleanly. __WebCrawler risk:__ crawler.py imports trafilatura at module level (optional [crawl] extra). Re-exporting it would break 'import owlbear.tools.browser' without [crawl].
4. __Architecture fit:__ Matches existing core/__init__.py pattern. Additive change.
5. __Implementation approach:__ Copy core/__init__.py pattern. Exclude WebCrawler (or defer trafilatura first).

### Refined AC

Exclude WebCrawler from re-exports. Keep 6 exports: BrowserToolset, BrowserConfig, BrowserManager, URLSafetyGuard, BlockedURLError, CrawlConfig. Consumers needing WebCrawler use TYPE_CHECKING guard already.

[[2026-03-15]] Sun 06:06

## Architecture Review
__Verdict:__ BLOCK -> ideation

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| tools/browser/__init__.py re-exports 6 types | Technically sound, matches core/__init__.py pattern | Blocked by unresolved decision |
| __all__ tuple (6 entries) | Standard Python, no issue | Blocked by unresolved decision |
| No circular import test | Good, verifiable | N/A |
| Ruff clean, all tests pass | Standard gate | N/A |
| WebCrawler excluded (optional trafilatura) | Correctly identified risk | N/A |

### Architecture Notes
__Blocker: contradictory research, unresolved decision.__

Dependency #813 is blocked in ideation with: 'Contradictory research: init-reexports.md says NO (.85), init-re-exports.md says YES (.90).'

The two research docs reach opposite conclusions:

- docs/research/init-re-exports.md (.90): YES, add re-exports (matches core/__init__.py, PydanticAI)
- docs/research/init-reexports.md (.85): NO, document as intentional (YAGNI/KISS, 0/66 imports use re-exports, app not library)

This task cannot be approved until the fundamental question is resolved: should re-exports be added to non-library packages?

No decision request has been filed at docs/decisions/pending/. One is needed.

### Dependencies

- #813 (auth/planning/projects/providers/safety re-exports): BLOCKED in ideation  contradictory research
- No preceding test task exists for #815

### Changes Made

- kanban-md edit 815 --status ideation --block 'reason' --release

[[2026-03-15]] Sun 09:48

## Research (2026-03-15, researcher)

Doc: docs/research/browser-re-exports.md

Findings:

- 0/167 browser imports use package-level paths (0 src, 0 tests). 100% deep.
- WebCrawler optional-dep risk confirmed (trafilatura module-level import).
- #815 shares #813 fundamental blocker: no independent justification exists.
- Recommendation (.90): do not proceed. Close as won't-do if decision = Option A.
- No new follow-up tasks needed (decision request already covers this).

[[2026-03-15]] Sun 14:00
## Research (2026-03-15, researcher -- decision request filed)
Doc: docs/research/browser-re-exports.md (valid). Decision request filed: docs/decisions/pending/813-re-export-feature-gate.md. 0/167 confirmed. .95 conf Option A. No new tasks.

[[2026-03-16]] Mon 12:36
## Research (2026-03-16, researcher -- closure)
Decision resolved: docs/decisions/resolved/813-re-export-feature-gate.md
Option A approved: do NOT add re-exports. 0/167 browser imports use package-level paths. Closing as won't-do.

[[2026-03-16]] Mon 14:43
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| re-exports 6 types | Wont-do: __init__.py empty stub, no changes | PASS (wont-do) |
| __all__ tuple | No __all__ defined, intentional per decision | PASS (wont-do) |
| No circular import | Python import test: OK | PASS |
| Ruff clean + tests | browser/ ruff clean; 148 browser tests passed | PASS |
| WebCrawler excluded | __init__.py unchanged | PASS |

### Test Results
- pytest (browser): 148 passed
- ruff: clean
- Full suite has pre-existing circular import from #814 (unrelated to #815)

### Wont-Do Verification
- Decision: docs/decisions/resolved/813-re-export-feature-gate.md (approved: true, Option A)
- 0/167 browser imports use package-level paths

### Confidence: 1.0
### Action: archive

### Upstream Quality Gap
docs/research/browser-re-exports.md was untracked; committed by auditor.
