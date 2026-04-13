---
id: 753
title: 'P0-02: Execute CDP spike on corporate laptop'
status: done
priority: critical
created: '2026-04-10T10:55:24.83012Z'
updated: '2026-04-13T23:19:53.984573+00:00'
tags:
- phase-0
- type:user-action
- scope:browser
- archived
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---

Execute the CDP spike script (P0-01 #752) on the corporate laptop with an active Edge SSO session.

Document results in `.owlbear/research/cdp-spike-results.md`:
- CDP connectivity: pass/fail
- SSO extraction: pass/fail
- EDR reaction: any alerts/blocks from --remote-debugging-port
- DLP reaction: any alerts from bulk text extraction
- SharePoint boilerplate behavior

Go/no-go decision: If CDP works → proceed Phase 1. If blocked → pivot strategy task.

AC:
- Spike executed, results documented
- Go/no-go decision recorded

[[2026-04-10]]
## Research
- Research doc: .owlbear/research/cdp-spike-execution-753.md
- Sources: 5 studied, 2 high-relevance (existing research + board state)
- Recommendation: Block until #776 completes (confidence: .85)
- Follow-up tasks created: none (dependency chain already exists)
- Decision requests: none — prerequisite dependency, not a design choice

## Challenge Results
- Challenger: FALLBACK — no recommendation to challenge; binary prerequisite assessment
- Confidence in original: .85
- Key challenges: N/A
- Researcher response: N/A

## Findings Summary
1. `.owlbear/scratch/cdp-spike.py` does not exist — #776 (implement script) is at research status
2. #753 has empty `depends_on` but logically depends on #776 (created after #753)
3. Execution plan and go/no-go decision matrix documented in research doc §3.2–§3.3
4. Chrome 136 fresh-profile constraint (from #752 research) is the primary risk variable for execution
5. Task is `type:user-action` — requires physical execution, EDR/DLP observation, and user-made go/no-go decision

[[2026-04-11]]
## Research (validation pass — 2026-04-11)
- Research doc: .owlbear/research/cdp-spike-execution-753.md (updated)
- Sources: 5 studied, 2 high-relevance (spike script + #776 archive status)
- Recommendation: Advance to backlog — blocker resolved (confidence: .90)
- Follow-up tasks created: none (execution chain complete)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — validation pass confirming resolved dependency, not a design choice
- Confidence in original: .90
- Key challenges: N/A
- Researcher response: N/A

## Findings Summary
1. **Blocker resolved:** #776 (implement spike script) is DONE and archived. `.owlbear/scratch/cdp-spike.py` exists (~245 LOC)
2. Production browser package also complete at `serve/browser/` (edge_launcher, cdp, extractor, cleaner)
3. Execution plan and go/no-go decision matrix documented in research doc §3.2–§3.3
4. #777 (trafilatura) and #778 (hash stability) are separate additive tasks — do not block core spike execution
5. Task is `type:user-action` — requires: close Edge, install playwright, run spike, observe EDR/DLP, record go/no-go
[[2026-04-11]]
## Architecture Review

### User-Action Assessment
Task is tagged `type:user-action`. Criterion 13 evaluation:
- **Counter-signals:** NONE (no function signatures, no test outcomes, no `type:test`/`type:config`)
- **M1:** AC defines no testable Python interface — TRUE
- **M2:** Completion can only be verified by human (physical EDR/DLP observation, go/no-go judgment) — TRUE
- **S1:** Physical-action verbs: "Execute", "close Edge", "run spike", "observe" — YES
- **S2:** External systems: Edge browser, corporate laptop, EDR, DLP, SharePoint — YES
- **S3:** Manual steps: close Edge, install playwright, run spike, observe EDR/DLP, record go/no-go — YES
- **Result:** `type:user-action` CONFIRMED → BLOCK verdict

### Prerequisite Verification
- `.owlbear/scratch/cdp-spike.py` — EXISTS (confirmed via filesystem check)
- #776 (implement spike script) — DONE and archived per research validation pass
- #777 (trafilatura) and #778 (hash stability) — independent, do not block spike execution

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| Spike executed, results documented | ADEQUATE for user-action | Body specifies 5 result categories (CDP connectivity, SSO extraction, EDR reaction, DLP reaction, SharePoint boilerplate) |
| Go/no-go decision recorded | ADEQUATE for user-action | Body specifies decision matrix: CDP works → Phase 1, blocked → pivot |

### Execution Checklist (for user)
1. Close all Edge instances
2. `pip install playwright` (or `uv pip install playwright`)
3. `playwright install chromium` (if not already installed)
4. Run `.owlbear/scratch/cdp-spike.py` with active Edge SSO session
5. Observe: EDR alerts? DLP alerts? CDP connectivity? SSO cookie extraction?
6. Document results in `.owlbear/research/cdp-spike-results.md`
7. Record go/no-go decision
8. Add `## Action Completed` section to this task body with AC checkboxes

### Challenge Results
- Challenger: FALLBACK — `type:user-action` BLOCK verdict; no design decision to challenge
- Scribe: FALLBACK — scribe agent not in available roster; block reason recorded inline

### Verdict: BLOCK
User-action task. Prerequisites verified (script exists, #776 done). AC adequate for physical execution. Blocked pending user action.

## Hash Stability Checklist (from #778)

Run spike with hash stability validation (step from #778 — AC1):

5a. Run with `--hash-stability` flag: `python .owlbear/scratch/cdp-spike.py --hash-stability` (adds ~6 min per URL)
5b. Check console output: look for `Hash stability: GO/NO-GO` verdict per URL and overall
5c. If NO-GO: inspect the diff output in the log — check for dynamic element patterns to remove via `prune_xpath`

[[2026-04-13]]
## Action Completed

- CDP connectivity: **FAIL** — `ECONNREFUSED 127.0.0.1:9222`
- SSO extraction: NOT TESTED (blocked by CDP)
- EDR reaction: N/A (CDP never opened)
- DLP reaction: N/A
- SharePoint boilerplate: NOT TESTED

**Root cause:** Corporate Group Policy `RemoteDebuggingAllowed = 0` at `HKLM\SOFTWARE\Policies\Microsoft\Edge`. Edge silently ignores `--remote-debugging-port`. Also: `HeadlessModeEnabled = 0`.

**Go/no-go: NO-GO** — CDP approach blocked on corporate laptop. Pivot strategy required.

Full results: `.owlbear/research/cdp-spike-results.md`

[[2026-04-14]]
## Archived — CDP Pivot
Spike completed, NO-GO recorded. CDP blocked by Group Policy (`RemoteDebuggingAllowed=0`). Pivot to Playwright Chromium + SSO extension validated in E2E PoC. See `.owlbear/research/cdp-spike-results.md`.