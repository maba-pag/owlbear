---
id: 951
title: Inject runtime task and workspace context into dispatched agent prompts
status: archived
priority: important
created: 2026-03-23T01:43:14.0612922+01:00
updated: 2026-03-23T04:17:19.813144+01:00
started: 2026-03-23T03:43:52.483367+01:00
tags:
    - agent
    - scope:copilot
    - scope:core
    - type:build
parent: 947
blocked: true
block_reason: 'Split into #958, #959, #960, #961 - work tracked there'
class: standard
---

See docs/research/ruflo-analysis.md section 5. AC: dispatched OwlBear agents receive current task, workspace, and channel context through a runtime prompt-assembly layer without duplicating static prompt text across files.

[[2026-03-23]] Mon 03:43

## Research

Doc: docs/research/dispatched-agent-runtime-context.md

Key findings:

- OwlBear already has a proven runtime seam in `src/owlbear/core/agent.py`: `OwlBearAgent.turn()` concatenates dynamic context into per-run `instructions=`.
- `src/owlbear/core/delegation.py` currently forwards only delegated task text plus deps and usage.
- `src/owlbear/daemon.py` duplicates builder prompt assembly in fresh and retry branches and currently omits a shared runtime context layer for child-agent runs.
- Recommendation: add one shared runtime dispatch builder that formats optional Current Task, Workspace, and Channel blocks into per-run `instructions=` and optional `metadata=`.
- Keep WIP summaries and pre-hydrated task references in the main prompt body; the runtime layer should carry only dispatch environment.
- No new follow-up tasks created: #951 itself is the implementation task.

Attribution:

- External sources for this task were logged in docs/sources/overview.md.

Refined AC:

1. Add a runtime dispatch-context carrier with workspace_root, channel_name, and optional task metadata.
2. Add one shared formatter that turns that carrier into per-run `instructions=` and optional `metadata=`.
3. Update `DelegationToolset._delegate()` to pass the shared runtime context while preserving usage passthrough and depth increment.
4. Update daemon `poll_tick()` retry and fresh-dispatch branches to use the same formatter and the same deps shape.
5. Leave markdown agent definitions unchanged; do not duplicate task/workspace/channel text across agent files.
6. Keep WIP and pre-hydrated task content in the main prompt, not the runtime instruction layer.
7. Add or update tests in the existing delegation and daemon suites for both fresh and retry dispatch paths.

[[2026-03-23]] Mon 04:17

## Architecture Review

**Verdict:** SPLIT -> #958, #959, #960, #961

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Add a runtime dispatch-context carrier with workspace_root, channel_name, and optional task metadata. | Correct goal, but it conflicts with the archived #153 rule that raw workspace_root and session should not be reopened as loose deps fields. This belongs to the core dispatch contract, not the daemon wiring task. | Split into #958 and #959 and preserve a narrow immutable dispatch-context carrier. |
| 2. Add one shared formatter that turns that carrier into per-run instructions= and optional metadata=. | Precise, but it is the shared core contract other call sites should consume rather than re-define. | Split into #958 and #959. |
| 3. Update DelegationToolset._delegate() to pass the shared runtime context while preserving usage passthrough and depth increment. | Single, verifiable core change in src/owlbear/core/delegation.py with a dedicated test seam in tests/test_delegation.py. | Split into #958 and #959. |
| 4. Update daemon poll_tick() retry and fresh-dispatch branches to use the same formatter and the same deps shape. | Separate bootstrap seam in src/owlbear/daemon.py with duplicated builder.run(prompt) call sites; keeping it on the same card breaks the single-domain rule. | Split into #960 and #961. |
| 5. Leave markdown agent definitions unchanged; do not duplicate task/workspace/channel text across agent files. | Good invariant, but it constrains both child implementations rather than describing one executable change. | Preserve as a binding constraint across #959 and #961. |
| 6. Keep WIP and pre-hydrated task content in the main prompt, not the runtime instruction layer. | Daemon-specific invariant tied to poll_tick() prompt assembly and hydration tests, not the delegation contract. | Split into #960 and #961. |
| 7. Add or update tests in the existing delegation and daemon suites for both fresh and retry dispatch paths. | This mixes two RED phases and two implementation seams on one implementation card, with no predecessor test task. | Split into RED tasks #958 and #960; make #959 depend on #958 and #961 depend on #960. |

### Architecture Notes

- src/owlbear/core/agent.py already proves the runtime-instructions pattern by concatenating per-run context into instructions= at call time; the new work should reuse that seam rather than copy mutable text into agent markdown.
- src/owlbear/core/delegation.py currently forwards only deps= and usage= to agent.run(...), so the shared runtime carrier and formatter are a core concern with their own test surface in tests/test_delegation.py.
- src/owlbear/daemon.py duplicates builder.run(prompt) in both retry and fresh-dispatch branches inside poll_tick(), which is a separate bootstrap concern with its own test surface in tests/test_daemon_coverage_gaps.py, tests/test_poll_dispatch.py, and tests/test_hydration_integration.py.
- src/owlbear/core/deps.py and archived task #153 deliberately kept raw workspace_root and session out of plain OwlBearDeps. Any propagation here must stay as a narrow immutable dispatch-context object rather than reopening broad per-agent state.
- src/owlbear/bootstrap/**init**.py already has the runtime sources for workspace and channel identity, but that does not make the daemon wiring ancillary; it is still a separate runtime entrypoint from delegation and must be tracked as its own bootstrap task.

### Changes Made

- Created #958: Test dispatch-context carrier and delegation runtime instructions.
- Created #959: Implement dispatch-context carrier and delegation runtime instructions, depends on #958.
- Created #960: Test daemon dispatch runtime context reuse, depends on #959.
- Created #961: Implement daemon dispatch runtime context reuse, depends on #960.
- Blocked #951 as the umbrella so execution proceeds on the child tasks instead of a cross-domain implementation card.

### Dependencies

- Verified: docs/research/dispatched-agent-runtime-context.md, src/owlbear/core/agent.py, src/owlbear/core/delegation.py, src/owlbear/core/deps.py, src/owlbear/daemon.py, src/owlbear/bootstrap/**init**.py, tests/test_delegation.py, tests/test_daemon_coverage_gaps.py, tests/test_poll_dispatch.py, and tests/test_hydration_integration.py.
- Added: #958 -> #959 -> #960 -> #961.
- Missing on the umbrella: a preceding RED task. The split restores TDD compliance.
