---
id: 2057
title: 'P9-03: Install the independent node acceptor workflow'
status: archived
priority: high
created: 2026-07-25T17:19:45.152185+02:00
updated: 2026-07-25T18:23:02.777068+02:00
tags:
  - phase-9
  - scope:agent
  - acceptor
  - orchestrator
  - read-only
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-008
  - packet:DN-008-PK-002
  - interface:IF-009
parent: 1985
depends_on:
  - 2056
ac:
  - 'AC-1: `w-node-acceptance` rehydrates only successful `start_job` identity, engine
    checkout, admitted node authority, current plan, packet receipts, and exact-SHA
    proof; it requires replacements and before/after tracked state, then returns one
    complete `AcceptorSuccess | AcceptanceRejected | AcceptanceBlocked` disposition.'
  - 'AC-2: The `acceptor` agent has no edit or lifecycle tools, uses the read-only
    write guard and tracked-diff check, executes proof only in the engine checkout
    or scratch, and cannot pick, start, finish, release, or approve authored tracked
    changes; agent validation and WIRING inspection prove the boundary.'
  - 'AC-3: `w-orchestration` maps `AcceptorSuccess` fields unchanged to `finish_accept`,
    `AcceptanceRejected` fields unchanged to `reject_accept`, and `AcceptanceBlocked`
    with unchanged identity to `release_job`; orchestrator exposes the acceptor and
    rejection tool, halts after one job, and does not classify findings or assemble
    evidence.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-008-PK-002`. Resolve behavior from REQ-006, WF-004, IF-009, NEG-003, NEG-009, RISK-008, and PROOF-007.

## Outcome
Install one hard-read-only acceptor role, its exact-commit workflow, and deterministic orchestrator routing.

## Envelope
In: workflow, agent declaration, write guard, orchestrator mapping, agent validation, and WIRING.

Out: runtime/MCP semantics, auditor work, setup/seed propagation, and Cockpit.

[[2026-07-25T18:08:40+02:00]]
## Builder Notes
- Added `w-node-acceptance` as the single procedure for one engine-started exact-commit accept job. It rehydrates only successful execution identity, engine checkout, admitted target, current plan, packet receipts, and exact-SHA proof; records allowed replacements and tracked state before/after every command; confines proof to checkout/scratch; and emits one complete `AcceptorSuccess`, `AcceptanceRejected`, or `AcceptanceBlocked`.
- Added `acceptor.agent.md` with read/search/proof execution and read-only native queries only. It has no edit, commit, pick, start, finish, reject, release, recovery, request mutation, or approval tools; `deny-writes.py` guards edit APIs and mandatory tracked-state evidence rejects proof-command writes or later-cleaned authored changes.
- Updated `w-orchestration` to dispatch exactly one successful accept start result, preserve execution identity, and map acceptor-owned fields unchanged to `finish_accept`, `reject_accept`, or `release_job`. The orchestrator does not execute proof, classify findings, plan correction, assemble evidence, alter replacements, or supplement dispositions.
- Added the acceptor delegate and public rejection tool to `orchestrator.agent.md`; updated WIRING role, required-skill, delegation, and hard-control rows.
- AC-1: workflow defines complete exact authority/receipt/proof rehydration, replacements, tracked-state evidence, and all three exhaustive dispositions.
- AC-2: frontmatter plus workflow enforce no edit/lifecycle surface, hard edit guard, checkout/scratch proof, before/after tracked diff, and no approval of authored changes.
- AC-3: orchestration explicitly forwards each success/rejection field unchanged and releases blocked work with unchanged identity; it processes one started job before replanning and owns none of the acceptance judgment.
- Validation: all 18 agents pass `validate_agents.py`; all skills pass `validate_skills.py`; explicit lint over five owned files passed; 37 relevant ecosystem/write-guard tests passed; executable YAML/text inspection proved forbidden-tool absence, hook attachment, delegate/tool reachability, exact mapping language, and WIRING rows. The full live-registry ecosystem assertion remains independently broken by pre-existing `collector.agent.md` declarations for removed task tools and was excluded without changing that unrelated role. Builder challenger decision: pass.

### Required Follow-up
None.

[[2026-07-25T18:13:14+02:00]]
## Verify Notes
- Independent structural and live-tool checks confirmed the declared role, disposition field ownership, orchestration mapping, digest, and ordinary edit-tool guard, but verifier challenger found a concrete hard-read-only defect.
- `git status` plus `git diff` cannot detect a terminal proof command that creates a commit or moves `HEAD`, then leaves the checkout clean. Because the acceptor has generic terminal execution, it could approve acceptor-authored commit state despite the current before/after check.
- This requires a hard terminal mutation guard and focused regression, which exceeds verifier local repair authority and returns to build.
- Evidence already passing: all agent/skill validators; 37 relevant ecosystem/write-guard tests; scoped live acceptor MCP grants; exact digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`. Verifier challenger decision: fail.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | AC-2/terminal-head-mutation | builder | Add a hard acceptor terminal guard that rejects Git commit/reset/checkout and tracked-write attempts before execution; require checkout `HEAD` to remain the supplied candidate SHA before and after every proof command; add focused regression for terminal commit/reset/write attempts and rerun validators. | `.owlbear/hooks/deny-writes.py`, `share/agents/acceptor.agent.md`, `share/skills/w-node-acceptance/SKILL.md`, focused hook tests | verifier-challenger: clean status/diff can hide a commit or moved-and-reset HEAD |

