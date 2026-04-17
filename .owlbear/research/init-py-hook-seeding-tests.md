# Tests: setup/init.py .py Hook Seeding

> **Owning task:** #899 — Tests: setup/init.py .py hook seeding
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Task #899 (child of #890 macOS-compat) requires RED tests verifying that `setup/init.py` seeds `.py` hooks instead of `.ps1`. The brief (O2) mandates: "`python ../owlbear/setup/init.py` seeds `.py` hooks (not `.ps1`), produces settings without Windows-only terminal profiles."

**Question:** What testing approach covers the 5 ACs, and what current state makes each test RED?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `setup/init.py` lines 1–310 | Codebase | 1.0 — the SUT |
| 2 | `seed/.owlbear/hooks/` listing | Codebase | 1.0 — current seed state |
| 3 | `seed/.vscode/settings.json` | Codebase | 1.0 — Windows-only profiles |
| 4 | `.owlbear/hooks/*.py` listing | Codebase | 0.9 — canonical 7-hook set |
| 5 | `tests/test_scaffold_mcp_memory_524.py` | Codebase | 0.7 — init.py test patterns |

## 3. Analysis

### Current State vs Target

| Aspect | Current | Target | RED? |
|--------|---------|--------|------|
| Seed hooks extension | 6 × `.ps1` | 7 × `.py` | Yes |
| Seed hook count | 6 (missing `deny-scratch-only-writes`) | 7 | Yes |
| Settings Windows profiles | `terminal.integrated.profiles.windows`, `terminal.integrated.defaultProfile.windows` | Removed | Yes |
| init.py `.ps1` in source | None (generic copy) | None | Pass — see note |

**AC4 note:** `init.py` has no `.ps1`-specific logic; it copies whatever extension exists in `seed/`. The meaningful RED assertion is that `seed/.owlbear/hooks/` contains `.ps1` files (which it does). A source-text check of `init.py` alone would PASS today, but a combined check (init.py source + seed directory) gives RED.

### Testing Approach Options

| Option | Description | Confidence |
|--------|-------------|------------|
| A — Real seed dir | Call `init()` with repo's real `seed/` dir, assert output | .85 |
| B — Synthetic fixtures | Build minimal seed dir in `tmp_path`, test init logic only | .60 |

**Recommendation: Option A** (confidence: .85). These are integration tests verifying the *actual seed state*. Using the real seed dir means tests naturally go RED because the seed has `.ps1` files, and go GREEN when the implementation task updates the seed. Synthetic fixtures would decouple from the defect being tested.

### Test Structure

| AC | Test | Assertion | Expected RED Reason |
|----|------|-----------|---------------------|
| 1 | `test_seeded_hooks_are_py_not_ps1` | No `.ps1` files in `target/.owlbear/hooks/` | Seed has 6 × `.ps1` |
| 1 | `test_seeded_hooks_have_py_extension` | All hook files end with `.py` | Seed has `.ps1` only |
| 2 | `test_all_seven_hooks_seeded` | Exactly 7 files matching canonical set | Seed has 6 |
| 3 | `test_settings_no_windows_terminal_profiles` | No `terminal.integrated.profiles.windows` key | Present in seed |
| 3 | `test_settings_no_windows_default_profile` | No `terminal.integrated.defaultProfile.windows` key | Present in seed |
| 4 | `test_init_py_source_no_ps1_refs` | `.ps1` not in init.py source text | PASS today — pair with seed check |
| 4 | `test_seed_hooks_dir_no_ps1_files` | No `.ps1` in `seed/.owlbear/hooks/` | 6 × `.ps1` present |

**Canonical 7 hooks:** `allow-stances-only`, `deny-code-writes`, `deny-scratch-only-writes`, `deny-src-writes`, `deny-writes`, `lint-changed`, `session-context`.

## 4. Recommendation

Use Option A — call `init()` with real `seed/` and assert output. 7 tests across 4 ACs, all RED except `test_init_py_source_no_ps1_refs` (which is already clean). Confidence: .85.

Challenge: FALLBACK — trivial T1 test task, no architectural decisions to challenge.

## 5. Follow-up Tasks

Task #899 itself advances to backlog for the test-writer. No additional tasks needed — the implementation tasks (#894–#896 dependencies) cover updating seed hooks, seed settings, and init.py.
