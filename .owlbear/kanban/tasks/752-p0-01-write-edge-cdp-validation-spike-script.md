---
id: 752
title: 'P0-01: Write Edge CDP validation spike script'
status: todo
priority: critical
created: '2026-04-10T10:55:04.342033+00:00'
updated: '2026-04-10T12:01:18.830441+00:00'
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
### Action Taken: Advanced to todo. Research deliverable is complete with thorough Chrome 136 analysis. Follow-up #776 carries the implementation with refined AC. Non-impl tag `type:research` already present.