[[2026-07-25T18:18:13+02:00]]
## Builder Notes
- Resolved `AC-2/terminal-head-mutation` at the hard-control owner. `deny-writes.py` now has an acceptor-only `--terminal-read-only` mode; default behavior remains unchanged for every existing role.
- Terminal-read-only mode fails closed on Git: only explicit inspection subcommands are allowed, so commit, reset, checkout, update-ref, custom aliases, and other unknown Git operations are denied before execution. It also denies explicit shell filesystem mutators/redirection, in-place sed/perl, and common inline scripting writes.
- `acceptor.agent.md` opts into terminal-read-only mode. `w-node-acceptance` now records and rechecks `git rev-parse --verify HEAD` against the engine candidate plus status excluding untracked scratch and `git diff --binary HEAD --` after every proof command, covering moved HEAD and staged/unstaged tracked bytes.
- Added focused regressions for commit, reset, checkout, update-ref, custom alias, chmod, redirection, and inline `Path.write_text`; read-only Git plus pytest remains allowed, and default guard mode is proven unaffected. Updated WIRING hard-control description.
- Durable-test justification: terminal execution bypassed the edit-tool hook and could silently approve acceptor-authored commit state; this independence/data-integrity boundary is hard to inspect manually and the focused hook test is cheaper than repeated command review.
- Validation: all 18 agents and all skills validate; 47 relevant ecosystem/write-guard tests pass; explicit lint over all five repair files passes. The unrelated global registry assertion still fails on pre-existing removed legacy task grants and remains untouched. Builder challenger decision: pass.

### Required Follow-up
None.

[[2026-07-25T18:22:18+02:00]]
## Verify Notes
- Reverified the full acceptor workflow and hard-control boundary across builder commits `d0d91497` and `8f083f1b`, resolving prior failure key `AC-2/terminal-head-mutation`.
- AC-1: confirmed successful-start/checkout/authority/plan/receipt/exact-SHA rehydration, disclosed replacements, complete tracked-state evidence, and exactly three complete dispositions.
- AC-2: confirmed no edit or native lifecycle tools, acceptor-only terminal-read-only hook mode, fail-closed Git inspection allowlist, denial of explicit filesystem writes/redirections, exact candidate `HEAD`, staged index, and unstaged tracked-worktree checks after every command, plus no approval or cleanup of authored changes.
- AC-3: confirmed one-job dispatch and unchanged acceptor-owned field forwarding to `finish_accept`, `reject_accept`, or identity-preserving `release_job`; orchestration retains no proof, finding, correction, replacement, or evidence judgment.
- Independently repaired two local guard parser bypasses reported by the verifier challenger: Git `--output` options and Bash `&>` redirection are now denied, with focused unit and real subprocess evidence. The challenger passed after this repair.
- Final validation: all 18 agents and all skills validate; 54 relevant write-guard, ecosystem, and setup-hook tests pass; explicit lint over all seven packet files passes; VS Code diagnostics are clean. The unrelated aggregate registry assertion still fails only on pre-existing legacy task grants and was not used as evidence.

### Required Follow-up
None.

[[2026-07-25T18:23:02+02:00]]
## Collect Notes
- Confirmed complete role history across initial builder `d0d91497`, verifier rejection `b448488d`, hard-control repair `8f083f1b`, and passing verifier `b2d5b16a`; `AC-2/terminal-head-mutation` is explicitly resolved and no required follow-up remains.
- Confirmed dependency #2056 is archived completed and no pending structured request exists.
- Closure covers all ACs: complete exact-commit acceptance dispositions; hard role/tool/hook/HEAD/index/worktree independence; and one-job field-preserving orchestration to finish, reject, or release without acceptance judgment.
- Final evidence is 54 passing guard/ecosystem/setup tests, all 18 agent and all skill validators, explicit lint over the complete packet, clean diagnostics, live new-tool resolution, real subprocess denial checks, and verifier challenger pass.
- The unrelated aggregate registry assertion remains a pre-existing legacy task-tool mismatch and does not affect the new acceptor or rejection surface.

### Required Follow-up
None.
