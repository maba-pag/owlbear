# Update setup/init.py for .py hooks

> **Owning task:** #900 — Update setup/init.py for .py hooks
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Task #900 (child of #890 macOS-compat) asks: does `setup/init.py` need code changes to seed `.py` hooks instead of `.ps1` hooks? Dependencies #898 (seed update) and #899 (init.py hook tests) are complete.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `setup/init.py` (full read, 295 lines) | Codebase | 1.0 |
| 2 | `seed/.owlbear/hooks/` (7 .py files) | Codebase | 1.0 |
| 3 | `tests/test_init_py_hooks.py` (task #899 tests) | Codebase | 0.9 |
| 4 | `tests/test_seed_py_hooks_and_clean_settings_898.py` | Codebase | 0.9 |
| 5 | `setup/setup-guide.md` (lines 25, 51-52) | Codebase | 0.8 |
| 6 | `.owlbear/briefs/draft-macos-compat/brief.md` | Codebase | 0.7 |

## 3. Analysis

### init.py seeding mechanism

`init()` walks `seed_dir.rglob("*")` and copies files generically — no hook-specific logic, no filename filtering by extension. The per-file dispatch handles only: `settings.json`, `mcp.json`, `.gitignore`, `owlbear-project.json`, and `_SKIP_IF_EXISTS_REL` items. All other files (including hooks) fall through to the generic copy path:

```
if src.suffix in (".json", ".yml"):
    # placeholder replacement + write
else:
    shutil.copy2(src, dest)
```

`.py` hook files hit the `shutil.copy2` branch — they are copied as-is with no transformation needed.

### .ps1 reference audit

| Location | `.ps1` references | Status |
|----------|-------------------|--------|
| `setup/init.py` source | **0** — `grep ".ps1" setup/init.py` returns nothing | Already clean |
| `seed/.owlbear/hooks/` | **0** .ps1 files, **7** .py files | Already clean (#898) |
| `seed/.vscode/settings.json` | **0** — no powershell/pwsh refs | Already clean (#898) |
| `setup/setup-guide.md` | **2** stale .ps1 hook names (lines 51-52) + `powershell` fence (line 25) | Needs update |
| `setup/sharing-guide.md` | **1** `powershell` code fence (line 30) | Needs update |

### Test verification

All 25 tests across `test_init_py_hooks.py` and `test_seed_py_hooks_and_clean_settings_898.py` pass. Key passing assertions:
- AC2: No .ps1 files in target after init()
- AC3: Exactly 7 .py hooks seeded
- AC5: No .ps1 files in seed/
- AC6: No .ps1 string in init.py source

## 4. Recommendation (confidence: 0.95)

**No code changes needed in `setup/init.py`.** The generic `rglob` + `shutil.copy2` mechanism already seeds `.py` hooks correctly because #898 replaced the seed files. All ACs for #900 are **already satisfied** at the code level.

The remaining `.ps1`/`powershell` references in `setup-guide.md` and `sharing-guide.md` are documentation issues covered by brief step 6 ("Update documentation") — a separate task scope.

Challenge: skipped — trivial finding (no recommendation among competing options; factual audit only).

**Tier: T1 — Autonomous.** No architecture change, no new capability, no user-facing behavior change. The code already works; documentation cleanup is the only follow-up.

## 5. Follow-up Tasks

- **Update setup-guide.md**: replace 2 stale .ps1 hook names and `powershell` code fence with cross-platform equivalents
- **Update sharing-guide.md**: replace `powershell` code fence with cross-platform shell example
