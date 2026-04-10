# CDP Spike Execution — Readiness Assessment & Execution Plan

> **Owning task:** #753 — P0-02: Execute CDP spike on corporate laptop
> **Date:** 2026-04-10 **Status:** Blocked on prerequisite

## 1. Context and Question

Task #753 requires physically running the CDP spike script on a corporate laptop with
an active Edge SSO session, observing EDR/DLP reactions, and recording a go/no-go
decision for the Authenticated Content Pipeline (#751). Can this task proceed?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | CDP spike research doc | .owlbear/research/cdp-spike-752.md | .95 |
| 2 | Task #776 (implement script) | Kanban board | .95 |
| 3 | Task #752 (write script — parent research) | Kanban board | .90 |
| 4 | Chrome 136 restriction (via #752 research) | developer.chrome.com/blog/remote-debugging-port | .90 |
| 5 | Task #751 (parent feature) | Kanban board | .80 |

## 3. Analysis

### 3.1 Prerequisite Status

| Prerequisite | Task | Status | Blocked? |
|--------------|------|--------|----------|
| CDP spike research | #752 | backlog (research done) | No |
| Implement cdp-spike.py | #776 | research | **YES — script doesn't exist** |
| Edge installed | — | Corporate-managed | No |
| Playwright available | — | Not yet installed | Deferred to #776 |

**Critical gap:** `.owlbear/scratch/cdp-spike.py` does not exist. Task #776 (implement
the script per #752 research §3.3) is at `research` status — not yet through the
pipeline. This task cannot proceed without the script.

**Missing dependency:** #753 has an empty `depends_on` list, but logically depends on
#776. The task was created before #776 existed.

### 3.2 Execution Plan (for when #776 completes)

When `cdp-spike.py` exists, the user should follow this checklist:

#### Pre-execution
1. Confirm Edge is installed: `where msedge` or check `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
2. Close ALL Edge windows (port 9222 conflicts with running instances)
3. Install playwright: `uv pip install playwright` (no `playwright install` needed — CDP uses existing Edge)
4. Open Windows Event Viewer → Security/Application logs (for EDR correlation)
5. Note the current time (for EDR/DLP log correlation)

#### Execution
6. Run: `uv run python .owlbear/scratch/cdp-spike.py`
7. Wait for completion (script handles its own lifecycle)
8. Keep terminal open — do not close for ~5 minutes (EDR reaction window)

#### Observation — record each item
| Check | What to observe | Pass criteria |
|-------|-----------------|---------------|
| CDP connectivity | Script connects to 127.0.0.1:9222 | No timeout or connection error |
| Chrome 136 compat | CDP endpoint responds after launch | HTTP 200 from /json/version |
| SSO extraction | SharePoint page loads with content | Text length > 0, no login redirect |
| Windows Integrated Auth | Fresh profile authenticates automatically | No password prompt, no IdP redirect |
| EDR reaction | Check Event Viewer + corporate security dashboard | No alerts/blocks on `--remote-debugging-port` |
| DLP reaction | Check Event Viewer + DLP console (if accessible) | No alerts on text extraction |
| SharePoint boilerplate | Inspect extracted text quality | Meaningful content, not just nav/chrome |

#### Post-execution
9. Check Windows Event Viewer for security events near the noted timestamp
10. Check corporate security dashboard (if accessible) for EDR alerts
11. Wait 24h if possible — some EDR policies have delayed reactions

### 3.3 Go/No-Go Decision Matrix

| CDP | SSO | EDR | DLP | Decision |
|-----|-----|-----|-----|----------|
| ✓ | ✓ | Clean | Clean | **GO** — proceed Phase 1 |
| ✓ | ✓ | Alert | Clean | **CONDITIONAL GO** — assess EDR severity |
| ✓ | ✗ | — | — | **NO-GO** — SSO approach fails, pivot to SharePoint REST API |
| ✗ | — | — | — | **NO-GO** — CDP blocked entirely, pivot strategy needed |
| ✓ | ✓ | Block | — | **NO-GO** — EDR blocks CDP, pivot strategy needed |
| ✓ | ✓ | Clean | Block | **NO-GO** — DLP blocks extraction, pivot strategy needed |

### 3.4 Risk: Chrome 136 + Fresh Profile

The #752 research identified this as the **primary risk variable**. Windows Integrated
Auth (Kerberos/NTLM) must provide SSO to SharePoint from a fresh Edge profile — without
the default profile's cookies. Corporate environments using Entra ID + Windows Hello
often negotiate auth at OS level, but this is unverified in this environment.

## 4. Recommendation (.85 confidence)

**Block #753 until #776 completes.** No research or execution work can proceed without
the spike script. When #776 delivers `cdp-spike.py`, this task becomes a pure
user-action: follow §3.2 checklist, document results in `.owlbear/research/cdp-spike-results.md`,
and apply §3.3 decision matrix.

Challenge: FALLBACK — no recommendation to challenge; this is a dependency status
assessment with a binary prerequisite (script exists or doesn't).

## 5. Follow-up Tasks

No new tasks needed — the dependency chain is already established:
- #776 (implement cdp-spike.py) → must complete first
- #753 (this task, execute spike) → unblocked when #776 is done
- Missing: formal `depends_on` link from #753 to #776
