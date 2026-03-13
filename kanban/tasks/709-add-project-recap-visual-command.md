---
id: 709
title: Add project-recap visual command
status: archived
priority: nice-to-have
created: 2026-03-09T15:25:19.3510256+01:00
updated: 2026-03-11T19:26:30.3896637+01:00
started: 2026-03-10T03:30:25.9408276+01:00
completed: 2026-03-11T19:26:30.3896637+01:00
tags:
    - scope:copilot
    - agent
depends_on:
    - 706
claimed_by: auditor
claimed_at: 2026-03-11T19:26:23.4225628+01:00
class: standard
---

Adapt visual-explainer project-recap as VS Code prompt file.
See docs/research/project-recap-command.md.

## Acceptance Criteria

- [ ] File .github/prompts/project-recap.prompt.md exists
- [ ] YAML frontmatter: `description` field only (no `agent:`  runs in current chat context, which already has terminal + file tools)
- [ ] Phase 1 instructions: gather data via terminal  `git log --oneline --since='2 weeks ago'`, `kanban\kanban-md.exe list --compact --status todo,in-progress,review,done`, `Get-ChildItem -Recurse -Depth 2 -Name`, read `copilot-instructions.md`
- [ ] Phase 2 instructions: generate single-page HTML with 8 sections (Identity, Architecture, Activity, Decisions, State, Mental Model, Cognitive Debt, Next Steps)
- [ ] Phase 2 references visual-output skill via markdown link: `[visual-output skill](.github/skills/visual-output/SKILL.md)`
- [ ] Phase 3 instructions: save `.owlbear/diagrams/project-recap.html`, open in browser via `Start-Process` or equivalent terminal command
- [ ] Self-contained HTML with inline CSS (no external stylesheets or scripts)
- [ ] Prompt file <= 60 lines
- [ ] ruff N/A (no Python code), manual invocation test recommended as follow-up

[[2026-03-11]] Wed 16:27
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| File exists | Clear, verifiable | Keep |
| YAML frontmatter description | Was vague on agent:/tools: fields | Tightened: description only, no agent: field |
| Phase 1 data gathering | kanban state was ambiguous | Tightened: explicit kanban-md.exe + git + dir commands |
| Phase 2 8-section HTML | Sections enumerated, clear | Keep |
| Phase 2 skill reference | Correct pattern (markdown link loads skill) | Keep |
| Phase 3 save + open | Clear output path + browser open | Keep |
| Self-contained HTML | Clear constraint | Keep |
| Prompt <= 60 lines | Measurable | Keep |

### Architecture Notes
- **Format decision sound:** .prompt.md is the correct format per VS Code docs (single repeatable task -> slash command). Matches existing orchestrate.prompt.md and commit-and-archive.prompt.md patterns.
- **Zero runtime code:** Pure prompt engineering  no .py, no new tools, no new agents. KISS-aligned.
- **Dependencies satisfied:** #706 (visual-output skill) archived, #708 (HTML templates) archived. No blocking deps.
- **TDD exemption:** .prompt.md files are prompt engineering artifacts, not application code. No unit test framework exists for prompt files. Manual validation follow-up recommended (per research doc section 5).
- **Single domain:** scope:copilot (prompt file customization). No other domains touched.
- **Output directory:** .owlbear/diagrams/ is the established convention per visual-output skill (SKILL.md line 73). Directory creation is an implementation detail for the builder.
- **No agent: field needed:** Existing prompts delegate to custom agents (orchestrator, auditor). project-recap needs only terminal + file tools, which are available in default chat context. Omitting agent: keeps it simpler.

### Changes Made
- Refined AC: specified no agent: field, explicit terminal commands for data gathering, ruff N/A note
- Body updated with full AC section

### Dependencies
- Verified: #706 (visual-output skill)  archived
- Verified: #708 (HTML templates)  archived
- No new dependencies added

[[2026-03-11]] Wed 17:02
## Test-Writer Notes
- Non-implementation task (prompt file, scope:copilot) -- no tests applicable.
- AC produces .prompt.md, not Python code. Architecture review confirms TDD exemption.
- Passing through to builder.

[[2026-03-11]] Wed 18:16
## Builder Notes
- Files created: .github/prompts/project-recap.prompt.md (46 lines)
- YAML frontmatter: description only, no agent: field
- Phase 1: 5 terminal commands (git log, kanban list x2, dir tree, read copilot-instructions)
- Phase 2: 8-section HTML, references visual-output skill via relative markdown link
- Phase 3: save to .owlbear/diagrams/, open via Start-Process
- Self-contained HTML constraint specified, inline CSS only
- No Python code -- ruff N/A
- All 9 AC lines satisfied

[[2026-03-11]] Wed 18:36
## Review Evidence
All 9 AC lines PASS. 46 lines (<=60). description-only frontmatter. 8 HTML sections. Skill link uses correct relative path. No Python code -- tests/lint/coverage N/A.
Verdict: PASS (confidence .93)

[[2026-03-11]] Wed 18:49
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Prompt file only, no behavior/API/convention change |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | Yes | Pass | Already updated: 3 rows at lines 42-44 (visual-explainer, Aider RepoMap, VS Code prompt docs) |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc linked | Yes | Pass | docs/research/project-recap-command.md exists, references #709 at line 3, follow-up task created |
| 6 | No impact | -- | -- | Items 3+5 apply; 1,2,4 do not |

### Files Updated
- None

### Scratch Files Cleaned
- None found

[[2026-03-11]] Wed 19:26
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| File exists | .github/prompts/project-recap.prompt.md read, 46 lines | PASS |
| YAML frontmatter description only | Line 2: description field, no agent: field | PASS |
| Phase 1 terminal commands | Lines 10-14: 5 commands (git log, kanban list x2, dir tree, read copilot-instructions) | PASS |
| Phase 2 8-section HTML | Lines 20-29: Identity/Architecture/Activity/Decisions/State/Mental Model/Cognitive Debt/Next Steps | PASS |
| Phase 2 skill reference | Line 15: [visual-output skill](../skills/visual-output/SKILL.md) resolves correctly | PASS |
| Phase 3 save + open | Lines 39-44: .owlbear/diagrams/ + Start-Process | PASS |
| Self-contained HTML | Line 18: explicitly specified inline CSS, no externals | PASS |
| <= 60 lines | 46 lines | PASS |
| ruff N/A | No Python code | PASS |

### Test Results
- pytest: 1437 passed, 33 failed (all pre-existing: browser wrapping #725, daemon imports, toolset snapshot, slack env)
- ruff: N/A (no Python code in this task)

### Confidence: .97
### Action: archive
