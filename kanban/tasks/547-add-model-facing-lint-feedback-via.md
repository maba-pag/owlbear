---
id: 547
title: Add model-facing lint feedback via additionalContext to builder PostToolUse hook
status: todo
priority: important
created: 2026-04-02T14:52:03.1922694+02:00
updated: 2026-04-02T16:36:08.7877861+02:00
tags:
    - scope:agents
    - hooks
    - type:build
depends_on:
    - 210
class: standard
---

## Context
See docs/research/posttooluse-additionalcontext-lint-feedback.md (task #547).
Empirical verification (#532) confirmed PostToolUse additionalContext reaches the subagent model context (wrapped in PostToolUse-context XML tags). The builder's lint guard (#210) uses systemMessage (user-facing only). This task adds additionalContext output so the builder model receives lint feedback and can self-correct.

## Acceptance Criteria
- [ ] When ruff finds errors, lint-changed.ps1 returns JSON with both `systemMessage` (existing) and `hookSpecificOutput` containing `hookEventName: PostToolUse` and `additionalContext` with the ruff output text
- [ ] Output JSON structure: `{ systemMessage: <ruff>, hookSpecificOutput: { hookEventName: PostToolUse, additionalContext: <ruff> } }`
- [ ] When ruff finds no errors: returns empty JSON `{}` (no additionalContext for clean results)
- [ ] Existing systemMessage behavior preserved unchanged
- [ ] Never exits with code 2 (non-blocking)
- [ ] Same ruff output text used for both systemMessage and additionalContext (no separate formatting)

## Verification Note
Model-facing delivery (additionalContext appearing as `<PostToolUse-context>` tags in Chat Debug View) requires manual observation during a live builder session. This is a post-implementation verification step, not a reviewer-testable criterion. Create an action request after builder completes if manual verification is needed.

## Implementation Notes
Output JSON structure when ruff finds errors:
`{ systemMessage: ruff_output, hookSpecificOutput: { hookEventName: PostToolUse, additionalContext: ruff_output } }`
Same ruff output for both fields (KISS). No truncation initially (YAGNI).

## Dependencies
Depends on #210 (lint-changed.ps1 must exist first).

[[2026-04-02]] Thu 16:35
## Architecture Review
**Verdict:** Approve
**DR Verification:** N/A -- T1 classification (no new capability, no architecture change). Research doc classifies as autonomous.

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| hookSpecificOutput.additionalContext with ruff output | Clear deliverable, JSON structure specified | Refined (added hookEventName, JSON schema) |
| hookEventName: PostToolUse included | NEW -- required per VS Code hooks spec and #532 probe | Added |
| Clean path returns empty JSON | NEW -- explicit clean-path criterion (no noise) | Added |
| systemMessage preserved | Verifiable via script test | Kept |
| Never exits code 2 | Deliberate non-blocking design | Kept |
| Same ruff output for both fields | KISS constraint -- no dual formatting | Added |
| Chat Debug View verification | Reframed as post-impl verification note (not reviewer-testable) | Reframed |

### Architecture Notes
- Single-file change: modifies lint-changed.ps1 output format (created by #210)
- No agent file changes needed -- hook command stays the same, script changes output JSON
- additionalContext confirmed model-facing by #532 empirical verification (N=1, create_file)
- VS Code docs unambiguous on hookSpecificOutput schema
- #546 (apply_patch filter) is orthogonal: changes WHEN lint runs, not WHAT output looks like. No ordering dependency needed.
- type:build tag correct -- testable script code changes

### Changes Made
- Rewrote AC body: 4 lines expanded to 6 precise lines with JSON schema, hookEventName, clean-path criterion
- Added Verification Note section (manual Chat Debug View check is post-impl, not AC)
- Added Implementation Notes with JSON structure
- Fixed depends_on: added #210 (was missing from frontmatter)
- Merged #549 (duplicate follow-up from research doc s5) into #547. Deleted #549.

### Dependencies
- Added: depends_on #210 (lint-changed.ps1 must exist before modification)
- Verified: #210 is in-progress (not yet complete -- #547 blocked until #210 ships)
- Orthogonal: #546 (apply_patch filter) -- no ordering dependency

### Challenge Results
- Challenger: block (.45 confidence in original)
- Key challenges: C1 (duplicate #549), C2 (missing depends_on), C3 (AC2 not testable), C4 (#546 ordering), C5 (AC not written to body), C6 (N=1 basis)
- Architect response:
  - C1 ACCEPTED: #549 deleted, merged into #547 (refined AC absorbed)
  - C2 ACCEPTED: depends_on [210] added to frontmatter
  - C3 ACCEPTED partially: AC2 reframed as post-impl verification note. Remaining AC lines are mechanically testable
  - C4 REBUTTED: #546 and #547 are order-independent. #546 tests tool_name triggering + systemMessage; #547 tests output structure. systemMessage preserved by both
  - C5 ACCEPTED: Refined AC written to task body before approval
  - C6 NOTED: N=1 is documented risk (.75 confidence in research). VS Code docs are unambiguous. Not blocking
- Confidence in original (revised): .80 -- all critical structural defects fixed in this cycle
