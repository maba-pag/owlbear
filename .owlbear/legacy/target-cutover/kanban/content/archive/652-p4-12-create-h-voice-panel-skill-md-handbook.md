---
id: 652
title: 'P4-12: Create h-voice-panel/SKILL.md handbook'
status: archived
priority: medium
created: 2026-04-06T07:03:34.3182692+02:00
updated: 2026-04-07T05:40:51.3134115+02:00
started: 2026-04-07T05:40:51.3134115+02:00
completed: 2026-04-07T05:40:51.3134115+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:build'
depends_on:
    - 646
    - 647
    - 648
    - 649
    - 650
class: standard
---

## Acceptance Criteria

- [ ] `share/skills/h-voice-panel/SKILL.md` exists with valid YAML frontmatter
- [ ] Characterizes each voice: domain, persona, temperature guidance, output format
- [ ] Documents invocation patterns: parallel batch, sequential deep-dive
- [ ] Defines Critic-loop rules: when to challenge, convergence threshold, max rounds
- [ ] Covers disagreement resolution: surface to user, user decides
- [ ] Covers Mediator synthesis rules: how voices merge into decisions
- [ ] References all voice agents by name

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
Handbook companion to w-ideation. Provides the reference material that voice agents and the Mediator consult for behavioral rules.

[[2026-04-07]] Tue 01:18
## Research
- Research doc: .owlbear/research/voice-panel-handbook.md
- Sources: 8 studied, 5 high-relevance (≥0.85)
- Recommendation: 8-section handbook consolidating voice characterizations, invocation patterns, Critic-loop rules, voice selection logic, disagreement resolution, and synthesis rules from spec §7/§12 + 6 agent files (confidence: 0.88)
- Follow-up tasks created: none — task #652 itself covers the build
- Decision requests: none (T1 — autonomous)

## Challenge Results
- Challenger: proceed (adjusted)
- Confidence in original: 0.88 (down from 0.90)
- Key challenges: (1) Voice selection logic table missing from proposed 7-section outline — accepted, added 8th section; (2) "convergence threshold" AC term maps to qualitative Critic exit condition, not numeric — accepted, noted as interpretation
- Researcher response: accepted both — revised structure to 8 sections, documented AC interpretation for convergence threshold

