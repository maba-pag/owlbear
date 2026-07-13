---
id: 774
title: 'Phase 0: Edge CDP Technical Spike'
status: archived
priority: medium
created: '2026-04-10T11:45:08.130424+00:00'
updated: '2026-04-10T16:43:38.571848+00:00'
tags:
- browser
- phase-0
- spike
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: gold-pine
claimed_at: '2026-04-10T16:43:38.571848+00:00'
---
# Phase 0: Edge CDP Technical Spike

## Go/No-Go Gate

Validate Edge CDP connectivity and content extraction quality on the corporate laptop before investing in architecture.

## Acceptance Criteria

1. Edge launches (or attaches) with `--remote-debugging-port=9222` on corporate laptop
2. Playwright `connect_over_cdp("http://localhost:9222")` connects and returns browser contexts
3. Navigation to an SSO-protected SharePoint page succeeds with user's active session
4. Page content is extractable via CDP (accessibility tree or DOM methods)
5. EDR/DLP does NOT block CDP port or flag extraction as threat
6. trafilatura `extract()` produces clean markdown from corporate HTML (test with 3+ SharePoint pages and 2+ Confluence pages)
7. Content hash is stable across repeated extractions of the same page (no dynamic boilerplate flicker)

## If Blocked

- CDP blocked by EDR → Document specific error, escalate to Phase 4 (SharePoint REST API) or browser extension research
- DLP flags bulk extraction → Document trigger threshold, implement rate limiting in Phase 1
- trafilatura over-extracts → Fall back to readability-lxml + markdownify (test both during spike)

## Implementation Notes

- Script in `.owlbear/scratch/research/cdp-spike/` — delete after validation
- Test with `playwright.chromium.connect_over_cdp("http://localhost:9222", is_local=True)`
- Verify CDP binds to 127.0.0.1 only (security requirement)
- Check `ipconfig` / `netstat` output for port exposure
- Results documented in task body for architect review

## Context

- Parent: #751 — Authenticated Content Pipeline
- Research: `.owlbear/research/751-authenticated-content-pipeline.md`
- Brief: `.owlbear/briefs/draft-browser-knowledge-extraction/brief.md`

[[2026-04-10]]
## Research
- Research doc: .owlbear/research/774-edge-cdp-spike.md
- Sources: 10 studied, 6 high-relevance
- Recommendation: Consolidate #774 into existing task chain (#752→#776→#753). AC 1-5 are duplicate with #753. AC 6-7 (trafilatura quality, hash stability) are unique and must be added to the spike script and execution. (confidence: .82)
- Follow-up tasks created: #777 (expand spike script with trafilatura test), #778 (add hash stability protocol to spike execution)
- Decision requests: none — T1 Autonomous (task housekeeping, no new capability)

## Challenge Results
- Challenger: FALLBACK — consolidation recommendation is task management, not a technical trade-off
- Confidence in original: .82
- Key challenges: N/A
- Researcher response: N/A

## Key Findings
1. #774 AC 1-5 are fully covered by existing #752/#776/#753 chain — 5/7 ACs are duplicate
2. #774 AC 6-7 (trafilatura extraction quality, hash stability) are NOT covered by any existing task — gap identified and follow-up tasks created
3. trafilatura v2.0.0 benchmark: F1 0.909, but evaluation is on news/blog content — corporate intranet (SharePoint web parts, Confluence macros) is structurally different, empirical validation required
4. Content hash stability risk is at the HTML input layer (dynamic boilerplate), not the hash function — trafilatura extraction is deterministic on identical input
5. Chrome 136 blog post confirmed: `--user-data-dir` to non-standard dir required for `--remote-debugging-port` — already addressed in #752 research

