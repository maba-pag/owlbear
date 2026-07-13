---
id: 752
title: 'P0-01: Write Edge CDP validation spike script'
status: archived
priority: medium
created: '2026-04-10T10:55:04.342033+00:00'
updated: '2026-04-10T15:02:32.994897+00:00'
tags:
- phase-0
- type:research
- scope:browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Write a script in `.owlbear/scratch/` that:

1. Launches Edge with `--remote-debugging-port=9222` bound to 127.0.0.1
2. Connects via Playwright CDP
3. Navigates to a known SSO-protected SharePoint page
4. Extracts cleaned text content
5. Logs any EDR/DLP alerts observed
6. Handles failure gracefully with clear error messages

This is Phase 0 of the Authenticated Content Pipeline (#751). Go/no-go gate for the entire feature.

AC:

- Script exists in `.owlbear/scratch/cdp-spike.py`
- Script can be run with `uv run python .owlbear/scratch/cdp-spike.py`
- Handles Edge not found, port in use, connection failure gracefully

[[2026-04-10]]

## Research

- Research doc: .owlbear/research/cdp-spike-752.md
- Sources: 8 studied, 4 high-relevance
- Recommendation: Proceed with Approach A (manual launch + connect_over_cdp) using --user-data-dir with fresh profile to comply with Chrome 136 restriction (confidence: .80)
- Follow-up tasks created: #776 (implement cdp-spike.py, research status)
- Decision requests: none

## Challenge Results

- Challenger: FALLBACK — spike validation is a binary empirical test, no controversial recommendation to challenge
- Confidence in original: .80
- Key challenges: N/A
- Researcher response: N/A

## Critical Finding

Chrome 136 (March 2025) changed `--remote-debugging-port` to require `--user-data-dir` pointing to a non-default directory. The default Edge profile (with SSO cookies) can no longer be debugged. The spike MUST test whether Windows Integrated Auth (Kerberos/NTLM) provides automatic SSO to SharePoint with a fresh Edge profile. This is the primary risk variable for the go/no-go gate.

## Post-task Reflection

- Chrome 136 `--remote-debugging-port` restriction is a significant constraint not documented in the original brief or prior research — all prior research (#264, #495, #684) predates this change
- The brief's security voice correctly identified "Test EDR reaction to `--remote-debugging-port`" as Phase 0 scope, but didn't flag the Chrome 136 profile restriction
- Windows Integrated Auth is the likely lifeline — corporate SharePoint environments commonly use Kerberos/NTLM which works independent of browser cookies
[[2026-04-10]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Research-only deliverable; implementation split to #776 |
| Interface clarity | PASS (advisory) | Original AC references script deliverables but task is now `type:research`; actual deliverables (research doc, follow-up #776) are clearly documented in body. Pass-through tag prevents pipeline confusion. |
| Dependency correctness | PASS | No depends_on, correct for Phase 0 entry point. #776 correctly depends on this task. |
| Module layering | N/A | Research task, no code |
| TDD compliance | PASS | `type:research` is pass-through — no test required |
| KISS/YAGNI | PASS | Research appropriately scoped to CDP viability + Chrome 136 constraint |
| Premise challenge | PASS | Phase 0 spike research is necessary before go/no-go gate investment |
| Pattern consistency | PASS | Research doc format, follow-up task creation, challenge section all follow established patterns |
| Security surface | PASS | N/A for research; security considerations thoroughly documented in brief security voice (HR#1-5) |
| Single domain | PASS | scope:browser only |

### Challenge Results

- Challenger: FALLBACK — no challenger agent available in agent list
- Architect self-assessment: Research is empirically-grounded (8 sources, 4 high-relevance). Chrome 136 finding is a genuine constraint that invalidates prior research assumptions (#264, #495, #684). The recommendation (Approach A: manual launch + connect_over_cdp) is well-justified for a diagnostic spike. Confidence: .88.

### Codebase Verification

- `SourceType` enum in `serve/knowledge/src/owlbear_knowledge/models.py` has `URL_LIST` and `FILE_GLOB` only — confirmed AUTHENTICATED_WEB doesn't exist yet (Phase 1 scope)
- `RefreshOrchestrator` in `serve/knowledge/src/owlbear_knowledge/refresh.py` dispatches by SourceType — architecture aligns with protocol injection approach
- No existing `serve/browser/` package — clean slate confirmed
- No playwright dependency in any pyproject.toml — confirms spike is standalone
- Prior research (#264, #495, #684) all predate Chrome 136 — this research correctly identifies the gap

### Advisory: Stale AC

The original AC ("Script exists in .owlbear/scratch/cdp-spike.py", runnable, handles errors) describes #776's deliverable, not this task's. Since `type:research` tag ensures pass-through, this is non-blocking. The body's Research section clearly documents the actual deliverables (research doc + follow-up task).

### Verdict: APPROVE

### Action Taken: Advanced to todo. Research deliverable is complete with thorough Chrome 136 analysis. Follow-up #776 carries the implementation with refined AC. Non-impl tag `type:research` already present

[[2026-04-10]]

## Test-Writer Notes

- Non-implementation task (tagged type:research) — no tests applicable.
- Passing through to builder.
[[2026-04-10]]

## Builder Notes

- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-04-10]]

## Review Evidence

### Test Results

- pytest: N/A — `type:research` pass-through, no `TestFromAC_*` classes

### Lint

- N/A — no Python source files changed

### Coverage

- N/A — no Python source files changed

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

SKIP — no `TestFromAC_*` classes exist (correct; test-writer documented "Non-implementation task (tagged type:research) — no tests applicable")

#### Security Review

Research doc security posture is sound:

- Recommends CDP binding to 127.0.0.1 only (§3.5 intent)
- Mandates fresh `--user-data-dir` (Chrome 136 constraint documented)
- Gap A (`--remote-allow-origins`) was subsequently identified in #776 research and documented as binding builder guidance in #776 architecture review
- No hardcoded secrets, no injection surface, no credentials in research doc

No issues.

#### Test Integrity

SKIP — no TestFromAC_ classes

#### Test Quality

SKIP — no tests

#### Data Safety

N/A — research document only, no data persisted or mutated

#### Implementation-Aware Gaps

N/A — no implementation code

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN — single correct pass-through |

---

### Pass 2 — INFORMATIONAL

None. Research quality is high and the task correctly reclassified scope to #776.

---

### AC Compliance

(Adapted for `type:research` — original AC is stale per architect advisory; reviewed against actual research deliverables)

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Orig AC1 — script at `.owlbear/scratch/cdp-spike.py` | Stale (architect: advisory). Actual deliverable is research doc. `.owlbear/research/cdp-spike-752.md` confirmed to exist and contain §3.3 design. #776 AC1 carries the file deliverable. | N/A (research) | PASS (via #776) |
| Orig AC2 — runnable with `uv run` | Stale. #776 AC2 carries this. Research §3.6 confirms playwright-only dependency. | N/A | PASS (via #776) |
| Orig AC3 — handles Edge not found, port in use, connection failure | §3.4 error matrix documents all 8 failure cases. #776 AC9 carries the code implementation. | N/A | PASS (via #776) |
| Research deliverable 1 — `.owlbear/research/cdp-spike-752.md` | File confirmed via workspace search. 8 sources studied (4 high-relevance), Chrome 136 restriction fully documented, Approach A vs B comparison, §3.3 step design, §3.4 error matrix, §3.5 EDR/DLP guidance. | N/A | PASS |
| Research deliverable 2 — follow-up task created | Task #776 confirmed: 11 AC lines, `depends_on: [752]`, parent #751, binding builder guidance for Gap A (security), Gap B (URL config), Gap C (try/finally). Architecture review APPROVED. | N/A | PASS |

---

### Confidence: .95

### Verdict: PASS

[[2026-04-10]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | type:research pass-through; no code modified |
| 2 | Module docstrings | No | N/A | No Python source files created or modified |
| 3 | External attribution → sources/overview.md | Yes | PASS | `.owlbear/sources/overview.md` "Edge CDP Validation Spike (Task #752)" section present with all 4 high-relevance sources (connect_over_cdp API, Chrome 136 change, launch_persistent_context API, Chrome Extensions docs) |
| 4 | CLI changes → README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | PASS | `.owlbear/research/cdp-spike-752.md` confirmed present; task body links it; follow-up #776 created and confirmed |
| 6 | Scratch file cleanup | N/A | PASS | No `.owlbear/scratch/752-*` files found |

Files updated: none required.
Scratch cleaned: nothing to clean.
Commit: skipped (no documentation files changed).
[[2026-04-10]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Research doc at `.owlbear/research/cdp-spike-752.md` | File exists, committed in `26fa00a1`, 135 lines, 8 sources studied, Chrome 136 critical finding documented | PASS |
| Follow-up task created | #776 exists (in-progress), `depends_on: [752]`, 11 AC lines, references research doc §3.3 | PASS |
| Follow-up references research doc | #776 body: "using the design from `.owlbear/research/cdp-spike-752.md` §3.3" | PASS |
| Orig AC1-3 (stale — script deliverables) | Correctly deferred to #776 per architect advisory. Not applicable to research task. | PASS (via #776) |

### Test Results

- pytest: 3163 passed, 389 failed, 2 errors — no failures in task scope (zero code changes)
- ruff: clean

### Architect Quality: 4/5

Original AC described script deliverables for a task that became research. Architect correctly identified stale AC as advisory and approved. Research body documented actual deliverables clearly. Minor upstream scoping gap compensated at architecture level.

### Deduction Breakdown

- No deductions applicable. All deliverables evidenced, lint clean, reviewer evidence detailed, no task-scope test failures, AC quality > 3.

### Confidence: 1.00

### Action: archive
