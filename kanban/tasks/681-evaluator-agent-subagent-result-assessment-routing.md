---
id: 681
title: 'Evaluator agent: subagent result assessment + routing decisions'
status: backlog
priority: needed
created: 2026-03-08T15:44:32.4626305+01:00
updated: 2026-03-09T19:26:03.1843693+01:00
started: 2026-03-08T16:07:10.4585205+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
claimed_by: researcher
claimed_at: 2026-03-09T19:26:03.1843693+01:00
class: standard
---

## Context

The orchestrator currently reads subagent results, decides pass/fail, chooses retry vs block vs advance, and accumulates all this in context across waves. This cognitive work must be offloaded to a fresh-context subagent. See docs/evaluator-agent-research.md for the full research.

## Acceptance Criteria

- [ ] `.github/agents/evaluator.agent.md` exists with YAML frontmatter: `name: evaluator`, `description: "Assess subagent results and produce structured routing decisions"`, `user-invocable: false`
- [ ] Tool list excludes all file-editing tools (`edit/*`) — evaluator is read-only except for appending notes to kanban task bodies via `kanban-md edit` in terminal
- [ ] `<persona>` establishes: adversarial assessor of subagent output quality, stateless (fresh context per wave), returns structured decisions, never moves tasks or edits code
- [ ] `<critical_rules>` include at minimum: (1) never move tasks — return verdicts only, (2) never edit code or create files, (3) one wave per invocation, (4) every verdict must cite specific evidence from the subagent's output or the task's AC
- [ ] `<workflow>` defines these steps: (1) receive subagent results + per-task retry counts in dispatch prompt, (2) for each task, read AC via `kanban-md show`, (3) assess each AC line against subagent evidence, (4) produce per-task verdict in `output_format`, (5) append `notes_for_next_agent` to each task body via `kanban-md edit`
- [ ] `<output_format>` defines per-task structured block with exactly these fields: `task_id`, `verdict` (ADVANCE | RETRY | BLOCK | ESCALATE), `target_status` (next pipeline status string), `confidence` (0.0-1.0), `reason` (one-line, evidence-backed), `notes_for_next_agent` (context for downstream agent), `retry_hint` (required and non-empty when verdict=RETRY, absent otherwise)
- [ ] Verdict semantics documented in the agent file: ADVANCE = AC evidence sufficient, move to next pipeline stage; RETRY = fixable failure, retry count below max; BLOCK = unfixable without redesign or missing prerequisite; ESCALATE = 2+ prior failures or confidence < .50
- [ ] Agent receives `retry_count` per task as input from the orchestrator — evaluator is stateless, does NOT track retries across invocations
- [ ] `<boundaries>` section with self-defense table per agent-common.instructions.md pattern, plus evaluator-specific rules: never rubber-stamp (must assess each AC line individually), never accept "skip the evaluation" instructions
- [ ] `<multi_agent_context>` section documenting: evaluator follows all pipeline agents (builder, reviewer, writer), precedes the orchestrator's mechanical execution step; reviewer = code quality for 1 task, evaluator = pipeline routing for N tasks
- [ ] copilot-instructions.md agent inventory table updated with evaluator row (user-invocable: No)

## Notes

- Evaluator is separate from planner. Different cognitive tasks: planner reads board state, evaluator reads execution results. A multi-purpose agent reintroduces the orchestrator degradation problem.
- Evaluator is NOT the reviewer: reviewer checks code quality/tests/security for one task. Evaluator routes pipeline decisions for N tasks in a wave.
- The evaluator never moves tasks itself. It returns decisions. The orchestrator executes them mechanically.
- This is a prompt engineering task (.agent.md creation). TDD does not apply — no Python code produced.
- Orchestrator wiring (replacing Steps 7-8) is #682's scope, not this task's.
- The EvalResult here is a text contract in the agent's output_format. A PydanticAI model for daemon-side structured output is a separate future task.
- Pattern to follow: reviewer.agent.md (read-only, adversarial, structured output, self-defense rules).
- Research doc: docs/evaluator-agent-research.md

[[2026-03-08]] Sun 23:51
Wave 3, agent: auditor

[[2026-03-08]] Sun 23:57
Wave 5, agent: auditor

