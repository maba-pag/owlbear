---
id: 684
title: 'Research: Playwright browser integration for agents'
status: done
priority: nice-to-have
created: 2026-04-08T19:18:22.1617576+02:00
updated: 2026-04-09T02:02:50.0379966+02:00
tags:
    - scope:tools
    - ' type:research'
    - ' source:analysis'
claimed_by: cliff-nova
claimed_at: 2026-04-09T02:02:50.0379966+02:00
class: standard
---

## Context

v1 had a full Playwright browser management suite:
- `BrowserManager` — launch/connect via CDP (Chrome DevTools Protocol)
- Browser actions — navigate, click, type, extract content
- Content guards and safety filters
- Crawler (BFS with depth/page limits, robots.txt, rate limiting)
- Screenshot capture from browser sessions
- CLI commands: `bearclaw browser start [--port 9222]`, `stop`, `status`

v2 has none of this. The knowledge engine has dead `SourceType.CRAWL` stubs but no actual crawler handler. No agent can programmatically browse or capture web page state.

## Research Questions

1. **What use cases need browser integration?**
   - Knowledge ingestion from web pages (beyond `fetch_webpage`)
   - Visual verification / screenshot capture
   - Interactive web application testing
   - Authenticated page access (corporate intranets)

2. **What's the right scope?**
   - Option A: Minimal — just add a `capture_screenshot(url)` tool
   - Option B: Read-only — navigate + extract content + screenshot (no mutations)
   - Option C: Full — v1-equivalent BrowserManager with CDP control
   - Option D: MCP server — expose as owlbear-browser MCP with tool surface

3. **Integration with existing infrastructure?**
   - Could wire into knowledge engine's dead crawl handler
   - Could become standalone MCP server
   - Corporate proxy/auth considerations (Edge CDP on Windows)

4. **Dependencies** — Playwright already in v2's dependency tree? What's the install footprint?

## Acceptance Criteria

- [ ] AC1: Use case inventory with priority assessment
- [ ] AC2: Evaluate scope options against use cases
- [ ] AC3: Assess Playwright dependency and install impact
- [ ] AC4: Recommendation with follow-up implementation task(s)

[[2026-04-08]] Wed 21:31
## Research
- Research doc: .owlbear/research/playwright-browser-integration-v2.md
- Sources: 6 studied, 3 high-relevance (v1 browser module .95, prior research #264 .90, v2 knowledge engine .85)
- Recommendation: Defer implementation — no current v2 workflow requires browser integration. When demand emerges, implement Option B (read-only MCP server `serve/mcp-browser/`) with navigate, read_text, screenshot, snapshot tools ported from v1. (confidence: .75)
- Key findings: (1) Playwright not in v2 deps, only v1 optional extra; (2) v2 uses MCP servers not FunctionToolsets — natural fit is new MCP server; (3) Prior research #264 confirmed keep-custom for browser module; (4) Dead SourceType.CRAWL stubs exist but no handler; (5) High-priority use case (static page ingestion) already covered by httpx-based URL intake
- Follow-up tasks created: #696 (document or remove dead SourceType.CRAWL stubs)
- Decision requests: none — T1 autonomous (deferral recommendation, no new capability introduced)

[[2026-04-08]] Wed 21:54
## Architecture Review

### AC Assessment

| AC | Status | Evidence |
|----|--------|----------|
| AC1: Use case inventory with priority assessment | MET | Research doc §3.1 — 6 use cases ranked, high-priority (static pages) already served by httpx |
| AC2: Evaluate scope options against use cases | MET | Research doc §3.2 — 4 options compared across 8 criteria |
| AC3: Assess Playwright dependency and install impact | MET | Research doc §3.3 — ~5 MB pip + 300-500 MB browser binaries, not in v2 deps |
| AC4: Recommendation with follow-up tasks | MET | Defer (YAGNI), Option B when demand emerges. Follow-up #696 created (dead CRAWL stubs) |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One research question fully scoped |
| Interface clarity | N/A | Research deliverable, no code interface |
| Dependency correctness | PASS | No task dependencies |
| Module layering | N/A | Research task |
| TDD compliance | N/A | Research task — pass-through tag `type:research` present |
| KISS/YAGNI | PASS | Defer recommendation aligns with YAGNI |
| Premise challenge | PASS | Reasonable gap to investigate — v1 had browser suite, v2 has none |
| Pattern consistency | PASS | Recommendation fits v2 MCP server pattern (`serve/mcp-browser/`) |
| Security surface | N/A | No implementation |
| Single domain | PASS | Tools/browser domain only |

### Codebase Verification

- Confirmed dead `SourceType.CRAWL` stub in `serve/knowledge/src/owlbear_knowledge/refresh.py:100`
- Verified Playwright absent from v2 `pyproject.toml` dependency tree
- Follow-up #696 exists at `research` status with appropriate AC

### Challenge Results
- Challenger: FALLBACK — challenger agent unavailable; defer recommendation is uncontroversial (no new capability introduced, YAGNI-aligned)
- Architect response: Proceeded without challenge

### Verdict: APPROVE
### Action Taken: Advanced to todo — research complete, all AC met, follow-up #696 tracks dead stubs

[[2026-04-08]] Wed 22:38
## Test-Writer Notes
- Non-implementation task (tagged type:research) — no tests applicable.
- Passing through to builder.

[[2026-04-08]] Wed 23:21
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-04-09]] Thu 00:24
## Review Evidence

### Task Type
`type:research` — no code changes, no tests applicable. Test-writer and builder correctly passed through.

### Changed Files
None. Deliverable is `.owlbear/research/playwright-browser-integration-v2.md`.

### Tests / Lint / Coverage
N/A — no implementation deliverable.

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: Use case inventory with priority assessment | Research doc §3.1 — 6 use cases in priority table (High/Medium/Low), finding: high-priority use case already covered by httpx-based URL intake | PASS |
| AC2: Evaluate scope options against use cases | Research doc §3.2 — 4 options (Minimal / Read-only / Full v1 / MCP Server) compared across 8+ criteria in matrix | PASS |
| AC3: Playwright dependency and install impact | Research doc §3.3 — `playwright>=1.40.0`, ~5 MB pip package, ~300–500 MB browser binaries, absent from v2 deps tree (verified grep on pyproject.toml) | PASS |
| AC4: Recommendation with follow-up tasks | Research doc §4 — defer (YAGNI), Option B when demand emerges (.75 confidence). Follow-up #696 exists at `in-progress` status (verified via show_task) | PASS |

### Codebase Spot-Checks (Independent Verification)
- Dead `SourceType.CRAWL` stub confirmed at `serve/knowledge/src/owlbear_knowledge/refresh.py:100` — matches architecture reviewer's claim
- Task #696 verified as created, with its own research doc and downstream implementation task #703

### Deductions
None.

### Verdict
Confidence: .97 → PASS

[[2026-04-09]] Thu 01:09
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | `type:research` — recommendation deferred, no implementation, no behavior change |
| 2 | Module docstrings | No | N/A | No Python files created or modified |
| 3 | External attribution → sources/overview.md | Yes | PASS | Section "Playwright Browser Integration for v2 (Task #684)" already present at line 26 — Playwright PyPI and prior research #264 rows attributed |
| 4 | CLI changes → README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc exists and linked | Yes | PASS | `.owlbear/research/playwright-browser-integration-v2.md` exists; task body references it; follow-up #696 created |

**Files updated:** None — all docs already in order.

**Scratch files:** No `.owlbear/scratch/684-*` files found.

**Verdict:** PASS — docs gate clean.
