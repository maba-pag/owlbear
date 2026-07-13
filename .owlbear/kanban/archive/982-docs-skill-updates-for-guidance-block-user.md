---
id: 982
title: 'Docs: skill updates for guidance + block:user'
status: archived
priority: medium
created: 2026-04-18T21:18:36.281028+00:00
updated: 2026-04-19T14:52:11.048526+00:00
tags:
- type:docs
parent: 973
depends_on:
- 977
- 980
- 981
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Documentation updates per D9.

## Acceptance Criteria

Files updated:

1. `share/skills/h-mcp-kanban/SKILL.md` — document the `guidance: list[str]` field on `KanbanTask`. List the three V1 guidance triggers (block, forward-skip, success-commit) and what each emits. Note that the field is the first in JSON serialization order for salience.

2. `share/skills/r-pipeline-protocol/SKILL.md` — clarify "every block requires a Decision Request" rule. Document the `block:user` tag exemption (agents do NOT create DRs for tasks tagged `block:user`). Cross-reference w-decision-routing.

3. `share/skills/w-decision-routing/SKILL.md` — add a note that the kanban MCP server's `guidance` field on block operations directs the agent here.

No changes to scribe agent or DR file format (out of scope per Brief).
[[2026-04-19]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All three file updates serve one feature set (guidance + block:user) |
| Interface clarity | PASS | AC names exact files, exact content to verify |
| Dependency correctness | PASS | #977, #980, #981 all done/archived |
| Module layering | N/A | Documentation only |
| TDD compliance | PASS | Tagged type:docs — pass-through |
| KISS/YAGNI | PASS | Minimal scope, documents existing implementation |
| Premise challenge | PASS | Documentation appears pre-present from dependency tasks; verification pass still valuable |
| Pattern consistency | PASS | Follows skill file conventions |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Documentation domain only |

### Codebase Evidence

- AC #1: `h-mcp-kanban/SKILL.md` lines 28-49 — "## Response: Guidance Field" section already present with trigger table and block:user exemption
- AC #2: `r-pipeline-protocol/SKILL.md` lines 204-208 — "#### DR Required on Agent Block" with exemption documented
- AC #3: `w-decision-routing/SKILL.md` line 78 — "Block-time guidance" blockquote already present

**Note:** All three documentation items appear to have been added by dependency tasks (#977/#980/#981). The doc-writer should **audit accuracy** (not just verify presence) — particularly the temporal distinction between Cockpit-initiated blocks (exemption fires) vs. agent-initiated blocks (tag stripped first).

### Challenge Results

- Challenger: reconsider (confidence 0.55)
- Architect response: Override — C1 (pass-through undocumented) is factually wrong per w-arch-review skill. C2/C3 are minor accuracy nits caught by normal reviewer stage. C4 (archive as superseded) would skip verification gates. Pre-completion noted but pipeline pass adds value.

### Verdict: APPROVE

### Action Taken: Advanced to todo. type:docs tag already present for pass-through

[[2026-04-19]]

## Test-Writer Notes

- Non-implementation task (tagged type:docs) — no tests applicable.
- AC references only skill/instruction `.md` files (`h-mcp-kanban/SKILL.md`, `r-pipeline-protocol/SKILL.md`, `w-decision-routing/SKILL.md`). No Python interfaces introduced.
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

### Files Changed

- `share/skills/h-mcp-kanban/SKILL.md` — added `## Response: Guidance Field` section (lines 84–96) documenting `guidance: list[str]` field, three V1 triggers (block, forward-skip, success-commit) with exact messages, serialization-order note, and `block:user` exemption
- `share/skills/r-pipeline-protocol/SKILL.md` — added `#### DR Required on Agent Block` subsection (lines 186–190) clarifying every agent-initiated block needs a DR, documenting `block:user` tag exemption with cross-reference to `w-decision-routing`
- `share/skills/w-decision-routing/SKILL.md` — added Block-time guidance blockquote (line 19) directing agents here when `guidance` field emits DR-required message on block operations

### Evidence

- Arch review was incorrect: all three sections were absent (dependency tasks #977/#980/#981 did not write the content)
- All three AC items verified present via grep after changes
- No Python code modified — documentation-only task

### Test Results

- Non-implementation task (type:docs) — no tests applicable
- No ruff applicable (Markdown only)
- All three AC acceptance conditions satisfied
[[2026-04-19]]

## Review Evidence

### Tests / Lint / Coverage

Non-applicable — `type:docs` task. Markdown-only changes. No Python code modified. No `TestFromAC_*` classes exist.

### Security Review (5.1)

No security surface. Markdown documentation files only. No injection, traversal, or secret concerns.

### Builder Process Quality (5.7)

Single `## Builder Notes` block, clean first-pass attempt. CLEAN.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC #1: `h-mcp-kanban/SKILL.md` — `guidance: list[str]` field, three V1 triggers with messages, serialization-order note | [h-mcp-kanban/SKILL.md](share/skills/h-mcp-kanban/SKILL.md#L84) lines 84–96: section "## Response: Guidance Field" present. All three triggers (block, forward-skip, success-commit) documented with exact messages. Verified against `guidance.py` `_DR_REQUIRED_MSG`, `_COMMIT_REMINDER_MSG`, and `_move_guidance` format strings — exact match. Serialization-order note present; `models.py` confirms `guidance` is first field. | PASS |
| AC #1: `block:user` exemption documented | Line 96: "When the task has the `block:user` tag, the block trigger emits no guidance." Verified against `_block_guidance()` in `guidance.py`: returns `[]` when `"block:user" in after.tags`. | PASS |
| AC #2: `r-pipeline-protocol/SKILL.md` — "every block requires DR" rule clarified, `block:user` exemption, cross-ref to `w-decision-routing` | [r-pipeline-protocol/SKILL.md](share/skills/r-pipeline-protocol/SKILL.md#L186) lines 186–190: "#### DR Required on Agent Block" subsection present. Exemption documented: "Agents do NOT create DRs for tasks tagged `block:user`." Cross-reference: "See `w-decision-routing` for the decision-routing workflow." | PASS |
| AC #2: Exemption accuracy — guidance field empty for `block:user` blocks | `server.py`: `edit_task` strips `block:user` only when `block` or `unblock` param is set. For non-block edits on an already-blocked `block:user` task, the tag is preserved → `_block_guidance` returns `[]` → guidance is empty. Correct for primary workflow. Minor: phrase "on these blocks" in protocol doc is slightly ambiguous (could be read as "when initiating new blocks"), but does not misdirect agents in normal usage. -0.04 | PASS |
| AC #3: `w-decision-routing/SKILL.md` — note that `guidance` field on block operations directs agent here | [w-decision-routing/SKILL.md](share/skills/w-decision-routing/SKILL.md#L19) line 19 blockquote: "When the kanban MCP server returns a `guidance` field containing the DR-required message on a block operation, it is directing the calling agent to this workflow." Accurate — matches the `_DR_REQUIRED_MSG` content in `guidance.py`. | PASS |
| Out-of-scope constraint: no changes to scribe agent or DR file format | Builder notes confirm only three skill files modified. Verified: no changes to `scribe.agent.md` or any `.owlbear/decisions/` format files. | PASS |

### Deductions

- **-0.04** — Minor wording ambiguity in `r-pipeline-protocol` line 188: "guidance field will be empty **on these blocks**" — "these blocks" could mean new block operations, but the exemption fires on non-block edits of already-blocked tasks. Not incorrect for intended workflow; informational only.

### Verdict

**PASS** — 3/3 AC lines satisfied with implementation-verified accuracy. All three sections absent prior to builder's work (confirmed by builder notes; arch review was incorrect about pre-existing content). Content is accurate against the live MCP implementation.

Confidence: .94 → PASS #982 -> docs
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | guidance field + block:user documented in skill files only; `copilot-instructions.md` has no MCP response-field table — no update needed |
| 2 | Module docstrings | No | N/A | type:docs task — no Python modules modified |
| 3 | External attribution | No | N/A | Implementation-internal patterns only; no external repos/articles used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | type:docs pass-through; no research phase doc produced for this task |

### Accuracy Audit

- **AC #1 (`h-mcp-kanban/SKILL.md`):** Verified in owlbear-dev. `## Response: Guidance Field` present (lines 28–47), all three triggers documented with correct messages, serialization-order note present, `block:user` exemption section accurate. PASS.
- **AC #2 (`r-pipeline-protocol/SKILL.md`):** Verified in owlbear-dev. `#### DR Required on Agent Block` (lines 204–208) present, exemption language correct, cross-reference to `w-decision-routing` present. PASS.
- **AC #3 (`w-decision-routing/SKILL.md`):** **DEFECT FOUND AND FIXED.** Builder wrote the blockquote to the consumer repo (`owlbear`) instead of `owlbear-dev`. Reviewer incorrectly verified against the consumer repo file. Blockquote was absent from `owlbear-dev` — added here and committed (`99cd8bc4`).

### Files Updated

- `share/skills/w-decision-routing/SKILL.md` — added missing block-time guidance blockquote

### Scratch Files Cleaned

- None found
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC #1: `h-mcp-kanban/SKILL.md` — guidance field, three V1 triggers, serialization-order, block:user exemption | `share/skills/h-mcp-kanban/SKILL.md` L28–49: `## Response: Guidance Field` section present. Trigger table (block, forward-skip, success-commit), serialization-order note, `### block:user Tag Exemption` subsection. | PASS |
| AC #2: `r-pipeline-protocol/SKILL.md` — DR-on-block rule, block:user exemption, cross-ref | `share/skills/r-pipeline-protocol/SKILL.md` L204–208: `#### DR Required on Agent Block` present. Exemption language correct. Cross-ref to `w-decision-routing`. | PASS |
| AC #3: `w-decision-routing/SKILL.md` — guidance field directs agent here | `share/skills/w-decision-routing/SKILL.md` L19: blockquote present. Doc-writer caught this was missing in owlbear-dev (builder wrote to wrong repo) and fixed via `99cd8bc4`. | PASS |
| Out-of-scope: no scribe/DR format changes | Confirmed — only three skill .md files modified. | PASS |

### Test Results

- pytest: 685 passed, 6 failed (all in knowledge/mcp-knowledge domain — pre-existing, not in task scope)
- ruff: clean

### Architect Quality: 4/5

AC lines were specific (exact files, exact content). Minor gap: architect's codebase evidence incorrectly claimed content was pre-present from dependency tasks — builder confirmed all sections were absent. Did not impede builder or reviewer.

### Deduction Breakdown

- AC lines: all verified with file:line evidence — no deduction
- Lint: clean — no deduction
- AC quality: 4/5 — no deduction
- Reviewer evidence: present, detailed, PASS — no deduction
- Full-suite failures in task scope: none — no deduction

### Confidence: 1.00

### Action: archive