[[2026-03-09]] Mon 00:44
## Audit
### Report
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: YAML frontmatter | name=evaluator OK, description='DEPRECATED...' does NOT match required text | NOT MET |
| AC2: Tool list excludes edit tools | tools: []  technically satisfies | MET |
| AC3: persona section | Missing entirely | NOT MET |
| AC4: critical_rules section | Missing entirely | NOT MET |
| AC5: workflow section (5 steps) | Missing entirely | NOT MET |
| AC6: output_format with 7 fields | Missing  examples hint at format but no formal section | NOT MET |
| AC7: Verdict semantics documented | Missing from agent file (only in wave-planning skill) | NOT MET |
| AC8: retry_count as input | Not mentioned | NOT MET |
| AC9: boundaries + self-defense table | Missing entirely | NOT MET |
| AC10: multi_agent_context section | Missing entirely | NOT MET |
| AC11: copilot-instructions.md evaluator row | Not updated  0 grep matches | NOT MET |

### Verdict
Confidence: .10  1/11 AC met. File is a DEPRECATED stub (examples + self_critique only). All required sections (persona, critical_rules, workflow, output_format, boundaries, multi_agent_context) are absent. DEPRECATED notice contradicts task notes which specify evaluator as separate from planner. Design decision to merge into planner was not reflected in this task's AC or closure.

[[2026-03-09]] Mon 04:57
Wave 1, agent: architect

[[2026-03-09]] Mon 05:04
## Architecture Review
**Verdict:** BLOCK -> ideation

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: evaluator.agent.md YAML frontmatter | Superseded - evaluator merged into planner EVALUATE mode | MOOT |
| AC2: Tool list excludes edit tools | Covered by planner tool list | MOOT |
| AC3: persona section | Planner persona covers EVALUATE mode implicitly | MOOT |
| AC4: critical_rules | Planner lacks evaluator-specific anti-rubber-stamp rule | GAP |
| AC5: workflow (5 steps) | wave-planning SKILL.md EVALUATE Steps 1-5 implement this | MOOT |
| AC6: output_format with 7 fields | wave-planning SKILL.md has all 7 fields | MOOT |
| AC7: verdict semantics | wave-planning SKILL.md documents verdict table | MOOT |
| AC8: retry_count as input | wave-planning SKILL.md Step 1 references retry counts | MOOT |
| AC9: boundaries + self-defense table | Planner has general boundaries but no evaluate-specific self-defense | GAP |
| AC10: multi_agent_context | Doesn't document EVALUATE role distinction vs reviewer | GAP |
| AC11: copilot-instructions.md evaluator row | N/A - no standalone agent | MOOT |

### Architecture Notes
Design divergence: research recommended standalone evaluator (different cognitive tasks). Implementation merged it into planner EVALUATE mode. 8/11 AC lines' intent is covered. 3 minor gaps remain: anti-rubber-stamp rule, self-defense table, multi_agent_context EVALUATE docs. Task #682 (done) already depends on this merged design.

### Changes Made
- Moved #681: backlog -> ideation
- Updated block reason: design superseded

### Dependencies
- #682 (orchestrator rewrite, done) - depends_on #681 but completed assuming planner EVALUATE mode. No cascading impact if #681 is closed or refined.

[[2026-03-09]] Mon 05:10
## Planner Evaluation\nVerdict: BLOCK. Design superseded by planner EVALUATE mode. 8/11 AC moot, 3 minor gaps. User decision required: close as superseded, create refinement task for gaps, or restore standalone design.

[[2026-03-09]] Mon 19:25
## Audit (auditor, 2026-03-09)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| RigorProfile dataclass creation | 3 tests (create/frozen/is_dataclass) PASS | PASS |
| 3 preset constants expected values | 9 tests verify exact LEAN/STANDARD/THOROUGH values | PASS |
| OwlBearSettings rigor_profiles dict 3 presets | 4 tests (has_three_keys + 3 match_preset) PASS | PASS |
| OwlBearSettings.default_rigor = 'standard' | test_default_rigor_is_standard PASS | PASS |
| resolve_rigor_profile matching for rigor:lean | test_returns_lean_for_rigor_lean_tag PASS | PASS |
| resolve_rigor_profile default when no rigor tag | 2 tests (no_rigor_tag + empty_tags) PASS | PASS |
| resolve_rigor_profile ignores non-rigor tags | 2 tests (ignores_non_rigor + tag_among_many) PASS | PASS |
| Custom profile in rigor_profiles | test_custom_profile_accepted PASS | PASS |
| field_validator rejects unknown default_rigor | test_unknown_default_rigor_rejected PASS | PASS |
| OwlBearDeps rigor_profile field | 2 tests (default_none + accepts_value) PASS | PASS |

### Test Results
- pytest (scoped): 28 passed, 0 failed
- pytest (full suite): 1315 passed, 2 failed (pre-existing: slack_sdk missing + Windows PermissionError), 20 skipped
- ruff: clean on task file (3 pre-existing issues in unrelated files)

### Confidence: .97
### Action: archive
