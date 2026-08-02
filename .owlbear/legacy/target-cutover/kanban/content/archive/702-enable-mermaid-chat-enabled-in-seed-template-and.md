---
id: 702
title: Enable mermaid-chat.enabled in seed template and document diagram rendering paths for agents
status: archived
priority: medium
created: 2026-04-08T21:56:26.0224615+02:00
updated: 2026-04-09T04:46:03.8214308+02:00
started: 2026-04-09T04:46:03.8214308+02:00
completed: 2026-04-09T04:46:03.8214308+02:00
tags:
    - scope:copilot
    - ' type:config'
class: standard
---

## Context

Research #691 confirmed `mermaid-chat.enabled` is NOT active anywhere in the workspace — not in `seed/.vscode/settings.json`, not in the code profile, and no `.vscode/settings.json` exists in the OwlBear dev workspace. The setting is opt-in per VS Code docs.

See `.owlbear/research/mermaid-chat-and-diagram-paths.md`

## Acceptance Criteria

- [ ] AC1: Add `"mermaid-chat.enabled": true` to `seed/.vscode/settings.json` so consumer projects get it via init.py
- [ ] AC2: Add a brief "Diagram Rendering" section to `share/instructions/agent-common.instructions.md` with a 3-row routing table:
  - Mermaid code blocks in chat → `mermaid-chat.enabled` setting
  - HTML + Mermaid CDN → `h-visual-output` skill
  - Excalidraw JSON → `h-excalidraw-diagram` skill
- [ ] AC3: Existing tests pass, ruff clean
- [ ] AC4: Update setup guide (`setup/setup-guide.md`) to mention `mermaid-chat.enabled` in the settings table if appropriate

## Affected Files

- `seed/.vscode/settings.json`
- `share/instructions/agent-common.instructions.md`
- `setup/setup-guide.md` (optional)

