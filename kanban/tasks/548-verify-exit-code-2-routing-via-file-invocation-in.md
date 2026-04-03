---
id: 548
title: Verify exit code 2 routing via -File invocation in subagent context
status: backlog
priority: nice-to-have
created: 2026-04-02T14:52:11.6630432+02:00
updated: 2026-04-02T17:40:23.0671199+02:00
tags:
    - scope:agents
    - hooks
    - research
    - type:test
blocked: true
block_reason: 'Action request pending: docs/decisions/pending/548-exit-code-2-file-verification.md'
class: standard
---

## Context
See docs/research/posttooluse-subagent-output-routing.md s3.4 (task #532).
The #532 empirical spike found exit code 2 was NOT model-facing when using powershell -Command one-liners. However, #210 uses powershell -File which handles exit codes differently. PS 5.1 -File mode propagates script exit codes as process exit codes. The hooks engine may correctly classify exit code 2 as BlockingError with -File.

## Acceptance Criteria
- [ ] Create a minimal .ps1 script that reads stdin, exits with code 2 and writes to stderr
- [ ] Add as PostToolUse hook to builder.agent.md using -File invocation
- [ ] Record hooks output channel classification (BlockingError vs NonBlockingError)
- [ ] Record whether stderr content appears in Chat Debug View (model-facing)
- [ ] Remove test hook after verification
- [ ] Update docs/research/posttooluse-subagent-output-routing.md with findings

[[2026-04-02]] Thu 17:40
## Research
Theoretical analysis complete. Doc: docs/research/exit-code-2-file-mode-routing.md
Confidence: .60 (lowered from .85 after challenge)

Key finding: PS 5.1 -Command mode converts exit 2 to process exit code 1, explaining #532 NonBlockingError. -File mode preserves exit codes per MS docs, predicting BlockingError for exit 2.

Risks: hooks engine spawn intermediary (cmd.exe wrapping), unproven causal attribution of #532.

Action request: docs/decisions/pending/548-exit-code-2-file-verification.md
User must perform empirical spike to confirm prediction.

[[2026-04-02]] Thu 17:40
## Challenge Results
- Challenger recommendation: reconsider
- Confidence in original: .55
- Key challenges: C1 (hooks engine spawn intermediary), C2 (causal attribution assumed), C3 (.85 too high given 0-for-2 track)
- Researcher response: accepted C1/C2/C3. Lowered confidence to .60.
