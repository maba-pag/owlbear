---
id: 897
title: 'Update agent.md command: fields to uv run python'
status: archived
priority: needed
created: 2026-04-16T22:54:12.431883+00:00
updated: 2026-04-17T05:25:56.491746+00:00
tags:
- phase-2
- scope:agent
- config
- platform
parent: 890
depends_on:
- 894
- 895
- 896
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] All 19+ agent.md files in share/agents/ updated
- [ ] Every `command:` field changed from `powershell -NoProfile -NonInteractive -File .owlbear/hooks/{name}.ps1` to `uv run python .owlbear/hooks/{name}.py`
- [ ] Hook type mappings preserved (PreToolUse, PostToolUse, SessionStart unchanged)
- [ ] Agent-to-hook mappings preserved exactly (see research findings for full mapping table)
- [ ] No .ps1 references remain in any agent.md file
- [ ] grep -r "powershell" share/agents/ returns no results
- [ ] grep -r ".ps1" share/agents/ returns no results

## Agent-Hook Mapping (reference)

architect: PreToolUse deny-code-writes | auditor: PreToolUse deny-writes | builder: SessionStart session-context, PostToolUse lint-changed | challenger: PreToolUse deny-writes | code-reader: PreToolUse deny-writes | doc-writer: SessionStart session-context, PreToolUse deny-code-writes | fix-attempt: PostToolUse lint-changed | ideation-architect: PreToolUse allow-stances-only | ideation-critic: PreToolUse deny-writes | ideation-data: PreToolUse allow-stances-only | ideation-enduser: PreToolUse allow-stances-only | ideation-security: PreToolUse allow-stances-only | quality-runner: PreToolUse deny-writes | researcher: PreToolUse deny-code-writes | reviewer: PreToolUse deny-writes | test-writer: SessionStart session-context, PreToolUse deny-src-writes

## Files