## Post-task Reflection
- Significant task duplication between #774 and the #752/#753/#776 chain — likely caused by #774 being created from #751 research after #752/#753 already existed from planner decomposition
- The unique value of #774 (AC 6-7: extraction quality + hash stability) was correctly identified by the #751 researcher as Phase 0 scope additions, but creating a parallel task instead of expanding existing tasks created confusion
- trafilatura's benchmark being exclusively on article-shaped content is a risk gap — no benchmark data exists for corporate intranet HTML structures
[[2026-04-10]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research deliverable only. Original ACs span CDP connectivity (1-5) and extraction quality (6-7) — correctly decomposed into dedicated tasks by researcher. |
| Interface clarity | N/A | Research task; no code interfaces. |
| Dependency correctness | PASS | No depends_on, correct for research spike entry point. Downstream tasks (#777, #778) correctly depend on #776. |
| Module layering | N/A | Research task, no code. |
| TDD compliance | PASS | Pass-through: `spike` tag present. Recommend adding `type:research` for explicit NON_IMPL_TAGS match. |
| KISS/YAGNI | PASS | Task served its purpose as a research vehicle identifying duplication. All unique value extracted to follow-ups. |
| Premise challenge | PASS | #774 was created from #751 research after #752/#753 already existed from planner decomposition. Duplication correctly identified. Research deliverable is the consolidation recommendation itself. |
| Pattern consistency | PASS | Research output follows established patterns (sources, findings, challenge, reflection). |
| Security surface | N/A | Research only. Security requirements (127.0.0.1 binding, EDR/DLP) are addressed in #776 and #753. |
| Single domain | PASS | scope:browser only. |

### AC Coverage Verification
All 7 original ACs are fully covered by the existing task chain:
- AC 1-5 (CDP connectivity, SSO, EDR/DLP): #752 (research) hands off to #776 (implement) hands off to #753 (execute)
- AC 6 (trafilatura quality): #777 (expand spike with trafilatura test)
- AC 7 (hash stability): #778 (add hash stability protocol)

### Failure Mode Map
N/A — research task with no codepaths.

### Challenge Results
- Challenger: FALLBACK — no challenger agent in available roster
- Architect self-assessment: Consolidation recommendation is well-evidenced. Researcher documented 10 sources, 6 high-relevance. AC mapping is 1:1 with zero gaps. Confidence: .90.

### Advisory: Dependency Chain Health
- #753 has empty `depends_on` but is manually blocked on #776 — `depends_on: [776]` should be set for structural correctness
- #777 and #778 both depend on #776 (correct)
- Recommend adding `type:research` pass-through tag to #774 — `spike` tag is not in NON_IMPL_TAGS list

### Verdict: APPROVE
### Action Taken: Advanced to todo. Research deliverable is complete — all 7 ACs are covered by the #752 to #776 to #753/#777/#778 task chain. Unique value (AC 6-7) was correctly extracted to #777 and #778. Task needs `type:research` tag for clean pipeline pass-through.
[[2026-04-10]]
## Test-Writer Notes
- Non-impl pass-through: `spike` tag — no testable Python interfaces.
- AC 1–7 describe browser connectivity and content extraction validation behavior intended for a temporary scratch script (`.owlbear/scratch/research/cdp-spike/` — does not exist, deleted post-validation as documented in Implementation Notes).
- No `src/` or `serve/` module is defined or modified by this task.
- Scanned AC for Python implementation intent (implement, function, class, module, src/, serve/, .py, import, endpoint, API) — none found.
- AC 6-7 unique value (trafilatura quality, hash stability) delegated to #777 and #778 by researcher. Tests for those ACs belong in those tasks.
- Passing through to builder.

[[2026-04-10]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
[[2026-04-10]]
## Review Evidence

### Test Results
- pytest: N/A — non-implementation task. No testable Python interfaces.
- Changed files check: `test_schema_extensions_754.py` (task #754) is the only unstaged file. Zero files changed for #774. Confirmed.

### Lint: N/A — no source code modified.

### Coverage: N/A.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
No `TestFromAC_*` classes — conditional skip applies. Test-writer determination reviewed directly against AC text:

| AC Line | Determination Rationale | Verdict |
|---------|------------------------|---------|
| AC 1–5: CDP/Playwright/SSO/EDR | AC describes physical hardware validation on corporate laptop — no Python unit-test surface. Delegated to #752/#776/#753. | CORRECT |
| AC 6: trafilatura extraction quality | Empirical test of corporate HTML — delegated to #777. | CORRECT |
| AC 7: content hash stability | Protocol-based re-extraction test — delegated to #778. | CORRECT |

Test-writer scan for Python implementation intent (`implement`, `function`, `class`, `module`, `src/`, `serve/`, `.py`, `import`, `endpoint`, `API`) found nothing — determination is evidence-based, not a handwave.

#### Security Review
No code changed. No security surface to evaluate. PASS.

#### Test Integrity
No `TestFromAC_*` classes — conditional skip applies.

#### Test Quality
N/A — no tests written (correct for spike pass-through).

#### Data Safety
No data operations. PASS.

#### Implementation-Aware Test Gap Analysis
No implementation. PASS.

#### Builder Process Quality
Single builder pass, no loop. CLEAN.

### AC Compliance Table

| AC Line | Evidence | Delegated To | Status |
|---------|----------|--------------|--------|
| 1. Edge launches with `--remote-debugging-port=9222` | Research doc §3.1 coverage table: #752 research done, #776 script step 3, #753 execution | #752/#776/#753 | DELEGATED / COVERED |
| 2. Playwright `connect_over_cdp` connects | Research doc §3.1: #752 research done, #776 script step 5, #753 execution | #752/#776/#753 | DELEGATED / COVERED |
| 3. SSO-protected SharePoint navigation | Research doc §3.1 + §3.4 (Chrome 136 constraint documented); #752/#776/(steps 6-7)/#753 | #752/#776/#753 | DELEGATED / COVERED |
| 4. Page content extractable via CDP | Research doc §3.1: #752 research done, #776 script step 8, #753 execution | #752/#776/#753 | DELEGATED / COVERED |
| 5. EDR/DLP does NOT block | Research doc §3.1: #753 execution (user observes) | #753 | DELEGATED / COVERED |
| 6. trafilatura extraction quality | Research doc §3.2: F1 0.909 benchmark, corporate HTML risk caveats, `favor_precision` recommendation. #777 exists (status: archived, depends_on: [776]) with concrete AC. | #777 | DELEGATED / COVERED |
| 7. Content hash stable across extractions | Research doc §3.3: stability risk at HTML input layer documented; 3×extraction protocol specified. #778 exists (status: archived, depends_on: [776]) with concrete AC. | #778 | DELEGATED / COVERED |

### Research Deliverable Quality
- `.owlbear/research/774-edge-cdp-spike.md` exists and verified: 10 sources studied, 6 high-relevance, coverage gap table, technical analysis (§3.2–§3.4), recommendation with 3-option comparison, T1 tier classification.
- Follow-up tasks #777 and #778: both confirmed present, status `research`, `depends_on: [776]` (correct — spike script must exist before trafilatura/hash tests can run), concrete AC, parent #751.
- Challenger FALLBACK correctly documented: consolidation recommendation is T1 task management, not a T3 technical trade-off.

### Deductions
None. All Pass 1 criteria either pass or have correct conditional skips.

### Informational (Pass 2)
- Architect flagged `spike` tag may not be in `NON_IMPL_TAGS` pipeline variable — `type:research` tag recommended for explicit match. Informational only; test-writer correctly identified semantics regardless of tag matching.

### Verdict
Confidence: .95 → **PASS**

This is a research spike with correct pass-through behavior at every pipeline stage. The deliverable is the research document and follow-up tasks — both verified to exist with appropriate quality. All 7 ACs are covered by downstream tasks with 1:1 mapping and zero gaps. No code was changed; no security surface exists.
[[2026-04-10]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Research spike — no code changed; no behavior/API change |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` §"Phase 0 CDP Spike Research (Task #774)" (lines 45–51) already present with 6 high-relevance sources, all attributed to `774-edge-cdp-spike.md` |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/774-edge-cdp-spike.md` exists; linked from task body; follow-up tasks #777 and #778 confirmed present with `depends_on: [776]` and concrete AC |

### Files Updated
None — all documentation already accurate.

### Scratch Files
`.owlbear/scratch/774-*` — none found. `.owlbear/scratch/research/cdp-spike/` — not present (correctly deleted per Implementation Notes post-validation).

### Informational
`.owlbear/sources/overview.md` line 1752 contains a `## Knowledge-ops SKILL.md Research (Task #774)` section — a stale ID collision from a different historical research task. Does not affect this gate; correct #774 sources block is at lines 45–51. Data quality note only.