[[2026-04-08]] Wed 22:22
## Research
- Research doc: .owlbear/research/mermaid-chat-and-diagram-paths.md (from #691, validated current)
- Sources: 7 studied (prior research doc), 4 high-relevance
- Recommendation: Add `mermaid-chat.enabled: true` to seed template + 3-row routing table in agent-common.instructions.md (confidence: .90)
- Follow-up tasks created: none (this task IS the follow-up from #691)
- Decision requests: none

### Validation Notes
- `seed/.vscode/settings.json` confirmed: only 3 `chat.*Locations` keys, no mermaid setting
- `init.py` `_merge_settings()` handles non-location keys correctly: owlbear value as default, user override wins — new key propagates safely to consumers
- Existing test `test_deep_merge_non_location_keys_shallow_merged_user_wins` validates the merge path needed for AC3
- AC4 (setup-guide): no per-setting table exists; a brief note in the "What Setup Creates" row for `.vscode/settings.json` or troubleshooting section is sufficient
- Tier: T1 — Autonomous. Config tweak + doc update. No architectural change, no new capability, no security impact.
- Challenge: FALLBACK — T1 trivial config/doc task, no architectural decision to challenge

[[2026-04-08]] Wed 22:41
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Config setting + doc for the same feature; one logical change |
| Interface clarity | PASS | AC specifies exact key name, exact file paths, exact table structure |
| Dependency correctness | PASS | No dependencies; standalone |
| Module layering | PASS | Touches only seed template and instruction docs — no code imports |
| TDD compliance | PASS | `type:config` pass-through; existing test `test_deep_merge_non_location_keys_shallow_merged_user_wins` validates the merge path |
| KISS/YAGNI | PASS | Minimal scope — one setting, one routing table, one optional guide mention |
| Premise challenge | PASS | `mermaid-chat.enabled` confirmed absent from workspace; enabling it provides real value for agent diagram rendering in chat |
| Pattern consistency | PASS | Follows existing seed template pattern; `_merge_settings()` non-location branch handles new key correctly (owlbear default, user override wins) |
| Security surface | PASS | No new system boundary; VS Code setting only |
| Single domain | PASS | Config/docs domain only |

### Codebase Verification

- `seed/.vscode/settings.json`: confirmed only 3 `chat.*Locations` keys, no mermaid setting
- `setup/init.py` `_LOCATION_KEYS`: confirmed `mermaid-chat.enabled` falls into the `else` branch (shallow merge, user override wins)
- `agent-common.instructions.md`: confirmed no existing diagram rendering section
- `setup/setup-guide.md`: no per-setting table exists; AC4's "if appropriate" qualifier is correct
- Test coverage: `test_deep_merge_non_location_keys_shallow_merged_user_wins` in `tests/test_setup_init.py:545` validates the merge path

### Challenge

FALLBACK — T1 trivial config/doc task, no architectural decision to challenge.

### Verdict

APPROVED — all AC lines are precise and verifiable, codebase paths confirmed.

[[2026-04-08]] Wed 23:24
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- Passing through to builder.
- AC1–AC4 touch only `seed/.vscode/settings.json`, `share/instructions/agent-common.instructions.md`, and `setup/setup-guide.md` — no Python interfaces.
- Existing test `test_deep_merge_non_location_keys_shallow_merged_user_wins` (tests/test_setup_init.py:545) already validates the `_merge_settings()` path for new non-location keys (AC3 coverage).

[[2026-04-09]] Thu 00:43
## Builder Notes

### Files Changed
- `seed/.vscode/settings.json` — AC1: `"mermaid-chat.enabled": true` added (was already in working tree)
- `share/instructions/agent-common.instructions.md` — AC2: `## Diagram Rendering Paths` section with 3-row routing table (was already in working tree)
- `setup/setup-guide.md` — AC4: Updated `.vscode/settings.json` row to mention `mermaid-chat.enabled`

### Test Results
- `tests/test_setup_init.py`: 46 passed — validates `_merge_settings()` non-location key path (AC3)
- No TestFromAC_ tests (type:config pass-through)

### Lint Status
- ruff: All checks passed (no Python files changed)

### Evidence
- AC1 ✅: `"mermaid-chat.enabled": true` present in `seed/.vscode/settings.json`
- AC2 ✅: 3-row diagram routing table in `agent-common.instructions.md` (Mermaid code block / HTML+CDN / Excalidraw JSON)
- AC3 ✅: 46 existing tests pass, ruff clean
- AC4 ✅: setup-guide `.vscode/settings.json` row updated with mermaid mention

### Commit
`16999ad` — feat: enable mermaid-chat.enabled in seed template and document diagram paths (#702)

[[2026-04-09]] Thu 01:24
## Review Evidence

### Test Results
- pytest: **46 passed, 0 failed** (quality-runner independent run on `tests/test_setup_init.py`)
- ruff: **clean** (exit 0)

### Coverage
- N/A — no Python modules changed (JSON + Markdown only)

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage
No `TestFromAC_*` classes — correct for `type:config` pass-through. SKIP.

#### 5.1 Security Review
- AC1: boolean `true` in JSON — no injection vector
- AC2/AC4: static Markdown content — no OWASP surface
- **Clean.**

#### 5.2 Test Integrity — TestFromAC Comparison
N/A — no TestFromAC_* classes.

#### 5.3 Test Quality
N/A — `type:config` pass-through.

#### 5.4 Data Safety
No data persistence, no LLM output, no concurrency. **Clean.**

#### 5.5 Implementation-Aware Test Gap Analysis
Three file changes, all config/doc:
- `seed/.vscode/settings.json` — one boolean key; `_merge_settings()` non-location path already tested by `test_deep_merge_non_location_keys_shallow_merged_user_wins`. No new code.
- `agent-common.instructions.md` — static routing table section. No testable interface.
- `setup/setup-guide.md` — one row update. No testable interface.
No significant untested paths.

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1: `"mermaid-chat.enabled": true` in seed template | `seed/.vscode/settings.json` line 11 confirmed via grep_search | **PASS** |
| AC2: 3-row diagram routing table in agent-common.instructions.md | Direct read confirms `## Diagram Rendering Paths` section with all 3 rows (Mermaid/HTML+CDN/Excalidraw) | **PASS** |
| AC3: Existing tests pass, ruff clean | 46 passed, 0 failed (quality-runner independent run); ruff exit 0 | **PASS** |
| AC4: setup-guide `.vscode/settings.json` row mentions mermaid-chat.enabled | `setup/setup-guide.md` line 51 confirmed via grep_search | **PASS** |

### Builder Process Quality
1 cycle. Builder notes "files already in working tree" for AC1/AC2 (pre-done by sibling task #691); AC4 (setup-guide) was genuinely new. Commit `16999ad` present. **CLEAN.**

### Deductions
None.

### Verdict
**Confidence: 0.97 → PASS → docs**

[[2026-04-09]] Thu 02:26
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | `copilot-instructions.md` covers only project identity and branch structure (18 lines). No tech-stack, diagram, or seed-template section exists; no appropriate place to add one. |
| 2 | Module docstrings | No | N/A | No Python files changed — only `seed/.vscode/settings.json` (JSON), `agent-common.instructions.md` (Markdown), `setup/setup-guide.md` (Markdown). |
| 3 | External attribution | No | N/A | Research #691 sourced only VS Code Copilot docs (https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features). That URL is already attributed in `sources/overview.md` under Task #683. No new row required. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/mermaid-chat-and-diagram-paths.md` exists and is linked in task body. Follow-up tasks: none needed (task #702 IS the follow-up from #691). |

### Verified File Changes
- `seed/.vscode/settings.json` line 11: `"mermaid-chat.enabled": true` confirmed ✓
- `share/instructions/agent-common.instructions.md` lines 43–46: `## Diagram Rendering Paths` section with all 3 rows confirmed ✓
- `setup/setup-guide.md` line 51: `.vscode/settings.json` row mentions `mermaid-chat.enabled` confirmed ✓

### Scratch Files
No `.owlbear/scratch/702-*` files found — nothing to clean.

### Commit
No doc-writer edits required. Builder commit `16999ad` is the authoritative commit for this task.

[[2026-04-09]] Thu 04:46
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `mermaid-chat.enabled: true` in seed template | `seed/.vscode/settings.json` line 11 confirmed | PASS |
| AC2: 3-row diagram routing table in agent-common | `agent-common.instructions.md` lines 38-46: Mermaid/HTML+CDN/Excalidraw rows confirmed | PASS |
| AC3: Existing tests pass, ruff clean | `test_setup_init.py`: 46 passed, 0 failed; ruff violations (5) all in `serve/mcp-kanban/` — not touched by #702 | PASS |
| AC4: setup-guide mentions mermaid-chat.enabled | `setup/setup-guide.md` line 51 confirmed | PASS |

### Test Results
- pytest (full suite): 3678 passed, 397 failed — all failures in unrelated modules (bearclaw voice, analysis, planner gates, etc.), none in task scope
- pytest (task-scoped): test_setup_init.py 46 passed, 0 failed
- ruff: 5 pre-existing violations in serve/mcp-kanban/ — no violations in task-changed files

### Architect Quality: 5/5
Specific file paths, exact setting name, exact table structure. AC4's "if appropriate" qualifier well-judged. No builder improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 → no deduction
- Lint violations in task scope: 0 → no deduction
- AC quality ≤ 3: no (5/5) → no deduction
- Missing reviewer evidence: no (detailed, PASS) → no deduction
- Full-suite failures in task scope: 0 → no deduction

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 16999ad | feat | seed/.vscode/settings.json, agent-common.instructions.md, setup-guide.md | #702 |
| e22f7d5 | chore | 702 task file | #702 |
