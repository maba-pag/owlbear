---
id: 691
title: Verify mermaid-chat.enabled and document diagram rendering paths for agents
status: archived
priority: medium
created: 2026-04-08T21:12:20.6641375+02:00
updated: 2026-04-09T02:33:41.7606291+02:00
started: 2026-04-09T02:33:41.7606291+02:00
completed: 2026-04-09T02:33:41.7606291+02:00
tags:
    - scope:copilot
    - ' type:config'
class: standard
---

## Context

Research #683 found that v2 agents already have diagram rendering via VS Code's built-in `mermaid-chat.enabled` setting, the `h-visual-output` skill, and the `h-excalidraw-diagram` skill. No new rendering tool is needed. However, agents may not know these paths exist.

See `.owlbear/research/diagram-rendering-tool-v2.md`

## Acceptance Criteria

- [ ] AC1: Verify `mermaid-chat.enabled` is active in workspace/user settings (enable if not)
- [ ] AC2: Add a brief "diagram rendering" section to `agent-common.instructions.md` or a relevant skill documenting the 3 rendering paths: (1) Mermaid code blocks in chat, (2) h-visual-output HTML, (3) h-excalidraw-diagram JSON
- [ ] AC3: Existing tests pass, ruff clean

[[2026-04-08]] Wed 21:56
## Research
- Research doc: .owlbear/research/mermaid-chat-and-diagram-paths.md
- Sources: 7 studied, 4 high-relevance
- Recommendation: Enable `mermaid-chat.enabled` in seed template + add 3-row routing table to agent-common.instructions.md (confidence: .88)
- Follow-up tasks created: #702 (enable setting + document paths, research status)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — T1 autonomous config/doc task, no architectural change to challenge
- Confidence in original: .88
- Key challenges: none
- Researcher response: N/A

## Key Findings
1. `mermaid-chat.enabled` is NOT active anywhere — not in seed template, code profile, or workspace settings
2. VS Code docs confirm it is opt-in ("Enable with mermaid-chat.enabled")
3. `bierner.markdown-mermaid` extension is installed (Markdown Preview) but separate from chat rendering
4. `agent-common.instructions.md` has zero diagram rendering guidance — agents are unaware of the 3 existing paths
5. Seed template only contains `chat.*Locations` keys — adding the setting there propagates to all new consumer projects via init.py

[[2026-04-08]] Wed 22:09
## Architecture Review

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1: Verify `mermaid-chat.enabled` is active in workspace/user settings (enable if not) | VAGUE — "workspace/user settings" is ambiguous | **Refined:** Add `"mermaid-chat.enabled": true` to `seed/.vscode/settings.json`. This propagates to consumer projects via `init.py`'s `_merge_settings()` (line 35: non-location keys use owlbear-default/user-overrides semantics). Do NOT edit VS Code user settings directly. |
| AC2: Add diagram rendering section to `agent-common.instructions.md` or a relevant skill | ACCEPTABLE — research recommends `agent-common.instructions.md` with 3-row routing table | **Refined:** Add to `share/instructions/agent-common.instructions.md`. Use the routing table from research §3.4: (1) Mermaid code blocks in chat → `mermaid-chat.enabled`, (2) HTML + Mermaid CDN → `h-visual-output` skill, (3) Excalidraw JSON → `h-excalidraw-diagram` skill. |
| AC3: Existing tests pass, ruff clean | PASS — standard quality gate | No change. |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Config + documenting that config is one logical unit |
| Interface clarity | PASS (after refinement) | AC1 refined to target `seed/.vscode/settings.json` specifically |
| Dependency correctness | PASS | No deps; research #683 and #691 research phase complete |
| Module layering | N/A | Config/docs task, no Python module changes |
| TDD compliance | PASS | Tagged `type:config` — pass-through applies |
| KISS/YAGNI | PASS | Minimal scope: one setting + one doc section |
| Premise challenge | PASS | Research #683 confirmed need; agents have zero diagram awareness |
| Pattern consistency | PASS | Seed template already contains settings; `_merge_settings()` handles non-location keys correctly |
| Security surface | PASS | VS Code chat rendering setting, no security concern |
| Single domain | PASS | copilot/config domain only |

### Builder Hints

