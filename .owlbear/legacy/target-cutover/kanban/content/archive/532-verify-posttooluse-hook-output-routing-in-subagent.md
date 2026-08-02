---
id: 532
title: Verify PostToolUse hook output routing in subagent context
status: archived
priority: medium
created: 2026-04-01 20:37:14.013663+02:00
updated: 2026-04-02 20:50:42.362222+02:00
started: 2026-04-01 21:26:02.031371+02:00
completed: 2026-04-02 20:50:41.848545+02:00
tags:
- scope:agents
- hooks
- research
- type:test
class: standard
archival_reason: completed
archival_refs: []
---

## Context
See docs/research/posttooluse-lint-guard-feasibility.md section 3.2.
The #209 cycle proved that hook output routing assumptions must be verified empirically before building. PostToolUse additionalContext and systemMessage routing to subagent models is undocumented.

## Acceptance Criteria
- [ ] Add a minimal PostToolUse hook to builder.agent.md returning a fixed additionalContext string and a fixed systemMessage string
- [ ] Run the builder agent on a throw-away task that edits a file
- [ ] Document which output (additionalContext, systemMessage, neither, both) appears in the builder model context
- [ ] Document which output (if any) appears in the orchestrator chat panel
- [ ] Remove the test hook after verification
- [ ] Update docs/research/posttooluse-lint-guard-feasibility.md with empirical findings

[[2026-04-01]] Wed 21:25
## Research
Theoretical analysis complete. See docs/research/posttooluse-subagent-output-routing.md
Confidence DEFERRED (.55 theoretical framework). Action request: docs/decisions/pending/532-posttooluse-subagent-verification.md

## Challenge Results
Challenger: block (.35). Accepted C2/C3, deferred all confidence scores.

Theoretical analysis complete. User must perform empirical spike.

[[2026-04-02]] Thu 14:54
## Research (empirical completion)
Empirical verification complete. Doc: docs/research/posttooluse-subagent-output-routing.md

