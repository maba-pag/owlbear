---
id: 1459
title: 'B1-agent: Update code-reader agent to match new w-code-review contract'
status: todo
priority: needed
created: 2026-05-08T19:47:13.556859+00:00
updated: 2026-05-09T07:02:28.608766+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
- agent
parent: 1403
depends_on:
- 1458
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Update `share/agents/code-reader.agent.md` to align with the new w-code-review consumer contract. The 8-section output (test_writer-audit, security_review, test_integrity, test_quality, data_safety, test_gaps, necessity_check, informational) is replaced by the 3-item checklist model. Update persona, critical_rules, output_format, and examples.


## Acceptance Criteria

- [ ] `output_format` section in `share/agents/code-reader.agent.md` specifies exactly 4 required output sections matching the w-code-review consumer contract: `## ac_to_code_mapping`, `## test_to_ac_alignment`, `## proof_sufficiency`, `## observations` — old 8-section list removed (td:1)
- [ ] `critical_rules` references the 3-item checklist (Steps 4.1–4.3 of w-code-review: AC→Code Mapping, Test→AC Alignment, Proof Sufficiency) — old §5.0–5.7 / §6.1–6.4 references removed (td:1)
- [ ] All references to the old 8-section model (`test_writer-audit`, `security_review`, `test_integrity`, `test_quality`, `data_safety`, `test_gaps`, `necessity_check`, `informational`) removed from `share/agents/code-reader.agent.md` (td:1)
- [ ] Examples demonstrate findings in the new 4-section format — old 8-section examples replaced (td:1)
- [ ] Persona and boundaries remain adversarial + read-only; no new tools or kanban access added (td:0)

## Builder Guidance

- The authoritative consumer contract is in `share/skills/w-code-review/SKILL.md` → `### Code-Reader Consumer Contract` (input fields unchanged; output sections changed to 4)
- The `<required_reading>` reference to `w-code-review` stays — that's the contract source
- The `description` and `argument-hint` in YAML frontmatter may need minor wording updates but are not load-bearing
- Scope is strictly `share/agents/code-reader.agent.md` — do NOT modify research docs, archived tasks, or w-code-review itself
[[2026-05-09]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single agent file update to match its consumer contract |
| Interface clarity | PASS | AC explicitly names all 4 output sections and the 3-item checklist references |
| Dependency correctness | PASS | #1458 (w-code-review rewrite) is archived/done — contract already landed |
| Module layering | PASS | Agent file reads skill via required_reading — correct direction |
| TDD compliance | PASS | Non-impl task tagged `agent` for test-writer pass-through |
| KISS/YAGNI | PASS | Minimal scope — align one agent file to its already-landed contract |
| Premise challenge | PASS | code-reader.agent.md references 8-section model that no longer exists in w-code-review; update is necessary |
| Pattern consistency | PASS | Follows agent file structure conventions |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Pipeline/agents domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.47)
- Key challenges: (1) task artifact needed explicit AC — addressed via REFINE, (2) missing `agent` pass-through tag — added, (3) AC scope ambiguity on "remove old references" — scoped to target file
- Architect response: accepted all three; refined AC and tags before approving. Challenger confidence was low because the task artifact hadn't been refined yet at evaluation time.

### Test Depth
- Max depth: td:1 (4 lines) + td:0 (1 line)
- Test-writer: SKIP (non-impl task, `agent` tag triggers pass-through)

### Verdict: APPROVE
### Action Taken: Refined AC with explicit 4-section output contract, scoped file boundaries, and builder guidance. Added `agent` pass-through tag. Advanced to todo.