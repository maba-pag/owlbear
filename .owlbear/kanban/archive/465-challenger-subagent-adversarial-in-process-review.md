---
id: 465
title: Challenger subagent — adversarial in-process review for architect 
  decisions
status: archived
priority: medium
created: 2026-03-31 04:06:56.771288+02:00
updated: 2026-04-01 02:17:18.467254+02:00
started: 2026-04-01 02:17:13.640931+02:00
completed: 2026-04-01 02:17:13.640931+02:00
tags:
- research
- ' scope:agents'
- ' phase-2'
class: standard
archival_reason: completed
archival_refs: []
---

## Context

Pipeline agents (especially architect) make high-stakes decisions in isolation. Bad AC from the architect cascades to builder, reviewer, auditor — the most expensive failure mode in the pipeline. The reviewer catches code quality issues post-hoc, but cannot challenge the reasoning behind architectural decisions.

Proposal: a **Challenger** subagent — an adversarial discussion partner that runs as an L2 subagent during an agent's work. Unlike the closed #681 evaluator (post-hoc result assessment at orchestrator level), the Challenger operates **in-process**, challenging reasoning **before** the decision is committed. Think Socratic devil's advocate, not quality gate.

**Interaction model:** One-shot challenge report (VS Code subagents return once). The consuming agent sends its reasoning and proposed decision; the Challenger returns a structured adversarial analysis (holes, biases, missing alternatives, risk blind spots). The consuming agent digests the challenge and may revise. Multi-turn debate is a future opt-in after the pattern proves itself.

**Trigger model:** Mandatory at critical gates. For the architect, this means every APPROVE verdict must pass through the Challenger first. Optional invocation may be added for lower-stakes decisions.

**Initial consumer:** Architect agent (highest stakes — design decisions are hardest to reverse). Future expansion to researcher, test-writer, writer after the pattern is proven.

Infrastructure: uses subagent nesting confirmed in #228 (L2 depth, `allowInvocationsFromSubagents` already enabled). Independent of Quality-Runner (#263) and parallel fan-out (#265).

## Acceptance Criteria

- [ ] Define the Challenger agent persona and adversarial reasoning style (what makes it different from general review — structured devil's advocate, not validation)
- [ ] Design the I/O contract: input schema (agent reasoning, proposed decision, context) and output schema (challenges, blind spots, alternative angles, risk assessment, confidence in the original decision)
- [ ] Determine tool requirements and mode (assign vs inherit). The Challenger needs to read code/files to verify claims but should not edit anything
- [ ] Identify mandatory trigger points in the arch-review workflow (where exactly the challenge must happen before APPROVE)
- [ ] Evaluate model selection: adversarial reasoning may benefit from a strong model vs. cost savings of a lighter one
- [ ] Design the protocol for how the architect integrates the challenge results (revise AC, strengthen reasoning, or acknowledge and proceed with justification)
- [ ] Assess expansion path: identify critical gates in researcher, test-writer, and writer workflows where mandatory challenge would add value
- [ ] Create follow-up implementation tasks at ideation (challenger.agent.md, arch-review skill integration, expansion tasks)
- [ ] Write design doc to docs/research/challenger-subagent-design.md

[[2026-03-31]] Tue 16:34
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** No formal T3 DR exists for #465. Gap noted but not blocking: implementation (#467) already architect-approved and auditor-archived at .98. Retroactive DR would be process theater. Recommend creating DRs earlier in future new-capability research.

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Define persona and reasoning style | Clear, verifiable. Maps to S3c, S3i in research doc | Keep |
| Design I/O contract (input + output schema) | Clear. Maps to S3d. 6 input fields, 6 output sections enumerated | Keep |
| Determine tool requirements and mode | Clear. Maps to S3c. Assign mode, 5 read-only tools | Keep |
| Identify mandatory trigger points | Clear. Maps to S3e. APPROVE mandatory, REFINE optional | Keep |
| Evaluate model selection | Clear. Maps to S3g. Opus 4.6 recommended with rationale | Keep |
| Design integration protocol | Clear. Maps to S3f. 3-path protocol (proceed/reconsider/block) | Keep |
| Assess expansion path | Clear. Maps to S3h. Phase 2: researcher, test-writer. Skip: writer | Keep |
| Create follow-up tasks at ideation | Verified: #467 (archived), #468 (backlog), #469 (ideation) | Keep |
| Write design doc | Verified: docs/research/challenger-subagent-design.md exists, complete | Keep |

### Architecture Notes
Research quality is high (.85 stated confidence). Grounded in academic sources (Du et al. 2023, Liang et al. 2024) and internal validated research (#228 nesting, #681 evaluator disposition). All design decisions are well-reasoned with explicit trade-off tables. The one-shot model is the right KISS approach for VS Code subagent constraints. Code-reader precedent validated for assign-mode read-only pattern.

Task has 
esearch tag for test-writer pass-through. No implementation code produced by this task.

T3 process gap: new capability research should require a DR before follow-up tasks are created at ideation. The pipeline allowed #467 to race ahead without a DR. Not blocking because the work is done, but this is a lessons-learned item.

### Changes Made
- Approved to todo (no AC changes needed, all lines are verifiable)

### Dependencies
- Verified: no depends_on in frontmatter
- #467 (implementation) already archived
- #468 (integration) in backlog, depends on #467 (met)
- #469 (expansion) in ideation, depends on #468

[[2026-03-31]] Tue 17:30
## Test-Writer Notes
- Non-implementation task (tagged research) -- no tests applicable.
- Passing through to builder.

[[2026-04-01]] Wed 01:25
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Research-only task; no behavior change. Challenger implementation was #467 (archived). |
| 2 | Docstrings | No | N/A | No Python code produced. |
| 3 | docs/sources/overview.md | Yes | Pass | Section present at line 2638 with 4 attributed sources (Du et al., Liang et al., Chan et al., VS Code docs). |
| 4 | README.md | No | N/A | No CLI changes. |
| 5 | Research doc | Yes | Pass | docs/research/challenger-subagent-design.md exists; architect confirmed. Follow-up tasks: #467 archived, #468 backlog, #469 ideation. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/465-* files found)

[[2026-04-01]] Wed 02:17
## Audit
### AC Verification
9/9 AC lines PASS. Each maps to research doc section (S3c-S3i) or verified deliverable.

### Research Task Verification
- Research doc exists: PASS (docs/research/challenger-subagent-design.md)
- Follow-up tasks created: PASS (#467 archived, #468 archived, #469 backlog)
- Follow-up tasks reference research doc: PASS
- Sources attributed: PASS (docs/sources/overview.md line 2638, 4 sources)

### Test Results
- pytest (full suite): 2369 passed, 243 failed, 7 skipped (no failures in task scope)
- ruff: 2 violations in unrelated file

### Upstream Commit Gaps
- docs/research/challenger-subagent-design.md UNTRACKED (researcher did not commit)
- docs/sources/overview.md uncommitted #465 attribution (writer did not commit)

### AC Quality Score: 4/5
AC mapped cleanly to research doc sections. Minor: verbs could be more concrete.

### Deduction breakdown
- -.02 no reviewer evidence section
- -.02 research doc + sources uncommitted
### Confidence: .96
### Action: archive