Key findings:
- additionalContext: CONFIRMED model-facing (Chat Debug View shows PostToolUse-context XML tags)
- systemMessage: user-facing only (consistent with #209)
- Exit code 2: NOT model-facing via -Command one-liners (PS 5.1); behavior via -File untested
- decision:block+reason: untested

Follow-up tasks created:
- #546: Add apply_patch to #210 tool_name filter (needed)
- #547: Add model-facing lint feedback via additionalContext (important)
- #548: Verify exit code 2 via -File invocation (nice-to-have)

Challenge: reconsider (.55). Accepted C1-C4, lowered confidence from .90 to .80.
Feasibility doc updated with empirical corrections (s6).

[[2026-04-02]] Thu 15:50
## Architecture Review
**Verdict:** Approve
**DR Verification:** docs/decisions/resolved/532-posttooluse-subagent-verification.md completed: true (action request, not decision request)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add minimal PostToolUse hook to builder.agent.md | Verifiable: binary check. User added probe hooks per action request. | Kept |
| Run builder on throw-away task | Verifiable: binary check. User performed empirical spike. | Kept |
| Document which output appears in builder model context | Verifiable: research doc s3.2-3.3. additionalContext=YES, systemMessage=NO, exit code 2=NO (-Command). | Kept |
| Document which output appears in orchestrator chat panel | Verifiable: research doc s3.2. systemMessage appears in chat panel (user-facing). | Kept |
| Remove test hook after verification | Verifiable: no PROBE/hooks/PostToolUse references in builder.agent.md (confirmed via grep). | Kept |
| Update feasibility doc with empirical findings | Verifiable: posttooluse-lint-guard-feasibility.md s6 added with corrections to s3.2 and s4. | Kept |

### Architecture Notes
- Task is a completed research/empirical-verification spike. No code to build.
- Tags: research + type:test = test-writer pass-through, builder verifies deliverables only.
- All 6 AC items already satisfied by user empirical spike + researcher documentation.
- Deliverables: posttooluse-subagent-output-routing.md (complete), feasibility doc s6 (updated), follow-ups #546/#547/#548 (created at ideation).
- Known limitation: action request notes field is empty; empirical chain depends on researcher transcription from user session. No independent verification artifact exists.
- Risk: #210 (in-progress) has stale tool_name filter missing apply_patch. #546 exists to fix this but is at ideation. Gap is non-critical: #210 is monitoring-only (systemMessage), not enforcement. Cannot modify #210 from this review (not dispatched for it).

### Changes Made
- No AC changes needed (all lines already precise and verifiable)

### Dependencies
- No depends_on changes. Follow-up tasks #546, #547, #548 at ideation track downstream work.

### Challenge Results
- Challenger: reconsider (.60)
- Key challenges: C1 (empty action-request notes), C2 (#210 race with apply_patch gap), C3 (N=1 confidence), C4 (stale risk table in feasibility doc s3.3), C5 (decision:block untested)
- Architect response: C1 accepted (noted as known limitation); C2 accepted partially (cannot modify #210, #546 tracks fix, gap is non-critical for monitoring-only tool); C3 rebutted (binary question with clear XML tag evidence, doc self-qualifies N=1); C4 accepted (minor doc polish, not blocking); C5 rebutted (out of scope)
- Confidence in original: .75

[[2026-04-02]] Thu 16:57
## Test-Writer Notes
- Non-implementation task (tagged research, type:test) — no tests applicable.
- Architecture Review confirms: completed empirical-verification spike, no Python implementation.
- All 6 AC items satisfied by user empirical spike + researcher documentation.
- Passing through to builder.

[[2026-04-02]] Thu 17:47
## Builder Notes
- Non-implementation task â€” no code changes needed.
- All 6 AC items satisfied by user empirical spike + researcher documentation (verified from task body).
- Passing through to review.

[[2026-04-02]] Thu 18:59
## Review Evidence

**Reviewer:** reviewer | **Date:** 2026-04-02

### Task Type
Research/empirical-verification spike. No Python implementation, no TestFromAC classes. Pass-through through test-writer and builder.

### Test Results
N/A -- no Python files changed by this task. ruff check docs/: All checks passed.

### Changed Files
- docs/research/posttooluse-subagent-output-routing.md (new)
- docs/research/posttooluse-lint-guard-feasibility.md (new with s6)
- kanban/tasks/532-* (board metadata)
No Python files modified.

### TestFromAC Audit
Skipped -- no TestFromAC_ classes (non-implementation task, correct per architecture review).

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Add minimal PostToolUse hook to builder.agent.md | Research doc s3.1 documents Probe A + B added per completed action request (docs/decisions/resolved/532-posttooluse-subagent-verification.md, completed:true) | PASS |
| Run builder on throw-away task that edits a file | Action request completed. Research doc s3.1 documents test protocol and results. Specific probe strings (PROBE_ADDITIONAL_CONTEXT_532) confirm real execution | PASS |
| Document which output appears in builder model context | Research doc s3.2-3.3: additionalContext=YES (Chat Debug View XML tags confirmed), systemMessage=NO (inferred #209), exit code 2=NO (-Command mode) | PASS |
| Document which output appears in orchestrator chat panel | Research doc s3.2 results matrix: systemMessage user-facing=YES (inferred #209), exit code 2 stderr user-facing=YES (as warning) | PASS |
| Remove test hook after verification | grep (all files incl. ignored) for PostToolUse/PROBE in agents/builder.agent.md: 0 matches (only unrelated 'hooks.py' reference at line 134) | PASS |
| Update posttooluse-lint-guard-feasibility.md with empirical findings | Section 6. Empirical Update (2026-04-02, task #532) confirmed at line 98. Corrects s3.2 and s4 recommendations | PASS |

### Follow-Up Tasks Verified
- #546 (backlog/needed): add apply_patch to tool_name filter -- confirmed present
- #547 (todo/important): additionalContext lint feedback -- confirmed present, architect-approved
- #548 (backlog/nice-to-have): verify exit code 2 via -File -- confirmed present, blocked on action request

### Builder Process Quality: CLEAN
One Builder Notes section, pass-through with clear rationale.

### Known Limitation (Acknowledged)
Action request notes field empty; empirical chain depends on researcher transcription. Observable artifacts in research doc (specific XML tags, probe strings) provide sufficient evidence. N=1 confidence documented in doc.

### Verdict: PASS

Confidence: .93

[[2026-04-02]] Thu 20:50
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Add minimal PostToolUse hook to builder.agent.md | Research doc s3.1 documents Probe A+B per completed action request (resolved/532) | PASS |
| Run builder on throw-away task | Action request completed:true. Research doc s3.1 test protocol | PASS |
| Document which output appears in builder model context | Research doc s3.2-3.3: additionalContext YES (XML tags), systemMessage NO, exit code 2 NO | PASS |
| Document which output appears in orchestrator chat panel | Research doc s3.2: systemMessage user-facing YES | PASS |
| Remove test hook after verification | grep PROBE/PostToolUse in builder.agent.md: 0 matches | PASS |
| Update feasibility doc with empirical findings | posttooluse-lint-guard-feasibility.md s6 confirmed at line 98 | PASS |

### Research Task Verification
- Research doc: docs/research/posttooluse-subagent-output-routing.md (exists, complete)
- Follow-ups: #546 (backlog/needed), #547 (todo/important), #548 (backlog/nice-to-have) all confirmed on board
- Follow-ups reference research doc in body
- Feasibility doc s6 updated with empirical corrections
- Resolved action request: docs/decisions/resolved/532-posttooluse-subagent-verification.md (completed:true)

### Test Results
- pytest: 2499 passed, 355 failed (all pre-existing from other tasks, 0 in #532 scope)
- ruff: pre-existing issues only (E902 system, PT018 in unrelated test), 0 from #532

### AC Quality Score: 4
AC was specific with 6 binary-verifiable items. Minor gap: did not anticipate N=1 limitation or decision:block+reason as testable items, but follow-up #548 exists.

### Deduction breakdown
- AC lines without evidence: 0 (all 6 PASS)
- Lint issues from task: 0
- AC quality (4, above 3): 0
- Reviewer evidence section: present and detailed (0)
- Full-suite failures in scope: 0
- Total deductions: 0

### Confidence: .98
All 6 AC items verified with evidence. Minor -.02 for N=1 qualification (single tool_name tested) acknowledged in research doc but not strictly an AC gap.

### Action: archive