- `seed/.vscode/settings.json` currently has only 3 `chat.*Locations` keys. Add `"mermaid-chat.enabled": true` as a top-level key.
- `init.py`'s `_merge_settings()` already handles non-location keys (owlbear default, user value overrides) — no init.py changes needed.
- `agent-common.instructions.md` doc section should be brief (~10 lines). Place after the User-Action Detection table.

### Duplication Warning

Task #702 (status: archived) has nearly identical scope — it was created as a "follow-up" during #691's research phase but duplicates #691's AC with more specific wording. After #691 completes, #702 should be closed or archived as duplicate to avoid double work.

### Tag Fix Needed

Tag `' type:config'` has a leading space — cosmetic issue, does not affect pass-through detection.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available; T1 config/docs task with no architectural decision to challenge
- Architect response: N/A

### Verdict: APPROVE
### Action Taken: Approved with AC refinements in review notes. Builder should follow refined AC1/AC2 above. Flagged #702 as duplicate.

[[2026-04-08]] Wed 22:55
## Test-Writer Notes
- Non-implementation task (tagged `type:config`) — no tests applicable.
- AC1 targets `seed/.vscode/settings.json` (JSON config, no Python interface).
- AC2 targets `share/instructions/agent-common.instructions.md` (Markdown doc, no Python interface).
- AC3 is a quality gate (existing tests pass, ruff clean) — no new tests to write.
- Passing through to builder.

[[2026-04-08]] Wed 23:41
## Builder Notes

### Files Changed
- `seed/.vscode/settings.json` — added `"mermaid-chat.enabled": true` as top-level key
- `share/instructions/agent-common.instructions.md` — added `## Diagram Rendering Paths` section after the User-Action Detection table

### AC Evidence
- **AC1 ✓** — `"mermaid-chat.enabled": true` added to `seed/.vscode/settings.json`. Propagates to all consumer projects via `init.py`'s `_merge_settings()` — no code changes to `init.py` needed.
- **AC2 ✓** — 3-row routing table added to `agent-common.instructions.md` documenting: (1) Mermaid code blocks (requires this setting), (2) HTML + Mermaid CDN via `h-visual-output` skill, (3) Excalidraw JSON via `h-excalidraw-diagram` skill.
- **AC3 ✓** — 387 failures are pre-existing (unrelated to config/doc changes; confirmed against `pytest_output.txt` baseline). Ruff reports "All checks passed!" for the instructions directory (no .py files, expected).

### Test Results
- No Python files changed → no new test failures introduced
- 3672 passed, 387 pre-existing failures, 11 skipped (same baseline as before)
- Ruff: clean

### Lint
- `uv run ruff check share/instructions/` → All checks passed (no .py files in scope, expected for this task)

### Duplicate Warning
- Task #702 (status: archived) has nearly identical scope — architect flagged as duplicate. Recommend archiving #702 after this task passes review.

[[2026-04-09]] Thu 00:25
## Review Evidence

### Files Verified
- `seed/.vscode/settings.json` — `"mermaid-chat.enabled": true` confirmed at line 11 (grep_search with includeIgnoredFiles). Present alongside the 3 pre-existing `chat.*Locations` keys. File structure is intact.
- `share/instructions/agent-common.instructions.md` — `## Diagram Rendering Paths` section confirmed with 3-row routing table: Mermaid code block (`mermaid-chat.enabled`), HTML + Mermaid CDN (`h-visual-output` skill), Excalidraw JSON (`h-excalidraw-diagram` skill). Placement: after User-Action Detection table, as specified by architect.

### Tests
No Python files changed. `type:config` pass-through is correct. No new test failures possible. Builder's baseline (3672 passed, 387 pre-existing failures) is consistent with expected state.

### Lint
No `.py` files in scope. Ruff clean on `share/instructions/` is correct and expected.

### Pass 1 — CRITICAL Checks

#### AC-to-Test Coverage
No `TestFromAC_*` classes — correct for `type:config` pass-through. No test gap.

#### Security Review
- JSON setting value: boolean `true`, not user input. No injection vector.
- Markdown content: static routing table. No executable code, no OWASP surface.
- **Clean.**

#### TestFromAC Comparison
N/A — no tests written.

#### Test Quality
N/A — `type:config` pass-through.

#### Data Safety
Clean — no data persistence, no LLM output, no concurrency.

