---
id: 467
title: Create challenger.agent.md (adversarial pre-decision review subagent)
status: in-progress
priority: needed
created: 2026-03-31T05:04:45.7284032+02:00
updated: 2026-03-31T07:35:17.3803548+02:00
tags:
    - scope:agents
    - phase-2
class: standard
---

Implement the Challenger agent per docs/research/challenger-subagent-design.md S3c-d.

AC:
- [ ] agents/challenger.agent.md exists in agents/ directory
- [ ] Frontmatter `name: challenger`
- [ ] Frontmatter `description`: one-line describing adversarial pre-decision reasoning challenge
- [ ] Frontmatter `argument-hint`: follows code-reader pattern with input field placeholders (task_id, proposed_verdict, reasoning, ac_lines, codebase_evidence, research_doc)
- [ ] Frontmatter `user-invocable: false`
- [ ] Frontmatter `disable-model-invocation: true`
- [ ] Frontmatter `model: Claude Opus 4.6 (copilot)` (single model, not array)
- [ ] Frontmatter `tools: [read/readFile, read/viewImage, read/problems, search, vscode/memory]` (canonical tool IDs, assign mode, read-only)
- [ ] Frontmatter `agents: []` (leaf subagent, no nesting)
- [ ] `<persona>` section defines adversarial challenge role: find weaknesses in reasoning, surface blind spots, identify counter-arguments; explicitly states agent does NOT validate/confirm the original analysis and does NOT edit files or kanban tasks
- [ ] Input contract table with 6 fields: task_id (string, required), proposed_verdict (string, required), reasoning (string, required), ac_lines (string[], required), codebase_evidence (string, required), research_doc (string, optional) -- types and descriptions per S3d
- [ ] Output contract with 6 sections: Challenges (array of category/description/severity: critical/moderate/minor), Blind Spots, Alternative Angles, Risk Assessment (overall: low/medium/high), Confidence in Original (.0-1.0 float), Recommendation (proceed/reconsider/block)
- [ ] Output is structured text only -- no file edits, no kanban commands, no tool calls that modify state

Sibling tasks: #468 (arch-review integration, depends on this), #469 (researcher expansion, depends on #468)

[[2026-03-31]] Tue 06:23
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| agents/challenger.agent.md exists | Clear, verifiable | Keep |
| Frontmatter name: challenger | Clear | Keep |
| Frontmatter description | Clear | Keep |
| Frontmatter argument-hint | Refined: added field list | Rewritten |
| Frontmatter user-invocable: false | Clear | Keep |
| Frontmatter disable-model-invocation: true | Clear | Keep |
| Frontmatter model (single Opus 4.6) | Clear, matches research S3g | Keep |
| Frontmatter tools (canonical IDs) | Refined: shorthand names replaced with canonical tool IDs | Rewritten |
| Frontmatter agents: [] | Clear | Keep |
| Persona section | Refined: added explicit NOT-validation constraint | Rewritten |
| Input contract (6 fields) | Refined: enumerated all fields with types | Rewritten |
| Output contract (6 sections) | Refined: enumerated sections with value types | Rewritten |
| Output is structured text only | Added: explicit read-only constraint | Added |

### Architecture Notes
Follows code-reader.agent.md pattern exactly: assign-mode, read-only tools, structured I/O contract, leaf subagent. Research (docs/research/challenger-subagent-design.md) is thorough -- grounded in Du et al. 2023, Liang et al. 2024, and confirmed L2 nesting from #228.

Key decisions preserved from research:
- Single model (Opus 4.6) not array -- challenger must match consuming agent capability
- Assign mode -- read-only prevents scope creep, same as code-reader
- One-shot interaction -- VS Code subagents return once, no multi-round debate

TDD not applicable: .agent.md is declarative configuration, not application code. Structural validation handled by scripts/validate_agents.py. Follows code-reader precedent.

### Changes Made
- Refined AC: shorthand tool names replaced with canonical VS Code tool IDs
- Refined AC: added argument-hint field requirement with input placeholders
- Refined AC: enumerated I/O contract fields explicitly instead of count-only reference
- Refined AC: added explicit read-only constraint on output
- Refined AC: persona AC now specifies NOT-validation boundary

### Dependencies
- Verified: no depends_on needed (standalone agent file)
- Verified: #468 (arch-review integration) correctly depends on #467
- Verified: #469 (researcher expansion) correctly depends on #468
