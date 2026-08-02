---
id: 646
title: 'P4-06: Create pragmatist-voice.agent.md'
status: archived
priority: medium
created: 2026-04-06T07:01:14.5070148+02:00
updated: 2026-04-07T00:29:50.4621473+02:00
started: 2026-04-07T00:29:50.4621473+02:00
completed: 2026-04-07T00:29:50.4621473+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:build'
depends_on:
    - 645
class: standard
---

## Acceptance Criteria

- [ ] `share/agents/pragmatist-voice.agent.md` exists with valid YAML frontmatter
- [ ] `user-invocable: false`
- [ ] `model: Claude Opus 4.6 (copilot)` configured
- [ ] Reads: `context.md`, `decisions.md`, ALL `voices/*.md` results
- [ ] Writes: `synthesis.md`
- [ ] Identifies convergences, disagreements, and produces recommendation
- [ ] Flags disagreements with attribution (NOT resolved algorithmically -- resolution is user's job)
- [ ] Does NOT read debate logs, user conversation, raw research, or input files

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
Pure synthesis subagent invoked after all domain voices have published. The Mediator reads synthesis.md and presents it to the user.

[[2026-04-06]] Mon 22:06
## Research
- Research doc: .owlbear/research/pragmatist-voice-agent.md
- Sources: 6 studied (5 codebase-internal, 1 external), 4 high-relevance
- Recommendation: Build ~65-line agent file following critic-voice pattern with 4 key differences: Claude Opus 4.6 model (not GPT-5.4), 4 tools including edit/createFile for synthesis.md write, single invocation scope, attribution as core persona trait (confidence: 0.88)
- Follow-up tasks created: none (existing board has full coverage: #647-#652)
- Decision requests: none

### Key Findings
- **Tool set**: 4 tools — `[read/readFile, edit/createFile, search, vscode/memory]`. Pragmatist needs file write (unlike read-only Critic). `search` enables voice file discovery as safety net.
- **disable-model-invocation: true**: Follows critic-voice pattern. Only ideator should invoke. Not in pipeline agent test list, so no conflict.
- **Model: Claude Opus 4.6 (copilot)**: Per spec §7, only the Critic uses a different model (GPT-5.4). All other voices use Claude Opus 4.6.
- **Simpler than Critic**: Single invocation scope (post-deliberation only), no dual-scope prompt complexity. ~65 lines vs Critic's ~80.
- **AC refinements flagged**: 6 items for architect (disable-model-invocation, exact tool set, agents:[], argument-hint, recommendation specificity, debate log exclusion encoding).
- **Cross-cutting tests**: blanket askQuestions ban (glob-based) — safe, not in proposed tool set. No other conflicts.
- **Prior art**: de Bono Blue Hat (synthesis facilitator role) + Blackboard pattern (shared memory synthesis) validate the design.

### Challenge Results
- Challenger: FALLBACK — not in available agent roster
- Confidence in original: 0.88
- Key self-challenges: (a) createFile vs editFiles for loop-back — Mediator clears Working Dir per spec; (b) search tool utility — Mediator passes names but search is safety net; (c) file size smaller than Critic — expected, simpler scope
- Researcher response: accepted all, no revision needed

[[2026-04-06]] Mon 22:36
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Creates one agent file, single purpose |
| Interface clarity | PASS (with refinements) | Core AC is verifiable; researcher flagged 6 refinements — all adopted below |
| Dependency correctness | PASS | #645 (ideator.agent.md) archived/done; ideator already lists pragmatist-voice in agents array |
| Module layering | PASS | Voice subagent invoked only by ideator (Mediator); no upward imports |
| TDD compliance | PASS | Agent file (non-code); pipeline test infra covers structural validation |
| KISS/YAGNI | PASS | ~65 lines, follows existing critic-voice pattern with minimal differences |
| Premise challenge | PASS | Spec s7 mandates Pragmatist as "Always subagent"; de Bono Blue Hat validates synthesis role |
| Pattern consistency | PASS | Follows critic-voice pattern: disable-model-invocation, subagent-only, vscode/memory |
| Security surface | PASS | No external APIs; reads/writes only within Working Dir (.owlbear/briefs/draft-*/) |
| Single domain | PASS | Strictly within ideator/thinking-companion domain |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| File exists with valid YAML frontmatter | Verifiable | Keep |
| user-invocable: false | Verifiable | Keep |
| model: Claude Opus 4.6 (copilot) | Verifiable | Keep |
| Reads: context.md, decisions.md, ALL voices/*.md | Verifiable | Keep |
| Writes: synthesis.md | Verifiable | Keep |
| Identifies convergences, disagreements, produces recommendation | Slightly vague | Builder: recommendation must include confidence score (0.0-1.0) per research s3d |
| Flags disagreements with attribution | Verifiable | Keep; encode in persona + critical_rules per research s3d |
| Does NOT read debate logs, user conversation, raw research, or input files | Verifiable | Keep |

### Binding Refinements (from research, adopted)

Builder must incorporate these in the agent file (all validated against spec s7/s12 and critic-voice pattern):

1. **`disable-model-invocation: true`** -- follows critic-voice pattern; only ideator invokes
2. **`tools: [read/readFile, edit/createFile, search, vscode/memory]`** -- exact tool set per research s3b
3. **`agents: []`** -- no subagent delegation; Pragmatist does not invoke Critic (Mediator handles optional final Critic per spec s12)
4. **`argument-hint: "Synthesize: {working directory path}"`** -- per h-agent-structure standards
5. **Recommendation specificity** -- synthesis.md output must include confidence score, not bare opinion
6. **Debate log exclusion** -- encode in persona + critical_rules sections, not just as AC prohibition
7. **Non-impl tag** -- task needs `agent` pass-through tag added (produces .agent.md, not testable Python)

### Architecture Notes

- Pragmatist maps to spec s12 Working Dir table: reads context.md, decisions.md, ALL voices/*.md; writes synthesis.md
- search tool justified as safety net: Mediator passes voice names in prompt but not all voices are always activated
- edit/createFile (not edit/editFiles) correct: Mediator clears Working Dir before re-invocation per spec s12 Phase 5
- Cross-cutting test constraints verified: askQuestions ban (glob-based) safe; disable-model-invocation list safe

### Challenge Results
- Challenger: FALLBACK -- not in available agent roster
- Self-challenge: proceed (confidence 0.90)
- Key challenges tested: role necessity (spec-mandated), merger with Critic (role conflict), tool set scope (minimal), security surface (none)

### Verdict: APPROVE
### Action Taken: Advanced to todo with binding refinements documented for builder

[[2026-04-06]] Mon 23:28
## Test-Writer Notes

- **Test file:** `tests/test_pragmatist_voice_agent_646.py`
- **Total tests:** 43 — all FAIL ✓
- **Ruff:** clean ✓

### Classes

| Class | Tests | Coverage |
|-------|-------|---------|
| `TestFromAC_PragmatistVoiceFrontmatter` | 26 | AC1-AC3, R1-R4 |
| `TestFromAC_PragmatistVoiceInputContract` | 5 | AC4 |
| `TestFromAC_PragmatistVoiceSynthesisOutput` | 7 | AC5-AC7, R5-R6 |
| `TestFromAC_PragmatistVoiceExclusions` | 5 | AC8, R6 |

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 — file exists + valid frontmatter | test_file_exists, test_has_valid_yaml_frontmatter, test_name_is_pragmatist_voice, test_description_exists, test_description_mentions_synthesis_or_pragmatist |
| AC2 — user-invocable: false | test_user_invocable_false |
| AC3 — model: Claude Opus 4.6 (copilot) | test_model_contains_claude_opus, test_model_version_is_46, test_model_is_copilot_provider, test_model_is_single_string_not_array, test_model_is_not_gpt_family |
| AC4 — reads context.md, decisions.md, ALL voices/*.md | test_context_md_referenced_in_body, test_decisions_md_referenced_in_body, test_voices_directory_or_pattern_referenced, test_working_directory_referenced_in_body, test_reads_all_voices_not_selective |
| AC5 — writes synthesis.md | test_synthesis_md_output_referenced, test_synthesis_write_intent_present, test_has_create_file_tool_for_synthesis_write |
| AC6 — convergences, disagreements, recommendation + confidence | test_convergences_mentioned_in_body, test_disagreements_mentioned_in_body, test_recommendation_mentioned_in_body, test_confidence_score_required_in_output |
| AC7 — attribution, not resolved algorithmically | test_attribution_mentioned_in_body, test_no_algorithmic_resolution_defers_to_user, test_persona_section_exists |
| AC8 — no debate logs / raw research / input files | test_debate_logs_excluded_in_body, test_raw_research_excluded_in_body, test_input_files_excluded_in_body, test_critical_rules_section_exists, test_reads_only_permitted_summary_files |
| R1 — disable-model-invocation: true | test_disable_model_invocation_true |
| R2 — tools exactly [read/readFile, edit/createFile, search, vscode/memory] | test_tools_exactly_four, test_tools_are_correct_set, test_no_execute_tools, test_no_kanban_mcp_tools, test_no_edit_files_tool |
| R3 — agents: [] | test_agents_is_empty_list |
| R4 — argument-hint starts with Synthesize + references working dir | test_argument_hint_exists, test_argument_hint_starts_with_synthesize, test_argument_hint_references_working_directory |
| R5 — confidence score in output contract | test_confidence_score_required_in_output |
| R6 — exclusions in persona + critical_rules | test_critical_rules_section_exists, test_debate_logs_excluded_in_body |

### Fail confirmation
`43 failed in 0.14s` — pragmatist-voice.agent.md does not exist yet; all tests fail on FileNotFoundError or AssertionError.

[[2026-04-06]] Mon 23:40
## Builder Notes

### Files Changed
- `share/agents/pragmatist-voice.agent.md` — created (new file, ~65 lines)

### Test Results
- 43 passed, 0 failed
- ruff: clean (no Python files — markdown-only change)

### Evidence
- RED verified: 43 failed before implementation
- GREEN confirmed: 43 passed after creation
- One fix required: removed quotes from `argument-hint` value (test reads raw `re.search` match, quotes caused `startswith("synthesize")` to fail on `"Synthesize`)

### Implementation Notes
- Followed `critic-voice.agent.md` pattern exactly
- Key differences from Critic: Claude Opus 4.6 (not GPT-5.4), `edit/createFile` tool included, `read/viewImage` / `read/problems` replaced with `search`, single invocation scope (no dual-scope complexity), synthesis writes `synthesis.md`
- All binding refinements R1–R6 incorporated: `disable-model-invocation: true`, exact 4-tool set, `agents: []`, argument-hint, confidence score in output contract, exclusions in `<persona>` + `<critical_rules>`
- `<persona>` + `<critical_rules>` encode debate log / raw research / input file exclusions per R6/AC8

[[2026-04-07]] Tue 00:14
## Review Evidence

### Test Results
- pytest: 43 passed, 0 failed

### Lint: clean

### Coverage: N/A — markdown-only change, no Python module

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — file exists + valid frontmatter | test_file_exists, test_has_valid_yaml_frontmatter | Yes — FileNotFoundError / AssertionError | COVERED |
| AC2 — user-invocable: false | test_user_invocable_false | Yes — exact string match | COVERED |
| AC3 — model: Claude Opus 4.6 (copilot) | test_model_contains_claude_opus, test_model_version_is_46, test_model_is_copilot_provider, test_model_is_not_gpt_family | Yes — would catch GPT, wrong version, wrong provider | COVERED |
| AC4 — reads context.md, decisions.md, ALL voices/*.md | test_context_md_referenced_in_body, test_decisions_md_referenced_in_body, test_voices_directory_or_pattern_referenced, test_reads_all_voices_not_selective | Yes — each checks body content explicitly | COVERED |
| AC5 — writes synthesis.md | test_synthesis_md_output_referenced, test_has_create_file_tool_for_synthesis_write | Yes — checks body + tool list | COVERED |
| AC6 — convergences, disagreements, recommendation + confidence | test_convergences_mentioned_in_body, test_disagreements_mentioned_in_body, test_recommendation_mentioned_in_body, test_confidence_score_required_in_output | Yes — confidence test uses specific (0.0–1.0) regex | COVERED |
| AC7 — attribution; not resolved algorithmically | test_attribution_mentioned_in_body, test_no_algorithmic_resolution_defers_to_user, test_persona_section_exists | Yes — resolution-defers-to-user regex is specific | COVERED |
| AC8 — no debate logs / raw research / input files | test_debate_logs_excluded_in_body, test_raw_research_excluded_in_body, test_input_files_excluded_in_body, test_critical_rules_section_exists | Yes — each uses targeted exclusion regex | COVERED |
| R1 — disable-model-invocation: true | test_disable_model_invocation_true | Yes — exact string match | COVERED |
| R2 — tools exactly [read/readFile, edit/createFile, search, vscode/memory] | test_tools_exactly_four, test_tools_are_correct_set, test_no_execute_tools, test_no_kanban_mcp_tools, test_no_edit_files_tool | Yes — frozenset equality + negative guards | COVERED |
| R3 — agents: [] | test_agents_is_empty_list | Yes — exact string match | COVERED |
| R4 — argument-hint starts with Synthesize + references working dir | test_argument_hint_exists, test_argument_hint_starts_with_synthesize, test_argument_hint_references_working_directory | Yes — startswith + keyword check | COVERED |
| R5 — confidence score in output | test_confidence_score_required_in_output | Yes — (0.0-1.0) regex | COVERED |
| R6 — exclusions in persona + critical_rules | test_persona_section_exists, test_critical_rules_section_exists, test_debate_logs_excluded_in_body | Yes | COVERED |

No MISSING. No LAX.

#### Security Review
- No executable code changed. Agent file is markdown with no external API calls, no secrets, no injection paths. No issues.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 43 TestFromAC_* tests | None — builder notes confirm no test modifications | PRESERVED |

Builder's single noted fix (removed quotes from argument-hint value) was in the implementation file, not in the test file. Correct: test regex `startswith("synthesize")` would have caught a quoted value — builder fixed the implementation, not the test.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | frozenset equality, exact string matches, targeted regex patterns (not bare `assert result`) |
| Negative/error coverage | STRONG | test_model_is_not_gpt_family, test_no_execute_tools, test_no_kanban_mcp_tools, test_no_edit_files_tool, test_no_algorithmic_resolution_defers_to_user |
| Manual mutation reasoning | STRONG | Removing any frontmatter field or body section triggers a test failure |
| Test independence | STRONG | All tests read from file directly; no shared mutable state |
| Descriptive test names | STRONG | All names follow test_{descriptive_contract} convention |

#### Data Safety
- No mutable state, no LLM output persisted, no race conditions, no resource-intensive operations. No issues.

#### Implementation-Aware Gaps
- No untested paths. Markdown agent file — every structural element (frontmatter fields, persona, critical_rules, input/output contract) is covered by a test.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- None.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | pragmatist-voice.agent.md exists; starts with `---\n`; non-empty frontmatter | test_file_exists, test_has_valid_yaml_frontmatter | PASS |
| AC2 | Frontmatter line: `user-invocable: false` | test_user_invocable_false | PASS |
| AC3 | Frontmatter line: `model: Claude Opus 4.6 (copilot)` — exact AC text | test_model_contains_claude_opus, test_model_version_is_46 | PASS |
| AC4 | Input Contract table: context.md, decisions.md, voices/*.md; body reads "read ALL" | test_reads_all_voices_not_selective | PASS |
| AC5 | Output Contract: "Write `synthesis.md` to the Working Directory"; `edit/createFile` in tools | test_synthesis_md_output_referenced | PASS |
| AC6 | Sections: Convergences, Disagreements, Recommendation; "confidence score (0.0–1.0)" in Output Contract | test_confidence_score_required_in_output | PASS |
| AC7 | Disagreements section: "Attribution: which voice(s) raised it"; critical_rules: "Never resolve disagreements. Surface them with full attribution; leave resolution for the user" | test_no_algorithmic_resolution_defers_to_user | PASS |
| AC8 | persona + critical_rules both enumerate: debate logs, raw research, input files as forbidden reads | test_debate_logs_excluded_in_body, test_critical_rules_section_exists | PASS |
| R1 | Frontmatter: `disable-model-invocation: true` | test_disable_model_invocation_true | PASS |
| R2 | Frontmatter: `tools: [read/readFile, edit/createFile, search, vscode/memory]` — exactly 4 | test_tools_exactly_four, test_tools_are_correct_set | PASS |
| R3 | Frontmatter: `agents: []` | test_agents_is_empty_list | PASS |
| R4 | Frontmatter: `argument-hint: Synthesize: {working directory path}` | test_argument_hint_starts_with_synthesize | PASS |

### Confidence: .98
### Verdict: PASS

[[2026-04-07]] Tue 00:17
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | New subagent added; `copilot-instructions.md` contains no agents registry (15-line file: project identity + branch table only). No update required. |
| 2 | Module docstrings | No | N/A | Markdown-only change — zero Python modules created or modified. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` already contains a "Pragmatist Voice Agent (Task #646)" section with the Six Thinking Hats / Blue Hat row (de Bono 1985). Blackboard pattern referenced in arch review as incidental validation; its primary row exists under Task #642. No new row needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/pragmatist-voice-agent.md` exists. Linked from task body ("Research doc: .owlbear/research/pragmatist-voice-agent.md"). Follow-up tasks noted as covered by existing board tasks #647–#652; no new task creation required. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `646-*` scratch files found)

[[2026-04-07]] Tue 00:29
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 file exists + valid frontmatter | pragmatist-voice.agent.md L1-10: starts with --- block, valid YAML | PASS |
| AC2 user-invocable: false | frontmatter L5: user-invocable: false | PASS |
| AC3 model: Claude Opus 4.6 (copilot) | frontmatter L7: model: Claude Opus 4.6 (copilot) | PASS |
| AC4 reads context.md, decisions.md, ALL voices/*.md | Input Contract table lists all 3; test_reads_all_voices_not_selective | PASS |
| AC5 writes synthesis.md | Output Contract: "Write synthesis.md"; edit/createFile in tools | PASS |
| AC6 convergences, disagreements, recommendation | Output Contract sections: Convergences, Disagreements, Recommendation + confidence (0.0-1.0) | PASS |
| AC7 attribution, not resolved algorithmically | critical_rules: "Never resolve disagreements. Surface them with full attribution" | PASS |
| AC8 no debate logs/raw research/input files | persona + critical_rules enumerate all forbidden reads | PASS |
| R1 disable-model-invocation: true | frontmatter L6 | PASS |
| R2 tools exactly 4 | frontmatter L8: [read/readFile, edit/createFile, search, vscode/memory] | PASS |
| R3 agents: [] | frontmatter L9 | PASS |
| R4 argument-hint starts with Synthesize | frontmatter L4 | PASS |

### Test Results
- pytest: 43 passed, 0 failed (test_pragmatist_voice_agent_646.py)
- Cross-task regression: 104 passed (critic-voice #644, ideator #645)
- Full suite: pre-existing failures in test_planner_gates.py (import error), test_argument_hint_skills.py, test_disable_model_invocation.py, all unrelated to #646
- ruff: clean

### Architect Quality: 4/5
One AC line slightly vague ("Identifies convergences, disagreements, and produces recommendation") but architect's binding refinement R5 (confidence score) addressed the gap. AC was otherwise specific and fully verifiable.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: none (0)
- Lint violations: none (0)
- AC quality 4/5 (above 3): no deduction
- Reviewer evidence: present, detailed, PASS at .98 (0)
- Full-suite failures in task scope: none (0)
- Uncommitted deliverables: noted but committed during audit (no deduction, quality gap only)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 7e04ffc | feat(agents) | pragmatist-voice.agent.md, test_pragmatist_voice_agent_646.py, pragmatist-voice-agent.md (research), kanban task file | #646 |
