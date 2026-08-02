---
id: 889
title: Monitor Copilot SDK for structured output / completions API support
status: archived
priority: medium
created: '2026-04-15T15:00:20.268602+00:00'
updated: '2026-04-15T20:43:40.505669+00:00'
tags:
- scope:knowledge
- tracking
parent: null
depends_on: []
blocked: true
block_reason: type:user-action — AC defines no testable Python interface; completion
  requires human judgment (checking external release notes). Recurring "quarterly"
  AC also has no terminal done state.
claimed_by: null
claimed_at: null
---
Track `github/copilot-sdk` releases for addition of a raw completions API or structured output (`response_format`) support. The SDK is in public preview (v0.2.2 as of 2026-04-15) and evolving rapidly.

## Acceptance Criteria

- Check SDK changelog/release notes quarterly (or when bumping deps)
- If SDK adds `response_format` or completions-level API, re-evaluate vs Option B (direct endpoint)
- Update .owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md with findings

## Context

- See .owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md — SDK (Option A) was rejected because it lacks structured output support
- SDK repo: <https://github.com/github/copilot-sdk>
- PyPI: <https://pypi.org/project/github-copilot-sdk/>
[[2026-04-15]]

## Research

Quarterly monitoring check of `github/copilot-sdk` for structured output / completions API support.

### Key Findings

- **SDK v0.2.2** (2026-04-10, latest) — still no `response_format` or completions-level API. SDK remains agent/session-oriented (`session.send()` → text events).
- **Changelog v0.2.0–v0.2.2** reviewed: additions include config discovery, commands/elicitation, system prompt customization, telemetry, blob attachments. Zero structured output features.
- **Issue #857** "Force structured output" — open since 2026-03-14, no milestone or official response observed.
- **BYOK `wire_api`** (`"completions"` | `"responses"`) exists but only for custom providers with external keys — not applicable to Copilot's own models.
- **SDK status**: still "Public Preview", "may change in breaking ways."

### Conclusion

Original #887 recommendation (Option B with caveats, confidence .65) remains unchanged. No re-evaluation triggered. Updated `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` with monitoring addendum.

- Research doc: .owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md (updated)
- Sources: 3 studied, 3 high-relevance
- Recommendation: No change from #887 (confidence: .65)
- Follow-up tasks created: none (tracking task re-checks quarterly)
- Decision requests: none
[[2026-04-15]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: monitor one SDK for one capability |
| Interface clarity | FAIL | AC is recurring ("quarterly") with no terminal done state — kanban tasks need a clear completion condition |
| Dependency correctness | PASS | No dependencies listed, none needed |
| Module layering | N/A | No code produced |
| TDD compliance | N/A | No code produced |
| KISS/YAGNI | PASS | Minimal tracking scope |
| Premise challenge | PASS | Valid — tracking an SDK gap that blocks Option A adoption |
| Pattern consistency | N/A | No code produced |
| Security surface | N/A | No code produced |
| Single domain | PASS | scope:knowledge only |

### User-Action Detection (Criterion 13)

- **Counter-signals:** None (no function signature, no test outcomes, not type:test/config)
- **Mandatory M1:** AC defines no testable Python interface — all 3 items are "check," "re-evaluate," "update doc" ✓
- **Mandatory M2:** Completion only verifiable by human reading external release notes ✓
- **Signals S1:** "Check SDK changelog/release notes" — physical-action verb ✓
- **Signals S2:** References external systems (PyPI, GitHub repo) ✓
- **Result:** `type:user-action` detected

### AC Issues

1. **Recurring AC with no done state.** "Check SDK changelog/release notes quarterly" is an ongoing obligation, not a completable task. Kanban tasks must have terminal conditions. Refine to scope this to a single quarterly check (e.g., "Q2 2026 check completed, research doc updated"). Future quarters get new tasks.
2. **Research already completed.** The `## Research` section shows all 3 AC items were satisfied for this cycle. The task is functionally done but structurally cannot be closed because the AC implies permanence.

### Recommended Refine

Rewrite AC to scope a single check cycle:

- ~~Check SDK changelog/release notes quarterly~~ → "Verify SDK v0.2.2 (latest as of 2026-04-15) still lacks `response_format` / completions API"
- ~~If SDK adds...~~ → "Confirm no re-evaluation of Option B is triggered"
- Keep: "Update .owlbear/research/887-...md with findings"
- Add: "Create follow-up tracking task for Q3 2026 if SDK still lacks the feature"
- Tag: `research` (valid pass-through tag)

After user acknowledges the block, refine AC and approve.

### Challenge Results

- Challenger: FALLBACK — not invoked for BLOCK verdicts (per Step 2.5: skip for non-APPROVE)
- Architect response: N/A

### Verdict: BLOCK

### Action Taken: Blocked as `type:user-action`. AC needs scoping to a single check cycle. Research findings already present — task is functionally complete but structurally unclosable with current AC

[[2026-04-15]]

## Archived — Deleted\nRecurring monitoring task with no terminal done state. Not suitable for kanban. User decision: remove