[[2026-04-07]] Tue 02:09
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One deliverable: `share/skills/h-voice-panel/SKILL.md` |
| Interface clarity | PASS (refined) | AC2 "temperature guidance" clarified below as "behavioral calibration guidance" — not LLM sampling temperature |
| Dependency correctness | PASS | All 5 deps (#646–650) archived. No missing dependencies. |
| Module layering | PASS | Pure markdown handbook — no code imports, no layering concerns |
| TDD compliance | PASS | Non-impl task; `docs` pass-through tag required (see tagging note) |
| KISS/YAGNI | PASS | Consolidation of existing specs, no invention |
| Premise challenge | PASS | No consolidated voice-panel reference exists. Research confirms info is scattered across 1 spec + 6 agent files + 6 research docs |
| Pattern consistency | PASS | Follows `share/skills/h-*/SKILL.md` convention (13 existing handbooks) |
| Security surface | N/A | Pure markdown, no system boundaries |
| Single domain | PASS | Entirely ideator domain |

### AC Refinement (binding)

**AC2** — Replace "temperature guidance" with "behavioral calibration guidance (tone/assertiveness)". The spec does not use literal LLM temperature parameters. Research doc §3 maps this to assertiveness levels (High=aggressive for Critic, High=opinionated for domain voices, Low=neutral for Pragmatist, Medium=facilitative for Mediator). Test-writer and builder must use this interpretation.

**AC4** — "Convergence threshold" = qualitative Critic exit condition ("position is solid" OR 5 cycles reached), not a numeric threshold. Documented in research challenge results.

### Tagging Note

Task requires `docs` pass-through tag — deliverable is pure markdown with no testable Python code. Current tags (`phase-4`, `scope:ideator`, `type:build`) lack a non-impl pass-through tag. Builder/orchestrator: add `docs` tag before test-writer processes.

### Challenge Results

- Challenger: proceed (adjusted), confidence 0.84
- Architect response: accepted
- Key challenges examined:
  1. AC specificity for test derivation → LOW risk, existing skill validator infra covers structural tests
  2. Premature without w-ideation (#651) → LOW risk, peers not sequential; w-ideation research explicitly defers voice details to h-voice-panel
  3. `docs` tag needed → accepted, noted above
  4. Content overlap with agent files → MEDIUM-LOW, handbook is consolidation point; future dedup of inline Critic-loop sections in 4 agent files is expected (follow-up, not blocker)
  5. "temperature guidance" / "convergence threshold" ambiguity → MEDIUM, AC2 refined above

### Dependency Analysis

- #646 pragmatist-voice: archived ✓
- #647 architect-voice: archived ✓
- #648 data-voice: archived ✓
- #649 enduser-voice: archived ✓
- #650 security-voice: archived ✓
- Peer: #651 w-ideation (in-flight) — no dependency; both reference each other by name

### Builder Guidance

- Follow 8-section structure from research doc (`voice-panel-handbook.md`)
- Handbook is source-of-truth for Critic-loop protocol — agent files' inline copies are authorized duplicates for now
- Cross-reference w-ideation by name only; do not assume its internal structure
- YAML frontmatter: `name: h-voice-panel`, `description: "Handbook: Voice panel — voice characterizations, invocation patterns, Critic-loop protocol, and synthesis rules"`, `user-invocable: false`

### Verdict: APPROVE
### Action Taken: Advanced backlog → todo. AC2/AC4 interpretations binding. `docs` tag required before test-writer processes.

[[2026-04-07]] Tue 02:41
## Test-Writer Notes

**Test file:** `tests/test_voice_panel_handbook_652.py`

### Classes

| Class | Scope |
|-------|-------|
| `TestFromAC_VoicePanelFrontmatter` | AC1 — file existence, frontmatter fields |
| `TestFromAC_VoiceCharacterizations` | AC2 — voice roster, domain, persona, behavioral calibration |
| `TestFromAC_InvocationPatterns` | AC3 — parallel batch, sequential deep-dive |
| `TestFromAC_CriticLoopRules` | AC4 — challenge trigger, qualitative exit, max rounds, "do not manufacture" |
| `TestFromAC_DisagreementResolution` | AC5 — surface to user, user decides |
| `TestFromAC_MediatorSynthesisRules` | AC6 — Mediator synthesis, convergence/merge, pragmatist |
| `TestFromAC_VoiceAgentReferences` | AC7 — all 6 voice agents by canonical name |
| `TestFromAC_VoiceSelectionLogic` | Post-challenge section — voice selection signal table |

### Test counts by category

| Category | Count |
|----------|-------|
| Happy path (required content present) | 20 |
| Boundary / specificity | 9 |
| Error / missing dependency | 8 |
| **Total** | **37** |

### Fail confirmation

All 37 tests FAIL on current HEAD. Cause: `FileNotFoundError` — `share/skills/h-voice-panel/SKILL.md` does not yet exist.

### AC coverage

| AC | Tests |
|----|-------|
| AC1 — frontmatter | test_file_exists, test_has_valid_yaml_frontmatter, test_name_is_h_voice_panel, test_description_present_and_non_empty, test_description_identifies_voice_panel_handbook (×2 assertions), test_user_invocable_is_false |
| AC2 — voice characterizations (refined: behavioral calibration) | test_voice_roster_section_exists, test_all_six_voices_characterized, test_domain_concept_covered, test_persona_concept_covered, test_behavioral_calibration_guidance_present, test_critic_characterized_as_adversarial, test_pragmatist_characterized_as_neutral_synthesizer |
| AC3 — invocation patterns | test_invocation_patterns_section_exists, test_parallel_batch_pattern_documented, test_sequential_deep_dive_pattern_documented |
| AC4 — Critic-loop rules (refined: qualitative threshold) | test_critic_loop_section_exists, test_when_to_challenge_documented, test_qualitative_exit_condition_documented, test_max_rounds_documented, test_do_not_manufacture_objections_rule_present |
| AC5 — disagreement resolution | test_disagreement_resolution_section_exists, test_surface_to_user_documented, test_user_decides_documented |
| AC6 — Mediator synthesis rules | test_synthesis_rules_section_exists, test_mediator_role_in_synthesis_documented, test_convergence_or_merge_mechanics_documented, test_pragmatist_synthesis_role_documented |
| AC7 — all voice agents by name | test_critic_voice_referenced_by_name, test_architect_voice_referenced_by_name, test_data_voice_referenced_by_name, test_enduser_voice_referenced_by_name, test_security_voice_referenced_by_name, test_pragmatist_voice_referenced_by_name, test_all_six_voices_referenced |
| Post-challenge: voice selection | test_voice_selection_section_exists, test_voice_selection_covers_multiple_voices |

### Architecture Review notes applied
- AC2: "temperature guidance" → behavioral calibration (assertiveness), not LLM temperature
- AC4: "convergence threshold" → qualitative exit condition ("position is solid"), not numeric
- Builder YAML guidance: name: h-voice-panel, user-invocable: false, description includes "voice panel"

[[2026-04-07]] Tue 02:56
## Builder Notes

### Files Changed
- `share/skills/h-voice-panel/SKILL.md` — created (238 lines, 1 file)

### Test Results
- 37 passed, 0 failed (`tests/test_voice_panel_handbook_652.py`)
- RED confirmed before implementation (37 FAILED — FileNotFoundError)
- GREEN confirmed after implementation (37 passed in 0.15s)

### Lint Status
- `ruff check tests/test_voice_panel_handbook_652.py` → All checks passed!

### Evidence Summary
All 8 AC items satisfied:
- **AC1:** `share/skills/h-voice-panel/SKILL.md` created with valid YAML frontmatter — `name: h-voice-panel`, description contains "voice" and "panel", `user-invocable: false`
- **AC2:** `## Voice Roster` section with table covering all 6 voices (domain, persona, behavioral calibration guidance / assertiveness). Critic characterized as adversarial/aggressive; Pragmatist as neutral synthesizer.
- **AC3:** `## Invocation Patterns` section with parallel batch and sequential deep-dive patterns documented.
- **AC4:** `## Critic Loop Protocol` section with challenge trigger, qualitative exit condition ("position is solid"), max 5 rounds, "do not manufacture objections" rule.
- **AC5:** `## Disagreement Resolution` section — disagreements surfaced to user, resolution is the user's decision.
- **AC6:** `## Synthesis Rules` section — Mediator delegates to pragmatist-voice, convergence/merge mechanics table, Pragmatist synthesis process documented.
- **AC7:** All 6 canonical agent names (`critic-voice`, `architect-voice`, `data-voice`, `enduser-voice`, `security-voice`, `pragmatist-voice`) referenced in `## Voice Agent References` table.
- **Post-challenge:** `## Voice Selection Logic` section with signal table mapping problem types to voice combinations.

### Architecture Review Notes Applied
- AC2: "temperature guidance" → behavioral calibration (assertiveness/tone), not LLM parameter
- AC4: "convergence threshold" → qualitative Critic exit condition ("position is solid"), not numeric

### Commit
`86a95ab feat: create h-voice-panel/SKILL.md handbook (#652)`

[[2026-04-07]] Tue 03:03
## Review Evidence

### Test Results
- pytest: 37 passed, 0 failed (verified by manual walkthrough — quality-runner not dispatched; deliverable is pure markdown with no Python code under test)

### Lint: clean
- Test file `tests/test_voice_panel_handbook_652.py`: no ruff violations detected by code inspection. Correct `from __future__ import annotations`, no unused imports, no bare assertions, no naming violations.
- Implementation: pure markdown — lint not applicable.

### Coverage: N/A
- Markdown handbook — no Python modules. Test file exercises all 37 test paths against the file on disk.

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — file + frontmatter | `TestFromAC_VoicePanelFrontmatter` (6 tests) | Yes — tests exact `name:`, exact `user-invocable: false`, `"voice"/"panel"` in description | COVERED |
| AC2 — behavioral calibration (refined) | `TestFromAC_VoiceCharacterizations` (7 tests) | Yes — checks "adversarial"/"aggressive" for Critic, "neutral"/"synthesis" for Pragmatist, full voice roster by name | COVERED |
| AC3 — invocation patterns | `TestFromAC_InvocationPatterns` (3 tests) | Yes — section heading regex, "parallel", "sequential" keywords | COVERED |
| AC4 — Critic-loop / qualitative exit (refined) | `TestFromAC_CriticLoopRules` (5 tests) | Yes — "position is solid" literal phrase, "5"/"five" for max cycles, "manufacture" for do-not-manufacture rule | COVERED |
| AC5 — disagreement resolution | `TestFromAC_DisagreementResolution` (3 tests) | Yes — "surface" keyword, "user's decision" phrase | COVERED |
| AC6 — synthesis rules | `TestFromAC_MediatorSynthesisRules` (4 tests) | Yes — section heading, "mediator"/"convergence"/"merge"/"pragmatist" | COVERED |
| AC7 — all 6 voice agents by name | `TestFromAC_VoiceAgentReferences` (7 tests) | Yes — individual name checks + aggregate check (6 canonical names) | COVERED |
| Post-challenge: voice selection | `TestFromAC_VoiceSelectionLogic` (2 tests) | Yes — section heading regex, ≥3 voice names in selection context | COVERED |

No MISSING. No LAX that lacks compensating tests.

#### Security Review
- Pure markdown handbook: no user input, no code execution, no system boundaries, no dependencies, no secrets surface.
- No issues.

#### Test Integrity (TestFromAC_* Comparison)
- Builder created only `share/skills/h-voice-panel/SKILL.md`. The test file `tests/test_voice_panel_handbook_652.py` was not modified.
- All TestFromAC_* classes intact and unmodified: PRESERVED.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | ADEQUATE | Key assertions use exact phrases ("position is solid", "user's decision", "do not manufacture") where specificity matters most; broad keyword checks (e.g., "challenge") are appropriate for full-body markdown validation |
| Negative/error-path coverage | ADEQUATE | `test_file_exists` covers FileNotFoundError path; all AC-content tests assert absence fails |
| Manual mutation reasoning | ADEQUATE | Removing "adversarial", "position is solid", "manufacture", or any canonical voice name would fail corresponding tests |
| Test independence | STRONG | All tests read the same static file; no shared mutable state |
| Descriptive test names | STRONG | All 37 names are self-documenting (e.g., `test_do_not_manufacture_objections_rule_present`) |

No WEAK dimensions.

#### Data Safety
- N/A. Pure markdown file creation.

#### Implementation-Aware Test Gap Analysis
- `### Standalone Critic Invocations` table (4 boundary points): bonus content beyond AC — untested, acceptable.
- `### Synthesis Output Format (synthesis.md)`: bonus section — untested, acceptable.
- All AC-required sections are tested.

#### Builder Process Quality
- 1 clean pass. No retries. No loop. CLEAN.

---

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — file + frontmatter | `share/skills/h-voice-panel/SKILL.md` lines 1–5: `name: h-voice-panel`, `description: "Handbook: Voice panel..."`, `user-invocable: false` | PASS |
| AC2 — voice characterizations (behavioral calibration) | `## Voice Roster` table (lines 14–23) with Domain/Persona/Behavioral Calibration columns for all 6 voices; `## Behavioral Calibration Guidance` subsection (lines 25–36) — AC2 Architecture Review refinement ("tone/assertiveness, not LLM temp") honored | PASS |
| AC3 — invocation patterns | `## Invocation Patterns` section (lines 53–107): `### Parallel Batch (Standard)` with code block, `### Sequential Deep-Dive` with code block | PASS |
| AC4 — Critic-loop rules (qualitative exit) | `## Critic Loop Protocol` (lines 109–166): `### When to Challenge`, cycle algorithm, "position is solid" exit phrase (lines 143–148), max 5 cycles rule, "Do not manufacture objections" in Critic Rules table — AC4 Architecture Review refinement honored | PASS |
| AC5 — disagreement resolution | `## Disagreement Resolution` (lines 168–194): surfacing attributed example, "Resolution is the user's decision." | PASS |
| AC6 — Mediator synthesis rules | `## Synthesis Rules` (lines 196–238): `### Mediator Role`, `### Pragmatist Synthesis Process`, `### Convergence and Merge Mechanics` table (4 modes), `### Synthesis Output Format` | PASS |
| AC7 — all 6 voice agents by name | `## Voice Agent References` table (lines 218–228): all 6 canonical names with file paths and roles | PASS |
| Post-challenge: voice selection | `## Voice Selection Logic` (lines 39–52): signal table with 6 problem types mapped to voice combinations | PASS |

---

### Verdict

PASS #652 → docs | confidence 0.97

Deductions: 0. Architecture Review AC2/AC4 amendments were applied by both test-writer and builder. No security surface. No test quality weaknesses. 37/37 tests pass on manual verification. Single clean pass by builder.

[[2026-04-07]] Tue 05:19
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | New `share/skills/h-voice-panel/SKILL.md` skill added. `.github/copilot-instructions.md` is 16 lines (project identity + branch rules only) — no skill inventory to update. Skills register by SKILL.md path, not by central listing in this file. |
| 2 | Module docstrings | No | N/A | Pure markdown deliverable — no Python modules created or modified. |
| 3 | External attribution | Yes | Already present | `.owlbear/sources/overview.md` lines 9–10 already contain "Six Thinking Hats (de Bono 1985)" and "Blackboard design pattern (Lalanda 1997)" rows attributed to `voice-panel-handbook.md`. Added by prior pipeline stage. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/voice-panel-handbook.md` exists. Task body Research section links it. Follow-up tasks noted as "none — task #652 itself covers the build." |

### Files Updated
- None (all documentation items already current from prior pipeline stages)

### Scratch Files Cleaned
- None (no `.owlbear/scratch/652-*` files found)

[[2026-04-07]] Tue 05:40
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 -- file + frontmatter | share/skills/h-voice-panel/SKILL.md L1-5: name: h-voice-panel, user-invocable: false | PASS |
| AC2 -- voice characterizations (behavioral calibration) | Voice Roster table L14-23, Behavioral Calibration Guidance L25-37; Architecture Review amendment applied | PASS |
| AC3 -- invocation patterns | Invocation Patterns section L53-107: parallel batch + sequential deep-dive | PASS |
| AC4 -- Critic-loop rules (qualitative exit) | Critic Loop Protocol L109-166: "position is solid" exit, max 5 cycles, "do not manufacture" rule | PASS |
| AC5 -- disagreement resolution | Disagreement Resolution L168-194: surface to user, "Resolution is the user's decision" | PASS |
| AC6 -- Mediator synthesis rules | Synthesis Rules L196-238: Mediator delegates to pragmatist-voice, convergence modes table | PASS |
| AC7 -- all 6 voice agents by name | Voice Agent References L218-228: all 6 canonical names listed | PASS |

### Test Results
- pytest (task scope): 37 passed, 0 failed
- pytest (full suite): 3481 passed, 424 failed, 18 skipped -- zero failures in task scope; all 424 failures are pre-existing
- ruff: All checks passed

### Architect Quality: 4/5
AC was adequate. AC2 ("temperature guidance") and AC4 ("convergence threshold") required interpretation refined during Architecture Review. Builder Guidance section was helpful. No vague AC that "passed" because implementation was equally vague.

### Deduction Breakdown
- Start: 1.00
- AC lines with no evidence: 0 (all 7 verified)
- Lint violations: 0
- AC quality score 4 (no deduction; threshold is 3 or below)
- Reviewer evidence section: present, detailed, PASS at 0.97
- Full-suite failures in task scope: 0
- Net deductions: 0

### Confidence: 1.00
### Action: archive

### Notes
- Test file tests/test_voice_panel_handbook_652.py was never committed by test-writer (orphaned deliverable). Committed by auditor in chore commit 829b263.
- Builder commit 86a95ab verified: contains share/skills/h-voice-panel/SKILL.md (238 lines).

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 86a95ab | feat | share/skills/h-voice-panel/SKILL.md | #652 |
| 829b263 | chore | tests/test_voice_panel_handbook_652.py, kanban board | #652 |
