# CDP Spike Execution — Readiness Assessment & Execution Plan

> **Owning task:** #753 — P0-02: Execute CDP spike on corporate laptop
> **Date:** 2026-04-11 **Status:** Complete (validation pass — unblocked)

## 1. Context and Question

Task #753 requires physically running the CDP spike script on a corporate laptop with
an active Edge SSO session, observing EDR/DLP reactions, and recording a go/no-go
decision for the Authenticated Content Pipeline (#751). Previous research (2026-04-10)
blocked this task on #776 (script implementation). Validation pass: is the blocker
resolved?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | CDP spike script (implemented) | .owlbear/scratch/cdp-spike.py | .95 |
| 2 | Task #776 (archived — done) | Kanban archive | .95 |
| 3 | Production browser package | serve/browser/src/owlbear_browser/ | .90 |
| 4 | #774 research (Phase 0 consolidation) | .owlbear/research/774-edge-cdp-spike.md | .90 |
| 5 | #776 test file | tests/test_cdp_spike_776.py | .85 |

## 3. Analysis

### 3.1 Blocker Resolution

| Prerequisite | Task | Previous status | Current status |
|--------------|------|-----------------|----------------|
| CDP spike research | #752 | backlog | **DONE (archived)** |
| Implement cdp-spike.py | #776 | research | **DONE (archived)** |
| Phase 0 spike research | #774 | active | **DONE (archived)** |
| Edge installed | — | Yes | Yes |
| Playwright available | — | Deferred | Install needed: `uv pip install playwright` |

**Blocker resolved.** `.owlbear/scratch/cdp-spike.py` exists (~245 LOC) and covers:
Edge discovery, Chrome 136-compliant launch args (`--user-data-dir`, `--remote-allow-origins`),
CDP connection via Playwright, SSO redirect detection, body text extraction, timestamped
logging, and cleanup on all exit paths.

### 3.2 Execution Plan

#### Pre-execution
1. Close ALL Edge windows (port 9222 conflicts with running instances)
2. Install playwright: `uv pip install playwright`
3. Open Windows Event Viewer → Security/Application logs (for EDR correlation)
4. Note the current time (for EDR/DLP log correlation)

#### Execution
5. Run: `uv run python .owlbear/scratch/cdp-spike.py --url <your-sharepoint-url>`
6. Wait for completion (script handles its own lifecycle)
7. Keep terminal open — do not close for ~5 minutes (EDR reaction window)

#### Observation — record each item
| Check | What to observe | Pass criteria |
|-------|-----------------|---------------|
| CDP connectivity | Script connects to 127.0.0.1:9222 | No timeout/connection error |
| Chrome 136 compat | CDP endpoint responds after launch | No "flag ignored" error |
| SSO extraction | SharePoint page loads with content | Text length > 0, no login redirect |
| Windows Integrated Auth | Fresh profile authenticates automatically | No password prompt |
| EDR reaction | Check Event Viewer + security dashboard | No alerts on `--remote-debugging-port` |
| DLP reaction | Check Event Viewer + DLP console | No alerts on text extraction |
| SharePoint boilerplate | Inspect extracted text quality | Meaningful content, not just nav |

#### Post-execution
8. Check Windows Event Viewer for security events near the noted timestamp
9. Check corporate security dashboard (if accessible) for EDR alerts
10. Wait 24h if possible — some EDR policies have delayed reactions

### 3.3 Go/No-Go Decision Matrix

| CDP | SSO | EDR | DLP | Decision |
|-----|-----|-----|-----|----------|
| ✓ | ✓ | Clean | Clean | **GO** — proceed Phase 1 |
| ✓ | ✓ | Alert | Clean | **CONDITIONAL GO** — assess EDR severity |
| ✓ | ✗ | — | — | **NO-GO** — SSO fails, pivot to SharePoint REST API |
| ✗ | — | — | — | **NO-GO** — CDP blocked, pivot strategy needed |
| ✓ | ✓ | Block | — | **NO-GO** — EDR blocks CDP |
| ✓ | ✓ | Clean | Block | **NO-GO** — DLP blocks extraction |

### 3.4 Scope Note: trafilatura + hash stability

#777 (trafilatura quality) and #778 (hash stability) are separate tasks at `research`
status. They expand the spike with extraction quality and hash stability tests
(from #774 research). These are additive — #753's core hypothesis (CDP + SSO works?)
does not depend on them. Running the base spike first is preferred: if CDP/SSO fails,
#777/#778 are moot.

## 4. Recommendation (.90 confidence)

**Advance #753 to backlog.** The prerequisite blocker (#776) is fully resolved. The
spike script exists and is ready for user execution. This is a `type:user-action`
task — the user follows §3.2, observes §3.3, and records the go/no-go decision.

Challenge: FALLBACK — validation pass confirming a resolved dependency, not a
design choice.

## 5. Follow-up Tasks

None needed. The dependency chain is complete:
- #776 (implement script) → **DONE**
- #753 (this task, execute spike) → **UNBLOCKED, ready for user action**
- #777, #778 (expanded tests) → separate tasks, can proceed independently
