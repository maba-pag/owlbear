# Clean up stale .github/instructions/ references

> **Owning task:** #111 — Clean up stale .github/instructions/ references
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #10 migrated instruction files from `.github/instructions/` to `instructions/`
at the repo root. The original #109 research identified 3 files with stale references.
This research validates those findings and proposes corrected AC.

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| #109 research doc | `docs/research/instructions-readme-update.md` §3 | 1.0 — original finding |
| Task #10 (Port instruction files) | `kanban/tasks/010-port-instruction-files.md` | 1.0 — confirms migration |
| Task #29 (.github/ cleanup) | `kanban/tasks/029-clean-up-github-v1-prompts-and-residual-files.md` | .90 — broader cleanup scope |
| Task #12 (setup script) | `kanban/tasks/012-build-setup-script-owlbear-setup.md` | .85 — setup.py AC context |

## 3. Analysis

### AC item validation

| AC item | File | Actual content at cited line | Stale? | Notes |
|---------|------|------------------------------|--------|-------|
| AC1 | `docs/decisions/README.md` L49 | `.github/skills/decision-requests/SKILL.md` | **NO** | Skills reference, not instructions. `.github/skills/` exists. AC is incorrect. |
| AC2 | `.github/prompts/agent-audit.prompt.md` L15 | `.github/instructions/*.instructions.md` | **YES** | Should reference `instructions/` |
| AC3 | `scripts/setup.py` L40 | `{rel}/.github/instructions` mapping | **YES** | But has test dependency and broader implications |

### AC3 complication: setup.py ripple effects

Removing `.github/instructions` from `scripts/setup.py` requires:

1. Updating `tests/test_setup_script.py` — `test_instructions_locations_has_root_and_github_paths` explicitly asserts `/.github/instructions` exists in the mapping
2. Task #12 (build setup script) is currently in `review` — its AC specifies this mapping
3. `.github/agents` and `.github/skills` mappings are also still in setup.py — removing only instructions creates inconsistency

**Recommendation (.85 confidence):** Defer the setup.py change to task #29 (Clean up
`.github/` v1 prompts and residual files), which already has AC for deleting
`.github/instructions/`, `.github/agents/`, and `.github/skills/`. Cleaning setup.py
mappings should happen atomically when the corresponding `.github/` dirs are deleted.

### Additional stale references (grep results)

| File | Reference | Classification |
|------|-----------|---------------|
| `instructions/README.md` L4 | "Migrated from `.github/instructions/`" | Historical context — keep |
| `kanban/tasks/007-*.md` | Original AC references | Task history — keep |
| `kanban/tasks/010-*.md` | Migration verification notes | Task history — keep |
| `kanban/tasks/012-*.md` L31 | Setup script AC | Will be addressed by #29 |
| `board.json`, `board_state.json`, `tasks.json` | Board snapshots | Not active files — ignore |

## 4. Recommendation (.90 confidence)

**Corrected AC for #111:**

- **Drop AC1** (docs/decisions/README.md) — the reference is to `.github/skills/`, not `.github/instructions/`. Not stale.
- **Keep AC2** (.github/prompts/agent-audit.prompt.md) — update `instructions/` path.
- **Defer AC3** (scripts/setup.py) — move to #29 where all `.github/` mappings get cleaned up atomically. Avoids inconsistency and test breakage.
- **Keep AC4** (grep verify) — verify after AC2 fix.

The only actionable change is AC2: update one line in agent-audit.prompt.md.

## 5. Follow-up Tasks

AC correction and implementation are one builder task. The existing #111 AC should be
corrected per the findings above.
