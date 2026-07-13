---
id: 994
title: '1c: Add delegation / operational-isolation extraction rule'
status: archived
priority: medium
created: 2026-04-18T21:23:32.421869+00:00
updated: 2026-04-19T12:46:29.338447+00:00
tags:
- type:docs
- scope:skills
parent: 984
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #984

## Objective

Add a rule defining markers for "when to extract a dedicated agent or subagent" to an appropriate authority skill. Location TBD by architect — likely `h-agent-structure` (if about agent structure) or `r-pipeline-protocol` (if about pipeline operations). Precedent: `quality-runner` exists because test-running has many failure modes despite a one-line prose description.

## Content

- Extraction markers (complexity signals, failure-mode count, reuse frequency)
- Operational-isolation criteria (when shared execution context becomes a liability)
- Reference to `quality-runner` as worked example

## Acceptance Criteria

- [ ] Rule is placed in the architecturally appropriate skill file (decided by architect).
- [ ] Defines concrete extraction markers (not vague guidelines).
- [ ] References quality-runner as precedent.
- [ ] Future audits can objectively flag missed extraction opportunities against this rule.
- [ ] No rules duplicated from other skills.

## Files

- `share/skills/h-agent-structure/SKILL.md` OR `share/skills/r-pipeline-protocol/SKILL.md` (architect decides)
[[2026-04-18]]

## Architecture Review

### Verdict: REJECT (Duplicate)

Task #994 is a pre-split duplicate of #1002 ("Add agent-extraction markers to h-agent-structure"), which was created during the architecture review of parent Brief #984. The post-split task #1002 supersedes #994 with:

- Tighter AC (concrete marker counts, format requirements, counter-markers)
- Proper `depends_on: [1000]` (prevents file-conflict with sibling editing the same SKILL.md)
- Correct `agent` tag for pipeline pass-through