- `share/agents/*.agent.md` (19+ files, edit)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/agent-command-fields-897.md
- Sources: 4 studied, 4 high-relevance
- Recommendation: Proceed — mechanical replacement of 19 command: fields across 16 agent files, plus prose cleanup in quality-runner (8 refs) and fix-attempt (2 refs). All Python hooks exist. Confidence: 0.95
- Follow-up tasks created: none (task #897 is itself the implementation unit)
- Decision requests: none — brief decisions D2/D5/D10 already cover this
- Key finding: AC requires zero powershell/.ps1 references in share/agents/ — quality-runner.agent.md has 8 prose PowerShell refs (piping pitfalls, WMI mitigation, code block labels) and fix-attempt.agent.md has 2 code block labels. These need updating alongside the command: fields.
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: update command: fields and remove powershell/ps1 refs from agent files |
| Interface clarity | PASS | AC specifies exact from/to patterns, mapping table, grep verification gates |
| Dependency correctness | PASS | Depends on #894/#895/#896 (all archived). All 7 Python hooks verified on disk |
| Module layering | N/A | Config-only changes, no Python imports |
| TDD compliance | PASS | Test-writer can write regression test (grep-based assertion, no powershell/ps1 in agents/) |
| KISS/YAGNI | PASS | Mechanical replacement, minimal scope |
| Premise challenge | PASS | Required for macOS compat initiative (#890) |
| Pattern consistency | PASS | Target format `uv run python .owlbear/hooks/{name}.py` matches hooks delivered by #894-#896 |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Agent configuration domain only |

### Codebase Verification

- **19 command: lines** across **16 agent files** confirmed via grep (architect, auditor, builder×2, challenger, code-reader, doc-writer×2, fix-attempt, ideation-architect, ideation-critic, ideation-data, ideation-enduser, ideation-security, quality-runner, researcher, reviewer, test-writer×2)
- **Mapping table** matches codebase exactly — all 19 lines verified against AC mapping
- **7 Python hooks** confirmed on disk: allow-stances-only.py, deny-code-writes.py, deny-src-writes.py, deny-writes.py, lint-changed.py, session-context.py (+ deny-scratch-only-writes.py, unused by current agents)
- **6 hookless agents**: curator, ideation-pragmatist, ideator, orchestrator, planner, scribe — no changes needed
- **Prose cleanup** (quality-runner: 8 refs at lines 36,47,55,63,87,98; fix-attempt: 2 refs at lines 78,84) — implicitly required by AC6/AC7 (grep must return no results). Research doc section 3.3 provides specific rewrite guidance

### Challenge Results

- Challenger: RECONSIDER (0.60) — raised concerns about external .ps1 references in setup/setup-guide.md, tests/test_*.py files
- Architect response: REBUTTED — all external concerns already covered by sibling tasks in parent #890 initiative: #901 (setup docs), #900 (init.py), #898 (seed/), #904 (.ps1 deletion), #905 (full validation). Task #897 scope correctly bounded to share/agents/. Challenger confidence reflects cross-initiative awareness gap, not a defect in this task's AC.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| All 19+ agent.md files updated | Minor imprecision — 16 files, 19 command lines | No change needed — mapping table in body is authoritative |
| command: field changed to uv run python | Precise, verifiable | None |
| Hook type mappings preserved | Precise, verifiable | None |
| Agent-to-hook mappings preserved | Precise, mapping table matches codebase | None |
| No .ps1 references remain | Precise, covers both command fields AND prose | None |
| grep powershell returns no results | Precise, forces prose cleanup in quality-runner/fix-attempt | None |
| grep .ps1 returns no results | Precise, forces all reference removal | None |

### Builder Guidance

- Research doc section 3.3 has specific prose rewrite instructions for quality-runner and fix-attempt
- quality-runner pitfall #1: rewrite to platform-neutral (principle is still valid: don't pipe uv run output)
- quality-runner pitfall #5: replace Windows WMI mitigation with `pkill -9 -f pytest`
- All code block labels: `powershell` → `sh`

### Verdict: APPROVE

### Action Taken: Advanced to todo. AC is precise and verifiable. All 13 criteria pass. Dependencies archived. Codebase state confirmed

[[2026-04-17]]

## Test-Writer Notes

- Test file: tests/test_agent_command_fields_897.py
- Classes: `TestFromAC_AgentCommandFields`
- Tests per category: happy 17 (all command fields use uv run python + per-agent mappings), error 2 (no powershell / no .ps1 anywhere)
- Total: 19 tests, all FAIL
- ruff: clean (VS Code diagnostics: no errors)

### AC Coverage

| AC | Tests |
|----|-------|
| AC2: command: changed to uv run python | test_all_hook_commands_use_uv_run_python |
| AC3: hook types preserved | covered implicitly by per-agent mapping tests (SessionStart/PreToolUse/PostToolUse keys asserted) |
| AC4: agent-hook mappings exact | test_{agent}_hook_* (16 tests) |
| AC5: all 19+ files updated | test_all_hook_commands_use_uv_run_python iterates all files |
| AC6: grep powershell → no results | test_no_powershell_in_any_agent_file |
| AC7: grep .ps1 → no results | test_no_ps1_in_any_agent_file |

Commit: `0d04b670` — test: add failing tests for agent command field update (#897, test-writer)
[[2026-04-17]]

## Builder Notes

### Files changed (19 files)

- `share/agents/*.agent.md` — 16 agent files: command: fields updated
- `tests/test_agent_command_fields_897.py` — removed unused `import pytest` (module-level)
- `pyproject.toml` — added F541 to tests per-file-ignores

### Changes applied

1. **19 command: fields** across 16 agent files: `powershell -NoProfile -NonInteractive -File .owlbear/hooks/{name}.ps1` → `uv run python .owlbear/hooks/{name}.py` (bulk sed replacement)
2. **quality-runner prose** — 6 powershell references replaced: critical_rules bullet reworded to platform-neutral, pitfall #1 rewritten (no Windows cmdlets), pitfall #4 code block label `powershell` → `sh`, pitfall #5 rewritten (WMI/Windows → `pkill -9 -f pytest`), scoped/full run code block labels `powershell` → `sh`
3. **fix-attempt prose** — 2 code block labels `powershell` → `sh` (Step 5 verify commands)
4. **ideation-pragmatist YAML fix** — pre-existing bug: unquoted colon in `argument-hint` value caused yaml.ScannerError in test_all_hook_commands_use_uv_run_python; fixed by quoting the value
5. **F541 per-file-ignore** — TestFromAC_AgentCommandFields.test_all_hook_commands_use_uv_run_python has an f-string without placeholder (untouchable TestFromAC class); added F541 to tests/**/*.py per-file-ignores

### Test results

- **19 passed**, 0 failed — all TestFromAC_AgentCommandFields tests green
- ruff: **clean**
- Commit: `89f4c2f2`

### AC coverage

- AC2 ✓ — test_all_hook_commands_use_uv_run_python passes
- AC3 ✓ — hook types preserved in all per-agent mapping tests
- AC4 ✓ — 16 per-agent mapping tests pass
- AC5 ✓ — 19+ files covered by iteration test
- AC6 ✓ — test_no_powershell_in_any_agent_file passes
- AC7 ✓ — test_no_ps1_in_any_agent_file passes
[[2026-04-17]]

## Review Evidence

### Quality-Runner Report

- **pytest:** 19 passed, 0 failed (tests/test_agent_command_fields_897.py)
- **ruff:** clean (tests/test_agent_command_fields_897.py)
- **Coverage:** N/A — config-only task; all assertions read files directly

### Source Verification

- `grep command: share/agents/*.agent.md` → 19 matches, all `uv run python .owlbear/hooks/*.py` — confirmed
- `grep -i powershell share/agents/*.agent.md` → 0 matches — confirmed
- `grep -i .ps1 share/agents/*.agent.md` → 0 matches — confirmed
- `pyproject.toml:114` — F541 added to `tests/**/*.py` per-file-ignores, correctly scoped (not global)

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: All 19+ agent.md files updated | 19 command: lines across 16 agent files confirmed via grep | test_all_hook_commands_use_uv_run_python (iterates all) + 16 per-agent tests | PASS |
| AC2: command: field changed to uv run python | All 19 grep hits show `uv run python .owlbear/hooks/` | test_all_hook_commands_use_uv_run_python | PASS |
| AC3: Hook type mappings preserved | Per-agent tests assert exact hook types (SessionStart, PreToolUse, PostToolUse) | test_builder_hook_mappings, test_doc_writer_hook_mappings, test_test_writer_hook_mappings + 13 others | PASS |
| AC4: Agent-to-hook mappings preserved | 16 per-agent tests each assert exact script name | 16 test_{agent}_hook_* tests | PASS |
| AC5: No .ps1 references remain | grep returns 0 matches | test_no_ps1_in_any_agent_file | PASS |
| AC6: grep powershell → no results | grep returns 0 matches; quality-runner prose verified clean | test_no_powershell_in_any_agent_file | PASS |
| AC7: grep .ps1 → no results | grep returns 0 matches | test_no_ps1_in_any_agent_file | PASS |

### Pass 1 Critical Checks

**5.0 TestFromAC Coverage:** All 7 AC lines covered. Every test would fail if its AC were violated (violations list checked against `== []`). No MISSING or LAX. PASS.

**5.1 Security:** Config-only changes (YAML frontmatter + markdown prose). No shell injection vectors, no secrets, no deserialization. PASS.

**5.2 TestFromAC Integrity:** Builder changed only: removed unused `import pytest` (line-level cleanup). All 19 test methods preserved with original assertions intact. No WEAKENED or REMOVED. PASS.

**5.3 Test Quality:** Assertion specificity STRONG (`violations == []` with detail). Negative path coverage STRONG (test_no_powershell/test_no_ps1 are the error tests). Mutation resistance STRONG (wrong script name or remaining ps1/powershell ref would each fail a distinct test). Independence STRONG (no shared state). Names STRONG (fully descriptive). PASS.

**5.4 Data Safety:** N/A. PASS.

**5.5 Implementation Gap Analysis:** No code paths beyond YAML frontmatter reads. ideation-pragmatist YAML fix implicitly covered — parsing error would surface in test_all_hook_commands_use_uv_run_python. PASS.

**5.6 Necessity Check:** Skipped (config change, no new dependencies).

**5.7 Builder Process Quality:** Single ## Builder Notes section, clean first-pass approach. CLEAN.

### Pass 2 Informational

- None worth noting.

### Verdict

0 deductions. All 7 AC lines evidenced and passing. Test quality STRONG. No security surface. No TestFromAC weakening. Builder process CLEAN.

**Confidence: .98 → PASS**
[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.github/copilot-instructions.md` is 14 lines covering project identity and branches only — no hook command documentation. No update needed. |
| 2 | Module docstrings | No | N/A | Config-only change: only `.agent.md` YAML/prose, `pyproject.toml` per-file-ignores, and test file unused-import removal. No Python modules created or modified. |
| 3 | External attribution | No | N/A | Research doc section 2 cites only internal sources: brief, .owlbear/hooks/*.py, agent files, parent kanban tasks. No external repos or articles. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/agent-command-fields-897.md` exists, linked in task body under "Research" section, follow-up tasks noted as "none needed" in doc section 5. |

### Files updated

None — no documentation impact. No commits needed.

### Scratch files

`find .owlbear/scratch/897-*` → no files. Nothing to clean.
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: All 19+ agent.md files updated | 19 command: lines across 16 agent files confirmed via grep | PASS |
| AC2: command: field changed to uv run python | All 19 lines show `uv run python .owlbear/hooks/*.py` format | PASS |
| AC3: Hook type mappings preserved | SessionStart/PreToolUse/PostToolUse verified per agent | PASS |
| AC4: Agent-to-hook mappings preserved | 16 agents verified against mapping table — all correct | PASS |
| AC5: No .ps1 references remain | grep returns 0 matches across all agent.md files | PASS |
| AC6: grep powershell returns no results | 0 matches; quality-runner + fix-attempt prose cleaned | PASS |
| AC7: grep .ps1 returns no results | 0 matches across all agent.md files | PASS |

### Test Results

- pytest: 4344 passed, ruff clean
- 5 listed failures: 1 in task scope (test_deny_code_writes_hook_591::test_pretooluse_hook_command expects old .ps1 format — intentional cross-task regression, architect scoped test cleanup to sibling tasks in #890 initiative), 1 pre-existing (edit/editFiles tools list), 3 unrelated (test_analysis model tests)
- Task #897 tests (test_agent_command_fields_897.py): 19/19 passing

### Architect Quality: 4/5

Precise and verifiable AC with exact patterns, grep verification gates, and authoritative mapping table. Minor gap: no explicit AC item for updating existing tests that reference old format, but architect addressed this in challenge response by scoping test updates to sibling tasks (#905 full validation).

### Deduction Breakdown

- Start: 1.00
- Full-suite test failure in task scope (test_deny_code_writes_hook_591 expects .ps1, broken by intentional format change — tracked for cleanup in #890 sibling tasks): -.05
- AC quality 4/5 (above threshold): -.00
- Reviewer evidence present and detailed (.98 PASS): -.00
- All 7 AC lines evidenced: -.00
- Lint clean: -.00

### Confidence: .95

### Action: archive
