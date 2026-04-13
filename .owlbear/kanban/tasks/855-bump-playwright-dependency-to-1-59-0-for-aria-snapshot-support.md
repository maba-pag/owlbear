---
id: 855
title: Bump playwright dependency to >=1.59.0 for aria_snapshot support
status: research
priority: important
created: '2026-04-12T14:03:37.182864+00:00'
updated: '2026-04-13T13:43:45.275165+00:00'
tags:
- phase-2
- scope:mcp-browser
parent: 837
depends_on: []
blocked: true
block_reason: 'Playwright Python 1.59.0 not yet published on PyPI (latest: 1.58.0,
  2026-01-30). AC item ''uv lock succeeds'' is infeasible until release.'
claimed_by: null
claimed_at: null
---
Update serve/browser/pyproject.toml playwright dependency from >=1.40.0 to >=1.59.0.

**Source:** .owlbear/research/837-mcp-browser-session-management.md §3f

**Why:** page.aria_snapshot() was added in Playwright v1.59. The snapshot() MCP tool requires this API.

**AC:**
- [ ] serve/browser/pyproject.toml: playwright>=1.59.0
- [ ] uv lock succeeds
- [ ] Existing browser tests still pass
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/855-playwright-dep-bump.md
- Sources: 7 studied, 2 high-relevance (external)
- Finding: `page.aria_snapshot()` confirmed introduced in Playwright v1.59, but **playwright-python 1.59.0 is not yet on PyPI** — latest is 1.58.0 (Jan 30, 2026). Node.js 1.59.1 shipped ~Apr 4; Python typically follows within weeks.
- Recommendation: Block until PyPI publishes v1.59.0 (confidence: .85)
- Alternative: Revise AC to `>=1.49.0` and use `page.locator('body').aria_snapshot()` instead (confidence: .75, requires updating #837 implementation plan + tests)
- No breaking changes between v1.40 and v1.58 affect our codebase
- Decision requests: none (T1 — temporal blocker, not a design decision)
- Follow-up tasks: none needed — task is correctly scoped, just needs unblocking

## Challenge Results
- Challenger: FALLBACK — factual PyPI constraint, not a controversial recommendation
- Confidence in original: .85
- Key challenges: n/a
- Researcher response: n/a