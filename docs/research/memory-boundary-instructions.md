# Memory Boundary Instructions Implementation

> **Owning task:** #11 — Write Copilot Memory boundary instructions
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #11 asks: where and how should the memory boundary instruction be implemented to constrain what agents store in the VS Code built-in memory tool, preventing layer duplication across OwlBear's three-layer knowledge architecture?

The prerequisite research (#5, `docs/research/copilot-memory.md`) established the boundary text and confirmed behavioral enforcement works. This research determines the implementation vehicle.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|-----------|-----------|
| S1 | OwlBear Memory Research (#5) | docs/research/copilot-memory.md | 1.0 |
| S2 | VS Code Settings Reference — Memory settings | code.visualstudio.com/docs/copilot/reference/copilot-settings | .95 |
| S3 | VS Code Custom Instructions docs | code.visualstudio.com/docs/copilot/customization/custom-instructions | 1.0 |
| S4 | GitHub Copilot Memory docs | docs.github.com/en/copilot/concepts/agents/copilot-memory | .85 |
| S5 | OwlBear copilot-instructions.md | .github/copilot-instructions.md (line 68) | .90 |
| S6 | awesome-copilot memory-bank.instructions.md | github.com/github/awesome-copilot/tree/main/instructions | .70 |

## 3. Analysis

### Where to place the boundary instruction

| Criterion | copilot-instructions.md | Dedicated .instructions.md | agent-common.instructions.md |
|-----------|------------------------|---------------------------|------------------------------|
| Single-responsibility | Low — mixes concerns | High — memory-only | Low — already 280+ lines |
| Auto-loaded | Yes (always-on) | Yes (applyTo: **) (S3) | Yes (applyTo: **) |
| Discovery | Already loaded | instructions/ in settings | Already loaded |
| Maintenance | Must edit large file | Edit small focused file | Must edit large file |
| Pattern consistency | — | Matches python/frontend .instructions.md pattern | — |
| KISS | Adds to bloat | Cleanly scoped | Adds to bloat |

### Content design

The boundary instruction should cover three areas (mapped to AC):

| Area | AC | Source |
|------|-----|--------|
| What to store in user memory | AC2 | S1 §4 |
| What to exclude | AC3 | S1 §4 |
| Management commands | AC5 | S1 §5 |

Testing (AC4) is behavioral — the #5 research (S1 §4a) confirmed agents follow explicit boundary constraints. The implementation task should document a manual test procedure.

### Format decision

VS Code `.instructions.md` files use YAML frontmatter with `applyTo` glob patterns (S3). With `applyTo: "**"`, the instruction applies to all files — effectively always-on. This is functionally equivalent to adding content to `copilot-instructions.md` but cleaner (S3: "Use multiple .instructions.md files per topic and apply them selectively").

## 4. Recommendation (.85 confidence)

**Create `instructions/memory.instructions.md`** with `applyTo: "**"`.

Rationale: follows existing project pattern (one `.instructions.md` per concern), stays KISS (small focused file), auto-loaded via `chat.instructionsFilesLocations` which already includes `instructions/`. Content derived from #5 research §4 boundary text, extended with management reference for AC5.

Risk: behavioral enforcement only (no hard technical guard). Mitigation: periodic manual audit of `/memories/` contents. Same limitation as all instruction-based constraints (S1 §4a).

Alternative rejected: adding to `copilot-instructions.md` — violates single-responsibility, already 200+ lines. Adding to `agent-common.instructions.md` — already 280+ lines, memory boundaries are orthogonal to agent coordination rules.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement memory boundary instruction file" --priority important --status ideation --tags "phase-1,scope:knowledge,type:docs" -b "## Objective
Create instructions/memory.instructions.md with applyTo ** to constrain built-in memory tool usage.

## Acceptance Criteria
- [ ] Create instructions/memory.instructions.md with YAML frontmatter (applyTo: **, description)
- [ ] Boundary text constrains user memory to: tool usage patterns, CLI flags, agent behavior, what worked/failed
- [ ] Boundary text explicitly excludes: architecture decisions, research findings, project-specific patterns, domain knowledge
- [ ] Include management section: Chat: Show Memory Files command, memory view/delete operations
- [ ] Manual test: run agent session, verify /memories/ contents stay in scope, document result in PR
- [ ] Add instructions listing entry to copilot-instructions.md instructions table if one exists

## Content Source
Boundary text from docs/research/copilot-memory.md section 4. Management commands from section 5.
See docs/research/memory-boundary-instructions.md for implementation rationale."
```
