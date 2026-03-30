# Delete Empty .github/agents/ and Clean Stale Settings

> **Owning task:** #166 — Delete empty .github/agents/ and clean stale settings
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #166 follows up from the `.github/` v1 cleanup research (#29, see `docs/research/github-v1-cleanup.md` sec 3). The `.github/agents/` directory is confirmed empty (agents ported to root `agents/`), but stale references remain in `scripts/setup.py` and `.vscode/settings.json`.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `docs/research/github-v1-cleanup.md` — #29 research | Original analysis identifying these stale refs |
| S2 | `scripts/setup.py` L33–44 | Contains stale `.github/agents` (L35) and `.github/instructions` (L42) mappings |
| S3 | `.vscode/settings.json` `chat.agentFilesLocations` | Contains stale `".github/agents": true` entry |
| S4 | `tests/test_setup_script.py` L108–143 | Two tests assert `.github/agents` and `.github/instructions` paths exist |
| S5 | `.github/agents/` directory listing | Confirmed empty — safe to delete |

## 3. Analysis

### Files to change

| File | Line(s) | Change | Risk |
|------|---------|--------|------|
| `.github/agents/` | dir | Delete empty directory | None — confirmed empty [S5] |
| `.vscode/settings.json` | `chat.agentFilesLocations` | Remove `".github/agents": true` | None — path resolves to empty dir |
| `scripts/setup.py` | L35 | Remove `f"{rel}/.github/agents": "OwlBear GitHub Agents"` | Low — only affects new project bootstrap |
| `scripts/setup.py` | L42 | Remove `f"{rel}/.github/instructions": "OwlBear GitHub Instructions"` | Low — `.github/instructions/` already deleted by #117 |
| `tests/test_setup_script.py` | L108–118 | Update `test_agent_files_locations_has_root_and_github_paths` — remove `has_github` assertion, rename to `test_agent_files_locations_has_root_path` | Required — test will fail otherwise |
| `tests/test_setup_script.py` | L131–143 | Update `test_instructions_locations_has_root_and_github_paths` — remove `has_github` assertion, rename to `test_instructions_locations_has_root_path` | Required — test will fail otherwise |

### AC gap (.95 confidence)

The AC says "Verify setup.py tests still pass" but **two tests explicitly assert the `.github/` paths exist** [S4]. These tests must be updated as part of the task — they will fail on the changed setup.py output. The test name and assertion changes are straightforward (remove `has_github` assertion, simplify test name).

## 4. Recommendation (.95 confidence)

N/A — trivial cleanup. All changes are deletions/removals with no design alternatives. The only nuance is the test gap documented above, which should be added to the AC.

## 5. Follow-up Tasks

Task #166 already exists with correct AC (plus the test update gap). No new tasks needed — the AC refinement is appended to the task body below.
