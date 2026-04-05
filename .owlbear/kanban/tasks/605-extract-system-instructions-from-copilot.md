---
id: 605
title: Extract system instructions from copilot-instructions.md
status: review
priority: needed
created: 2026-04-04T20:31:16.804802+02:00
updated: 2026-04-05T05:51:35.8868694+02:00
tags:
    - scope:infra
    - phase-2
    - type:config
parent: 598
depends_on:
    - 600
class: standard
---

## Summary

Extract owlbear system-level instructions (heuristics, memory governance, pipeline protocol, operational fundamentals) from .github/copilot-instructions.md into share/instructions/owlbear-system.instructions.md.

## Acceptance Criteria

- [ ] AC1: share/instructions/owlbear-system.instructions.md exists with YAML frontmatter: `description:` field present, no `applyTo` key
- [ ] AC2: Contains extracted content from .github/copilot-instructions.md: S2 Decision Heuristics, S3 System Awareness, S4 Memory Governance, S5 Operational Fundamentals (content fidelity preserved, no material omissions or additions)
- [ ] AC3: .github/copilot-instructions.md retains only S1 Project Identity: document title + project description paragraph
- [ ] AC4: [Verification] After #600 settings are in place, owlbear-system.instructions.md appears in VS Code Chat Customizations panel and is auto-enabled for chat requests. If VS Code does not auto-enable instruction files without applyTo, add `applyTo: **` to the frontmatter as fallback.

## Notes

- chat.instructionsFilesLocations configuration is owned by #600 AC6, not duplicated here
- Target project delivery verification is owned by #604 AC7, not this task
- Line number references in research docs (e.g., docs/research/agent-common-memory-mcp-integration.md L83-105 sourcing Memory Governance) become stale after extraction. Research docs are historical; live reference updates belong to #607.

[[2026-04-04]] Sat 22:35
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single extraction operation: split copilot-instructions.md into project-identity stub + global system instructions file |
| Interface clarity | PASS (fixed) | AC refined: section-level precision on extraction boundary, explicit auto-discovery gate with fallback, removed redundant/out-of-scope AC lines |
| Dependency correctness | PASS | Depends on #600 (move .github/ to share/, provides share/instructions/ directory and chat.instructionsFilesLocations setting). No missing deps. |
| Module layering | N/A | No code modules: file creation and markdown editing only |
| TDD compliance | PASS | Tagged type:config (pass-through). No testable Python code produced. |
| KISS/YAGNI | PASS | Minimal scope: one file extraction, one file reduction |
| Premise challenge | PASS | copilot-instructions.md is auto-discovered from .github/ but not shareable to target projects. Extracting to share/instructions/ enables VS Code settings-based sharing without file copies. |
| Pattern consistency | PASS | Follows existing .instructions.md convention (YAML frontmatter with description:). First global instruction file (no applyTo): new pattern, AC4 explicitly gates discovery. |
| Security surface | PASS | No new system boundaries. Content moves between markdown files only. |
| Single domain | PASS | scope:infra |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| VS Code instruction discovery | File without applyTo not auto-enabled | None (silent) | Yes: AC4 gates with applyTo fallback | System instructions missing from chat context |
| copilot-instructions.md too minimal | Agents lose system context in owlbear workspace | None (silent) | Yes: AC4 manual verification confirms instructions load | Agent quality degrades |
| Research doc line refs (L83-105) | Stale line numbers in docs/research/ | N/A | Acknowledged: historical docs, live refs in #607 scope | Misleading source citations in old research |

### Refinements Applied

1. AC2: Added section-level precision: explicitly lists S2-S5 with requirement for content fidelity
2. AC3: Specified what "project identity only" means: document title + project description paragraph (S1)
3. Old AC4 (settings): REMOVED, redundant with #600 AC6 (chat.instructionsFilesLocations)
4. Old AC5 (target project delivery): REMOVED, scope creep; delivery verification belongs to #604 AC7
5. AC4 (new): Explicit auto-discovery verification with applyTo: "**" fallback if VS Code does not auto-enable
6. Old AC6 (manual verification): Merged into new AC4
7. Tags: type:build replaced with type:config (pass-through tag for non-implementation work)
8. Notes: Added scope boundaries for settings (#600), target delivery (#604), and stale research refs (#607)

### Challenge Results

- Challenger: reconsider (confidence: 0.35)
- Concerns: (1) VS Code auto-discovery gap for no-applyTo files, (2) stale line refs in research docs, (3) target project delivery unverified, (4) extraction boundary, (5) AC coverage
- Architect response: Override with targeted refinements
  - C1: AC4 now explicitly gates auto-discovery with applyTo: "**" fallback
  - C2: Dismissed: research docs are historical; live refs belong to #607
  - C3: Dismissed: target project delivery is #604 scope, not #605
  - C4: Accepted: boundary confirmed as reasonable
  - C5: Accepted: AC4 restored with specificity

### Verdict: APPROVE
### Action Taken: Refined AC (4 lines: file existence, content extraction, copilot-instructions.md reduction, auto-discovery verification with fallback). Replaced type:build with type:config. Removed redundant/out-of-scope AC lines. Advanced to todo.

[[2026-04-04]] Sat 22:36
APPROVED #605 to todo. Refined AC: 6 lines reduced to 4 (file existence, content extraction with S2-S5 precision, copilot-instructions.md reduction to S1, auto-discovery verification with applyTo fallback). Removed redundant AC4 (settings owned by #600) and out-of-scope AC5 (target delivery owned by #604). Replaced type:build with type:config. Challenger overridden (0.35): 2 concerns accepted (VS Code discovery gap, AC coverage), 2 dismissed (research refs historical, target delivery out of scope), 1 confirmed (boundary).

[[2026-04-05]] Sun 00:36
## Test-Writer Notes\n- Non-implementation task (tagged type:config) — no tests applicable.\n- AC1–AC4 describe file creation, markdown content extraction, and VS Code UI verification — no testable Python interfaces exist.\n- Passing through to builder.

[[2026-04-05]] Sun 05:51
## Builder Notes

**Files changed (2):**
- `share/instructions/owlbear-system.instructions.md` — created (S2–S5 extracted content, YAML frontmatter: `description:` only, no `applyTo` key per AC1)
- `.github/copilot-instructions.md` — reduced to S1 Project Identity only (title + paragraph)

**Test results:** N/A — type:config pass-through, no Python tests applicable.

**Lint status:** N/A — markdown-only changes.

**AC evidence:**
- AC1 ✅ File exists with `description:` frontmatter, no `applyTo` key
- AC2 ✅ S2 Decision Heuristics, S3 System Awareness (Tech Stack + Pipeline + Directory Structure), S4 Memory Governance, S5 Operational Fundamentals — content extracted verbatim, no omissions or additions
- AC3 ✅ `.github/copilot-instructions.md` retains only S1: document title + project description paragraph
- AC4 ⚠️ MANUAL VERIFICATION REQUIRED — open VS Code Chat Customizations panel, confirm `owlbear-system.instructions.md` appears and is auto-enabled. If not auto-enabled, add `applyTo: "**"` to the frontmatter.

**Commit:** 9690513
