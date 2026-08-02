---
id: 878
title: Submit Azure AD app registration request to IT for Graph API SharePoint access
status: archived
priority: medium
created: '2026-04-14T19:30:42.941518+00:00'
updated: '2026-04-15T20:28:25.222321+00:00'
tags:
- phase-4
- scope:knowledge
- deferred
- non-code
parent: 773
depends_on: []
blocked: true
block_reason: 'type:user-action — requires human physical action (submit IT request,
  record ticket ID). No testable Python interface. Needs user to perform AC #2–#4
  manually.'
claimed_by: null
claimed_at: null
---
Non-code prerequisite for Graph API SharePoint extraction.

## Acceptance Criteria

1. Document required permissions: `Sites.Read.All` (delegated) or `Sites.Selected` with justification
2. Prepare app registration request following corporate IT intake process
3. Submit request and record ticket/tracking ID
4. Track approval status — expected timeline weeks to months

## Context

- See .owlbear/research/773-sharepoint-rest-api-parallel-path.md §3.3 for auth options
- MSAL Python device-code flow or interactive browser flow for token acquisition
- Delegated permissions preferred (user-present model, aligns with OwlBear's design)
- No code investment should happen until approval is confirmed

## Blockers

- Requires identifying the correct IT intake process for Azure AD app registrations
- Conditional Access policies may block device-code flow — needs IT consultation

[[2026-04-14]]

## Research

- Research doc: .owlbear/research/878-azure-ad-app-registration-request.md
- Sources: 5 studied, 3 high-relevance (Graph API sitePage permissions, Entra ID app registration, device-code flow)
- Recommendation: Request `Sites.Read.All` (delegated) with device-code flow — least privileged permission for sitePage.Get, same auth pattern as existing Copilot OAuth (confidence: .85)
- Key deliverable: Complete app registration specification (§3.3) and justification template (§3.4) ready for IT submission
- Risks: Conditional Access may block device-code (.40); IT may require Sites.Selected (.40); approval timeline weeks-months (.70) — all mitigated, Playwright path works today
- Tier: T1 — Autonomous. Documentation/preparation only, no code or architecture impact
- Follow-up tasks created: none (sibling #879 already exists)
- Decision requests: none
- Challenge: FALLBACK — challenger not in available agent list
- Sources logged in .owlbear/sources/overview.md
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single purpose: submit and track an IT request |
| Interface clarity | PASS | AC steps are clear and sequential |
| Dependency correctness | PASS | No dependencies; correct for a gating prerequisite |
| Module layering | PASS | N/A — no code |
| TDD compliance | PASS | N/A — no code |
| KISS/YAGNI | PASS | Minimal scope — documentation and submission only |
| Premise challenge | PASS | Validated: Graph API access genuinely requires Azure AD app registration with admin consent |
| Pattern consistency | PASS | N/A — no code |
| Security surface | PASS | Research §3.3 specifies least-privilege delegated permissions, public client, no client secret |
| Single domain | PASS | scope:knowledge — single domain |
| User-action detection | **DETECTED** | See below |

### User-Action Detection (Step 2 §13)

- **Counter-signals:** None (no function signatures, no test outcomes, not type:test/config)
- **Mandatory:** M1 — no testable Python interface ✓; M2 — human-only verification ✓
- **Signals:** S1 — "Submit", "Prepare", "Track" ✓; S2 — Azure AD, Entra ID, corporate IT ✓; S3 — manual steps in AC #2–#4 ✓
- **Verdict:** type:user-action confirmed

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: Document required permissions | Clear and verifiable — research §3.3 provides the spec | No change needed |
| AC2: Prepare app registration request | Clear — research §3.3–§3.4 provide complete template | No change needed |
| AC3: Submit request and record ticket ID | Clear but human-only — no Python interface | Blocked: user action required |
| AC4: Track approval status | Clear but human-only — ongoing manual tracking | Blocked: user action required |

### Tagging

- Task needs `type:user-action` tag added (currently has `non-code` which is not a canonical pass-through tag)
- Unable to add tag: `edit_task` tool not available. User or orchestrator should add `type:user-action` tag.

### Challenge Results

- Challenger: FALLBACK — challenger not in available agent list
- Scribe: FALLBACK — scribe not in available agent list (AR not created via scribe)
- Architect response: proceeding on criteria analysis; user-action detection is unambiguous

### Verdict: BLOCK

### Action Taken: Blocked as type:user-action. All AC items require human physical action (submit Azure AD app registration to IT, record tracking ID, monitor approval). Research doc §3.3–§3.4 provide complete specification and justification template ready for submission. User should: (1) add `type:user-action` tag, (2) identify IT intake process, (3) submit request, (4) record ticket ID in task body under `## Action Completed`

[[2026-04-15]]

## Archived — Won't Do\nGraph API SharePoint code path was fully removed in task #886 (dead path per v1 auth failure). Azure AD app registration is no longer needed. Archiving as won't-do