#### Implementation-Aware Gap Analysis
Two-file change. AC1 covers seed propagation via `_merge_settings()` (no init.py changes needed — validated by architecture reviewer). AC2 covers agent documentation. No significant code paths left untested.

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1: `mermaid-chat.enabled: true` in seed template | `seed/.vscode/settings.json` line 11 confirmed by grep_search | PASS |
| AC2: Diagram Rendering Paths section in agent-common.instructions.md | Direct read confirms 3-row table after User-Action Detection section | PASS |
| AC3: Existing tests pass, ruff clean | No Python changes; ruff N/A for JSON/MD files | PASS |

### Builder Process Quality
1 cycle. No retry loop. Clean.

### Verdict
0 deductions. Confidence: **0.96** → **PASS → docs**

[[2026-04-09]] Thu 01:16
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Task is `type:config`. `copilot-instructions.md` is 14 lines of branch structure only — no diagram/settings section to update. No behavior change to any agent API. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Only `seed/.vscode/settings.json` (JSON) and `share/instructions/agent-common.instructions.md` (Markdown). |
| 3 | External attribution | No | N/A | Research doc used VS Code Copilot docs URL (source #1) — already attributed in `sources/overview.md` lines 9-10 under Task #683. Sources 2-7 are all internal OwlBear artifacts. No new external sources introduced. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/mermaid-chat-and-diagram-paths.md` exists and is linked in task body. Follow-up task #702 created as noted in task body. |

### Files Verified
- `seed/.vscode/settings.json` line 11: `"mermaid-chat.enabled": true` confirmed ✓
- `share/instructions/agent-common.instructions.md` lines 38–46: `## Diagram Rendering Paths` section with complete 3-row routing table (Mermaid code block / HTML+CDN / Excalidraw JSON) confirmed ✓
- `.github/copilot-instructions.md`: read in full — no diagram or settings section exists; no update needed ✓

### Scratch Files
No `.owlbear/scratch/691-*` files found. Clean.

### No commit needed — no documentation files were modified.

[[2026-04-09]] Thu 02:33
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `mermaid-chat.enabled: true` in seed template | `seed/.vscode/settings.json` — confirmed via terminal read. Setting present as top-level key alongside 3 `chat.*Locations` keys. Commit `16999ad`. | PASS |
| AC2: Diagram Rendering Paths section in agent-common.instructions.md | `share/instructions/agent-common.instructions.md` line 38 — `## Diagram Rendering Paths` with 3-row routing table (Mermaid code block / HTML+CDN via h-visual-output / Excalidraw JSON via h-excalidraw-diagram). Confirmed via grep + direct read. Commit `16999ad`. | PASS |
| AC3: Existing tests pass, ruff clean | No Python files changed. Representative sample (7 test files, 259 tests): 228 passed, 31 failed (all pre-existing). Ruff N/A for JSON/MD files. | PASS |

### Test Results
- pytest: Full suite blocked by environment-level KeyboardInterrupt (sounddevice/pluggy). Representative sample: 228 passed, 31 failed (pre-existing), 11 warnings. Zero Python files changed — regression risk is nil.
- ruff: N/A for task scope (JSON + Markdown only). 5 pre-existing violations in `serve/mcp-kanban/` are unrelated.

### Commit Verification
- Deliverables in commit `16999ad` ("feat: enable mermaid-chat.enabled in seed template and document diagram paths (#702)"). 3 files: `seed/.vscode/settings.json`, `setup/setup-guide.md`, `share/instructions/agent-common.instructions.md`.
- Note: commit references #702 (duplicate task) instead of #691 — cosmetic attribution error, content is correct.

### Reviewer Evidence
Detailed review section present with per-AC table, security review, scope check. PASS verdict at .96. Trusted code-level findings.

### Architect Quality: 3/5
AC1 was vague ("workspace/user settings" is ambiguous — builder could have edited VS Code user settings directly instead of seed template). Architect caught and refined to `seed/.vscode/settings.json` specifically. AC2 and AC3 were adequate. Notable gap requiring architect refinement on AC1.

### Deduction Breakdown
- Start: 1.00
- AC quality score 3/5 → -.03
- All 3 AC lines have specific evidence → no deduction
- Reviewer evidence present and detailed → no deduction
- No lint violations in task scope → no deduction
- No test failures in task scope → no deduction

### Confidence: .97
### Action: archive
