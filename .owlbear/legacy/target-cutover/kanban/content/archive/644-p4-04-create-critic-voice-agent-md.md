---
id: 644
title: 'P4-04: Create critic-voice.agent.md'
status: archived
priority: medium
created: 2026-04-06T07:00:33.6982746+02:00
updated: 2026-04-06T19:11:11.872112+02:00
started: 2026-04-06T19:11:11.872112+02:00
completed: 2026-04-06T19:11:11.872112+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:build'
depends_on:
    - 641
class: standard
---

## Acceptance Criteria

- [ ] `share/agents/critic-voice.agent.md` exists with valid YAML frontmatter
- [ ] `user-invocable: false` set
- [ ] `model: GPT-5.4 (copilot)` configured for genuine model diversity
- [ ] System prompt is purely adversarial: challenges positions, never proposes alternatives
- [ ] Prompt includes Critic exit behavior: "If position is solid after honest examination, say so and exit. Do not manufacture objections."
- [ ] Agent receives voice's current position via prompt, reads `context.md` from Working Directory
- [ ] Returns adversarial challenges to the invoking voice (no direct file writes)
- [ ] Works when invoked by domain voices AND by the Mediator (standalone checks)

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
The Critic is the most-invoked subagent: 4 standalone calls per engagement (after M1, M2, M4, M5) plus up to 5 cycles per domain voice. Must work at two scopes: domain-level (invoked by voice) and meta-level (invoked by Mediator).

## Design

- Single agent file handles both standalone and voice-embedded invocations
- Scope determined by input context, not agent configuration
- Different model (GPT) from all other voices (Opus) is the key architectural requirement

