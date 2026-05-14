---
task_id: 1534
agent: auditor
request_type: decision
created: '2026-05-14'
response: approved
resolved_by: cockpit-api
---

See `.owlbear/research/cockpit-visual-audit.md`.

Decision needed before Planner decomposes remediation: should the next Cockpit UI cycle be a coordinated dashboard redesign, and what product/design constraints should it obey?

Recommendation: approve a full Cockpit dashboard redesign cycle, adopt a PDS-first visible-control policy, keep 320px as a tested no-overflow viewport, and require screenshot visual gates before future UI tasks are accepted. Overall confidence: 0.84.

Option A — Full coordinated redesign cycle (recommended, confidence 0.86)
Pros: addresses root cause across shell, sidecar, filters, overlays, cards, and responsive behavior; avoids local fixes that still leave the whole dashboard incoherent.
Cons: larger planning effort; more regression surface.
Risk: scope can sprawl unless Planner splits by visible workflow and locks screenshot gates.
Expected outcome: Planner creates coordinated tasks for shell/sidecar, overlays, filters/forms, card metadata, responsive contract, and visual gates.

Option B — Incremental polish inside current structure (confidence 0.38)
Pros: smaller changes; faster first green pass.
Cons: likely preserves the raw-dashboard feel because the failures are contextual, not isolated.
Risk: false-green visual tasks continue: each local component can pass while the full Cockpit remains unfinished.

Required sub-decisions for Planner:
1. PDS policy: PDS-first for all visible controls, with explicit exceptions only. Pro: consistent controls and accessibility. Con: some wrappers need event-pattern cleanup. Risk: test updates required. Confidence: 0.82.
2. Sidecar IA: redesign as a real inspector; decide whether DR queue remains above detail or moves to a dedicated sheet/route. Pro: fixes worst surface. Con: needs product choice. Risk: preserving current mixed sidecar keeps cognitive clutter. Confidence: 0.80.
3. Mobile contract: keep 320px no-overflow as required, but define whether it is full UI, board-only, or controlled unsupported state. Pro: ends ambiguity. Con: may constrain layout. Risk: continuing reachability-only tests hides bad UX. Confidence: 0.78.
4. Visual gate: add screenshot regression baselines for desktop, detail, filters, overlays, dark, tablet, and mobile. Pro: prevents future false-green visual work. Con: screenshot maintenance cost. Risk: flaky baselines if animations/SSE are not controlled. Confidence: 0.83.

## Response
- response: approved
Approved via chat on 2026-05-14. Use the #1560 recommended package: full coordinated Cockpit dashboard redesign; PDS-first visible controls; sidecar as inspector; PPopover/PModal/PSheet overlay strategy; 320px no-overflow mobile contract with board-first/sheet preference; screenshot and structural visual gates; keep local pinned PDS runtime assets, no live CDN switch for visual remediation.