The full pre-split set (#992, #993, #994, #995) is superseded by the post-split set (#1000, #1001, #1002, #1003). Recommend archiving all pre-split children to avoid confusion.
[[2026-04-18]]

## Research

**Verdict: Confirmed duplicate — archive.**

# 994 is a pre-split planner artifact superseded by #1002 (created during the architect's formal SPLIT of parent #984). Verified

- #1002 covers identical scope (agent-extraction markers in `h-agent-structure/SKILL.md`)
- #1002 has stricter AC (3-5 markers, 2-3 counter-markers, single-line conditionals, precedent requirement)
- #1002 has correct `depends_on: [1000]` preventing file conflicts
- #1002 has correct `agent` tag for pipeline pass-through
- Parent #984's architecture review lists #1000–#1003 (not #992–#995) as canonical children

No research doc written — duplicate confirmation requires no analysis artifact.

- Sources: 0 external (codebase-only verification)
- Recommendation: archive #994 and all pre-split siblings (confidence: .99)
- Follow-up tasks created: #1011 (archive pre-split set #992–#995)
- Decision requests: none
[[2026-04-18]]

## Architecture Review (2nd pass)\n\n### Verdict: APPROVE (Duplicate — advance for archival)\n\n**Context:** This task completed a full REJECT → research → backlog cycle. Both the prior architecture review and the researcher confirmed #994 is a pre-split duplicate of #1002 (confidence .99). Task #1011 exists to archive the pre-split set (#992–#995).\n\n### Evaluation\n\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | N/A | Duplicate — no work to perform |\n| Interface clarity | N/A | Superseded by #1002 |\n| Dependency correctness | N/A | #1002 has correct depends_on: [1000] |\n| Module layering | N/A | — |\n| TDD compliance | N/A | Pass-through (type:docs) |\n| KISS/YAGNI | N/A | — |\n| Premise challenge | FAIL | Work already covered by #1002 |\n| Pattern consistency | N/A | — |\n| Security surface | N/A | — |\n| Single domain | N/A | — |\n\n### Challenge Results\n- Challenger: SKIPPED — procedural advancement of confirmed duplicate, no architectural decision\n- Architect response: N/A\n\n### Rationale\n\nRejecting again would create an infinite research↔backlog loop (already completed one cycle). The task is tagged `type:docs` ensuring pass-through at test-writer and builder stages. Downstream agents should treat this as a no-op duplicate and advance to archival.\n\n**Canonical replacement:** #1002 (Add agent-extraction markers to h-agent-structure)\n**Archival task:** #1011 (Archive pre-split Brief #984 children)

[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged type:docs) — no tests applicable.
- Passing through to builder.
- Note: Task is a confirmed duplicate of #1002 (pre-split artifact). Builder should treat as no-op and advance for archival per #1011.
[[2026-04-19]]

## Builder Notes

**Pass-through — confirmed duplicate.**

- Files changed: 0
- Tests: N/A (type:docs, no implementation)
- Lint: N/A
- Evidence: #994 is a pre-split artifact superseded by #1002. All pipeline stages (architect ×2, researcher, test-writer) confirmed no-op. Advancing to review for archival per #1011.
[[2026-04-19]]

## Review Evidence

### Test Results

- Quality-Runner: not dispatched — 0 files changed, no code to test or lint.
- Rationale: `type:docs` + confirmed duplicate = no implementation, no tests applicable. Dispatching quality-runner on zero changed files produces no actionable evidence.

### Lint Results

- N/A — no source files modified.

### TestFromAC Modifications

- None. No `TestFromAC_*` files exist for this task (correctly — test-writer passed through).

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|---------|--------|
| Rule placed in architecturally appropriate skill file | Superseded — #1002 covers this scope with stricter AC | N/A (duplicate) |
| Defines concrete extraction markers | Superseded by #1002 | N/A (duplicate) |
| References quality-runner as precedent | Superseded by #1002 | N/A (duplicate) |
| Future audits can objectively flag missed extraction | Superseded by #1002 | N/A (duplicate) |
| No rules duplicated from other skills | Superseded by #1002 | N/A (duplicate) |

### Duplicate Verification

Pipeline consensus (5 stages, unanimous):

- Architect (1st pass): REJECT — pre-split duplicate of #1002
- Researcher: confirmed duplicate, confidence .99, spawned #1011 for archival
- Architect (2nd pass): APPROVE advance for archival — infinite loop risk if rejected again
- Test-writer: pass-through, no tests applicable
- Builder: pass-through, 0 files changed

# 1002 supersedes #994 with tighter AC, `depends_on: [1000]`, and correct `agent` tag. Canonical replacement confirmed active

### Deductions

- Quality-runner not run: justified (0 changed files, no code path to exercise). No deduction warranted — dispatching would produce null results.
- Builder changed 0 files: **correct behavior** for a confirmed duplicate no-op.

### Verdict

Confidence: .96 → **PASS**

Action: advance to docs (pass-through); archival handled by #1011.
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | 0 files changed; confirmed duplicate no-op |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution → sources/overview.md | No | N/A | Researcher: "Sources: 0 external" |
| 4 | CLI changes → README.md | No | N/A | 0 files changed |
| 5 | Research doc | No | N/A | Researcher explicitly noted no research doc needed for duplicate confirmation |
| 6 | No docs impact | Yes | PASS | Confirmed duplicate of #1002; all 5 pipeline stages unanimous pass-through |

### Files Updated

None.

### Scratch Files

`.owlbear/scratch/994-*` — none found.

### Result

No docs impact. Advancing to done for archival per #1011.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Rule placed in appropriate skill file | Superseded by #1002 (archived) | N/A (duplicate) |
| Defines concrete extraction markers | Superseded by #1002 (archived) | N/A (duplicate) |
| References quality-runner as precedent | Superseded by #1002 (archived) | N/A (duplicate) |
| Future audits can flag missed extraction | Superseded by #1002 (archived) | N/A (duplicate) |
| No rules duplicated from other skills | Superseded by #1002 (archived) | N/A (duplicate) |

### Duplicate Verification

- Canonical replacement #1002 confirmed archived (scope: agent-extraction markers in h-agent-structure)
- #1002 had tighter AC, correct depends_on: [1000], correct agent tag
- Parent #984 block_reason references #1000-#1003 (not #992-#995) as canonical children
- Archival task #1011 exists in backlog to clean up pre-split set

### Test Results

- pytest: not dispatched (0 files changed, no code to test)
- ruff: not dispatched (0 source files modified)
- Justification: confirmed duplicate no-op with unanimous 7-stage pipeline consensus. Quality-runner would produce null results.

### Architect Quality: N/A

Pre-split planner artifact — AC was never meant to be implemented. Architect correctly REJECT'd as duplicate on first pass. 2nd-pass APPROVE prevented infinite loop.

### Deduction Breakdown

- Starting: 1.00
- Quality-runner not run: 0 (justified — 0 files changed)
- AC lines N/A: 0 (correctly superseded by archived #1002)
- Reviewer evidence present and detailed: 0

### Confidence: .98

### Action: archive