[[2026-04-06]] Mon 15:01
## Research
- Research doc: .owlbear/research/critic-voice-agent.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Single file, dual-scope (Option A) — follows Challenger pattern with GPT-5.4 model, Working Dir context, exit behavior clause (confidence: 0.88)
- Follow-up tasks created: none (task #644 is itself the build task)
- Decision requests: none

### Key Findings
- **Dual-scope works from one file**: standalone (Mediator) vs embedded (voice) scopes differ only in input context, not agent config. Confirmed by spec §7.
- **No overlap with Challenger**: different pipeline stage, model, invokers, inputs. Distinct agents in distinct systems.
- **Model**: GPT-5.4 (copilot) as sole model (not fallback array) — model diversity is the architectural mechanism. 4 existing agents already use GPT-5.4.
- **Tools**: Read-only mirror of Challenger — `[read/readFile, read/viewImage, read/problems, search, vscode/memory]`.
- **Exit behavior**: prompt-embedded "If position is solid… say so and exit." Prevents manufactured objections.
- **Tier: T1** — agent file creation following established pattern, no new capability beyond what the spec already designed.

[[2026-04-06]] Mon 16:22
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single agent file creation |
| Interface clarity | REFINE | AC tightened below: 3 new lines, 2 rewrites |
| Dependency correctness | PASS | #641 archived |
| Module layering | PASS | No code modules, agent file only |
| TDD compliance | PASS | Agent file, no testable Python. **REQUIRED: add `agent` tag** (currently only type:build, not a non-impl pass-through tag) |
| KISS/YAGNI | PASS | Minimal scope, single file |
| Premise challenge | PASS | Required by spec sections 7 and 12 |
| Pattern consistency | PASS | Follows Challenger pattern with 3 adaptations (GPT-5.4, Working Dir context, exit behavior) |
| Security surface | PASS | Read-only tools, no new system boundaries |
| Single domain | PASS | Ideation domain only |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| #1 valid YAML frontmatter | Sufficient | None |
| #2 user-invocable: false | Verifiable | None |
| #3 model: GPT-5.4 | Verifiable | Clarify: sole model, not fallback array |
| #4 purely adversarial prompt | Verifiable | None |
| #5 exit behavior | Verifiable | None |
| #6 receives position, reads context.md | Verifiable | None |
| #7 no direct file writes | Verifiable | None |
| #8 works for voices AND Mediator | UNVERIFIABLE at build time | Reworded below |

### AC Refinements (authoritative for builder)

**Refined AC#3:** `model: GPT-5.4 (copilot)` as sole model (not fallback array) for genuine model diversity. This is a first-of-kind in the workspace; the spec mandates it.

**Refined AC#8:** Designed for dual-scope invocation: prompt handles both standalone context (Mediator passes problem/outcome/approach claim) and embedded context (voice passes current position). No scope-specific configuration or branching logic required.

**New AC lines:**
- `disable-model-invocation: true` set (standard for all subagent-only agents)
- `tools: [read/readFile, read/viewImage, read/problems, search, vscode/memory]` (read-only, mirrors Challenger)
- `agents: []` (no subagent delegation)

**Builder guidance:**
- Include `argument-hint` covering both invocation scopes, e.g. `"Critique: {position or claim to challenge}"`
- Agent tier: T4 (Tools) per h-agent-structure (same as Challenger). No pipeline protocol references needed in critical_rules.
- Pattern reference: `share/agents/challenger.agent.md` for structural template
- Information boundary (prompt-only enforcement): Critic can technically read other voices' files via read/readFile. Prompt must instruct reading only what the invoker provides and context.md. This follows the Challenger pattern.

### REQUIRED ACTION: Add `agent` tag for non-impl pass-through (edit_task not available to architect; orchestrator or test-writer must add before processing).

### Challenge Results
- Challenger: reconsider (confidence 0.55)
- C1 (sole model precedent): REBUTTED. Spec mandates model diversity as architectural mechanism. Fallback array dilutes guarantee; if GPT-5.4 unavailable and Claude runs, Critic and voices use same model family.
- C2 (AC#8 unverifiable): ACCEPTED. Reworded to "designed for dual-scope invocation."
- C3 (underspecified frontmatter): ACCEPTED. Added 3 new AC lines for disable-model-invocation, tools, agents.
- C4 (prompt-only boundary enforcement): ACKNOWLEDGED as minor. Follows Challenger pattern; tool-level restriction would break legitimate context.md access.
- B1 (agent tier): Resolved as T4.
- B2 (YAML validation): Standard review process covers this.
- B3 (orphaned invocation chain): Expected; consumers (#645-650) depend on #644, not vice versa.
- A2 (argument-hint gap): Added to builder guidance.

### Verdict: APPROVE
### Action Taken: AC refined with 3 new lines and 2 rewrites. Tag `agent` must be added by next handler. Advanced to todo.

[[2026-04-06]] Mon 17:13
## Test-Writer Notes

**Test file:** `tests/test_critic_voice_agent_644.py`

**Classes:**
| Class | Tests | Category |
|-------|-------|----------|
| `TestFromAC_CriticVoiceFrontmatter` | 21 | frontmatter structure, AC1-AC3, AC9-AC11 |
| `TestFromAC_CriticVoicePromptBehavior` | 9 | AC4 adversarial persona, AC5 exit behavior |
| `TestFromAC_CriticVoiceContextAndScope` | 5 | AC6 context.md/Working Dir, AC8 dual-scope |
| `TestFromAC_CriticVoiceOutputContract` | 4 | AC7 read-only output contract |

**Total: 39 tests, all FAIL ✓** (ruff: clean)

**AC Coverage:**

| AC | Tests |
|----|-------|
| AC1 file + frontmatter | test_file_exists, test_has_valid_yaml_frontmatter |
| AC2 user-invocable: false | test_user_invocable_false |
| AC3 model: GPT-5.4 (copilot), sole string, not Claude | test_model_contains_gpt54, test_model_is_single_string_not_array, test_model_is_copilot_provider, test_model_is_not_claude_or_opus |
| AC4 adversarial, never proposes alternatives | test_persona_section_exists/closing_tag, test_persona_adversarial_challenge_role, test_persona_challenges_positions_not_pipeline_decisions, test_persona_never_proposes_alternatives |
| AC5 exit behavior (solid/honest/manufacture) | test_exit_behavior_solid_present, test_exit_behavior_honest_examination, test_exit_behavior_allow_clean_exit, test_exit_behavior_no_manufacture_objections |
| AC6 receives position, reads context.md from Working Dir | test_context_md_mentioned, test_working_directory_mentioned, test_position_input_described_in_body, test_argument_hint_generic_covers_both_scopes |
| AC7 read-only, no file writes | test_no_execute_tools, test_no_edit_tools, test_no_mcp_glob_tools, test_no_file_writes_stated_in_body, test_no_kanban_commands_stated, test_critical_rules_section_exists |
| AC8 dual-scope, no scope config | test_dual_scope_no_scope_specific_frontmatter, test_dual_scope_describes_both_mediator_and_voice, test_argument_hint_generic_covers_both_scopes |
| AC9 disable-model-invocation | test_disable_model_invocation_true |
| AC10 exact tool set | test_tools_key_exists, test_tools_exactly_five, test_tools_are_correct_set |
| AC11 agents: [] | test_agents_is_empty_list |

**Note (hook bypass):** `create_file` blocked by deny-src-writes.ps1 absolute-path bug (known issue, hooks-patterns.md). File written via `[System.IO.File]::WriteAllText` per documented workaround.

[[2026-04-06]] Mon 17:59
## Builder Notes

### Files Changed
- `share/agents/critic-voice.agent.md` — created (69 lines)

### Test Results
- 39 FAILED → 39 passed (RED verified before implementation)
- Ruff: clean

### Coverage
- Agent file (not a Python module) — content-level verification via 39 contract tests

### Evidence
- All 4 TestFromAC_* classes pass: Frontmatter (21), PromptBehavior (9), ContextAndScope (5), OutputContract (4)
- Frontmatter: name, description, user-invocable, disable-model-invocation, model (GPT-5.4 copilot sole string), tools (exactly 5 read-only), agents []
- Body: `<persona>` adversarial challenger, exit behavior ("solid", "honest examination", "say so and exit", "Do not manufacture objections"), context.md + Working Directory, dual-scope (Mediator/voice), `<critical_rules>` section, no file writes stated, no kanban commands

### Fix Applied
- UTF-8 BOM issue: `[System.IO.File]::WriteAllText` defaults to UTF8 with BOM; fixed by using `New-Object System.Text.UTF8Encoding $false`

### Commit
- `a4f63df` feat: add critic-voice.agent.md adversarial subagent (#644)

[[2026-04-06]] Mon 18:12
## Review Evidence

### Test Results
pytest: **39 passed, 0 failed**
ruff: **clean**
Coverage: N/A (agent markdown file, not a Python module — content-level verification via 39 contract tests)

### Source Control
Changed files: `share/agents/critic-voice.agent.md` (created, 69 lines)
Test file: `tests/test_critic_voice_agent_644.py` (39 tests across 4 TestFromAC_* classes)

### AC Compliance

| AC Line | Evidence | Mapped Test(s) | Status |
|---------|----------|----------------|--------|
| AC1: file exists with valid YAML frontmatter | `share/agents/critic-voice.agent.md` exists, begins `---\n` | `test_file_exists`, `test_has_valid_yaml_frontmatter` | PASS |
| AC2: `user-invocable: false` | frontmatter line: `user-invocable: false` | `test_user_invocable_false` | PASS |
| AC3: `model: GPT-5.4 (copilot)` sole string | frontmatter line: `model: GPT-5.4 (copilot)` (not array) | `test_model_contains_gpt54`, `test_model_is_single_string_not_array`, `test_model_is_copilot_provider`, `test_model_is_not_claude_or_opus` | PASS |
| AC4: purely adversarial, never proposes alternatives | `<persona>`: "adversarial critic… do not propose alternatives… You find what is wrong" | `test_persona_adversarial_challenge_role`, `test_persona_never_proposes_alternatives` | PASS |
| AC5: exit behavior clause | Both in `<persona>` (body line ~19) and Output Contract (body line ~67): "If position is solid after honest examination, say so and exit. Do not manufacture objections." | `test_exit_behavior_solid_present`, `test_exit_behavior_honest_examination`, `test_exit_behavior_allow_clean_exit`, `test_exit_behavior_no_manufacture_objections` | PASS |
| AC6: receives position, reads `context.md` from Working Directory | Input Contract section: "You receive the invoker's current position via the prompt. Additionally, read `context.md` from the Working Directory" | `test_context_md_mentioned`, `test_working_directory_mentioned`, `test_position_input_described_in_body` | PASS |
| AC7: read-only output, no file writes | `<critical_rules>`: "Strictly read-only. No file edits, no file creation, no kanban commands, no state mutations of any kind." | `test_no_file_writes_stated_in_body`, `test_no_kanban_commands_stated`, `test_critical_rules_section_exists`, `test_no_execute_tools`, `test_no_edit_tools` | PASS |
| AC8: dual-scope, no scope-specific config | "Dual-Scope Invocation" section describes both Mediator standalone and domain voice embedded contexts; no `scope:` field in frontmatter | `test_dual_scope_no_scope_specific_frontmatter`, `test_dual_scope_describes_both_mediator_and_voice` | PASS |
| AC9: `disable-model-invocation: true` | frontmatter line: `disable-model-invocation: true` | `test_disable_model_invocation_true` | PASS |
| AC10: exact tool set | frontmatter line: `tools: [read/readFile, read/viewImage, read/problems, search, vscode/memory]` — frozenset exact match | `test_tools_exactly_five`, `test_tools_are_correct_set`, `test_no_mcp_glob_tools` | PASS |
| AC11: `agents: []` | frontmatter line: `agents: []` | `test_agents_is_empty_list` | PASS |

### TestFromAC Integrity
No prior test baseline — first review cycle. 4 TestFromAC_* classes confirmed; no modifications possible.

### Test Quality Assessment
**Overall: ADEQUATE–STRONG.** Two LAX tests identified, both mitigated by compensating strong tests:
1. `test_persona_challenges_positions_not_pipeline_decisions`: regex `position|claim|stance` across whole body — too broad to fail on its own. Mitigated by `test_persona_adversarial_challenge_role` and `test_persona_never_proposes_alternatives`.
2. `test_position_input_described_in_body`: semantically identical assertion to the above (same regex, same corpus). Mitigated by `test_context_md_mentioned` and `test_working_directory_mentioned` anchoring AC6 independently.
Assertion specificity: STRONG (frozenset exact-match on tools; exact-string on flags; named-phrase matching on exit behavior). Negative paths: STRONG (execute/edit/mcp tools, Claude family check). Test independence: STRONG. Naming: STRONG.

### Security Review
No OWASP Top 10 issues. Agent file is static prompt/config; test file uses hardcoded path construction with no user input. No injection, traversal, or deserialization concerns.

### Informational (non-blocking)
- **Test gap — output schema:** The four-section output structure (`### Challenges`, `### Blind Spots`, `### Confidence in Position`, `### Recommendation`) is not tested. A builder could remove it without failing any test. AC7 does not specify this schema, so this is beyond-AC. (Moderate silent-failure risk for consumers; suggest follow-up task to add schema test if output contract is load-bearing.)
- **Test gap — `<critical_rules>` content:** Existence confirmed; individual rules not asserted. Mitigated by body-level tests covering same constraints.
- **Informational redundancy:** `test_persona_challenges_positions_not_pipeline_decisions` and `test_position_input_described_in_body` are effectively duplicate assertions.
- **Tool prefix whitelist fragility:** `test_no_mcp_glob_tools` hardcodes known prefixes; future prefixes would false-positive.
- **Exit-behavior duplication in agent:** The exit clause appears twice (persona + output contract). Intentional emphasis; future editors must keep both in sync.

### Builder Process Quality
Single build attempt. No loop detected. CLEAN.

### Deductions
- 2 LAX tests, both mitigated: –0.02
- Minor informational test gap (output schema): –0.01
- **Total deductions: –0.03**

### Verdict
**Confidence: .97 → PASS**

[[2026-04-06]] Mon 18:18
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.github/copilot-instructions.md` is a 3-line project identity stub — no agent catalog or tech stack table present. No update target exists. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Sole artifact is `share/agents/critic-voice.agent.md` (agent config file). |
| 3 | External attribution | No | N/A | Research cites 2 external sources: (a) VS Code custom agents docs — validates standard frontmatter fields already in use across ≥4 existing agents, not a new pattern adopted; (b) de Bono's Six Thinking Hats — conceptual background (relevance 0.6), adversarial persona structure derived from internal spec §7/§12 and `challenger.agent.md` pattern. No external patterns implemented into OwlBear. |
| 4 | CLI changes | No | N/A | No CLI command changes. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/critic-voice-agent.md` exists and is linked from task body. Follow-up tasks: none required (task #644 was the designated build task). |

### Files Updated
- None

### Scratch Files Cleaned
- None found (`.owlbear/scratch/644-*` glob returned empty)

[[2026-04-06]] Mon 19:11
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: file exists, valid YAML | share/agents/critic-voice.agent.md exists, 69 lines, frontmatter parses | PASS |
| AC2: user-invocable: false | frontmatter confirmed | PASS |
| AC3: model GPT-5.4 sole string | frontmatter line 7: `model: GPT-5.4 (copilot)`, single string | PASS |
| AC4: purely adversarial | persona section: "adversarial critic", "do not propose alternatives" | PASS |
| AC5: exit behavior clause | persona + output contract: "If position is solid after honest examination, say so and exit. Do not manufacture objections." | PASS |
| AC6: receives position, reads context.md | Input Contract section confirmed | PASS |
| AC7: no file writes, read-only | critical_rules: "Strictly read-only", tools are read-only set | PASS |
| AC8: dual-scope invocation | Dual-Scope section describes Mediator + voice contexts, no scope-specific config | PASS |
| AC9: disable-model-invocation: true | frontmatter confirmed | PASS |
| AC10: exact tool set (5 read-only) | frozenset match in tests, confirmed in frontmatter | PASS |
| AC11: agents: [] | frontmatter confirmed | PASS |

### Test Results
- pytest (task): 39 passed, 0 failed
- pytest (full suite): 3097 passed, 457 failed, 18 skipped — all failures external to #644 (voice scaffolding, session hooks, planner gates, other in-progress tasks)
- ruff: clean

### Architect Quality: 4/5
AC was specific and verifiable. Architect proactively refined 3 new lines and 2 rewrites after challenge review. Minor gap: AC8 needed rewording for verifiability (caught and fixed by architect). Strong upstream work.

### Deduction Breakdown
- Start: 1.00
- Uncommitted test file (test-writer process gap, committed by auditor): -.02
- Full-suite failures in task scope: none (-.00)
- Reviewer evidence: detailed, comprehensive, .97 PASS — trusted (-.00)
- AC quality 4/5: no deduction (> 3)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a4f63df | feat | share/agents/critic-voice.agent.md | #644 |
| 2ba4066 | test | tests/test_critic_voice_agent_644.py | #644 |
