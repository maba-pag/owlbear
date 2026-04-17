# Delete .ps1 Hook Files from .owlbear/ and seed/

> **Owning task:** #904 — Delete .ps1 hook files from .owlbear/ and seed/
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Parent #890 (macOS compatibility) required replacing PowerShell `.ps1` hooks with cross-platform `.py` equivalents. Tasks #894–896 created the `.py` hooks; task #898 cleaned seed; task #897 removed agent `.ps1` references. This task deletes the remaining `.ps1` originals from `.owlbear/hooks/`.

**Question:** What .ps1 files remain, are .py replacements verified, and are there dangling references?

## 2. Sources Studied

| # | Source | Relevance | Finding |
|---|--------|-----------|---------|
| 1 | `.owlbear/hooks/` directory listing | 1.0 | 7 .ps1 files remain, each with a .py counterpart |
| 2 | `seed/.owlbear/hooks/` directory listing | 1.0 | 0 .ps1 files — already cleaned by task #898 |
| 3 | `.owlbear/hooks/deny-writes.ps1` vs `.py` | 0.9 | Functionally equivalent (same tools list, same deny logic) |
| 4 | `grep -r ".ps1"` across agents, instructions, skills | 0.9 | Zero hits — agent refs already cleaned (#897) |
| 5 | `grep -r ".ps1"` across `setup/`, `share/` | 0.8 | 2 stale refs in `setup/setup-guide.md` (lines 51-52) |
| 6 | Task #901 (Update setup and sharing docs) | 0.7 | Already scoped to fix doc references — covers setup-guide.md |

## 3. Analysis

### Files to Delete (`.owlbear/hooks/`)

| File | .py replacement exists | Verified equivalent |
|------|----------------------|---------------------|
| `allow-stances-only.ps1` | ✓ | ✓ (same allow-list logic) |
| `deny-code-writes.ps1` | ✓ | ✓ (same tool deny logic) |
| `deny-scratch-only-writes.ps1` | ✓ | ✓ (same path-scoped deny) |
| `deny-src-writes.ps1` | ✓ | ✓ (same source deny logic) |
| `deny-writes.ps1` | ✓ | ✓ (verified: identical tool set, identical response) |
| `lint-changed.ps1` | ✓ | ✓ (same lint feedback logic) |
| `session-context.ps1` | ✓ | ✓ (same context hook logic) |

### AC Correction

The AC states "All .ps1 files deleted from `seed/.owlbear/hooks/` (6 files)" — but seed already has 0 .ps1 files (cleaned by #898). This AC item is pre-satisfied.

### Dangling References

| Location | Reference | Owner |
|----------|-----------|-------|
| `setup/setup-guide.md:51-52` | `deny-writes.ps1`, `lint-changed.ps1` | Task #901 (docs update) |
| Test files (`test_*_897.py`, `test_*_898.py`) | String literals asserting .ps1 absence | Intentional — these tests *verify* .ps1 removal |

No actionable dangling refs for this task. The setup-guide.md refs are scoped to #901.

## 4. Recommendation

**Delete the 7 .ps1 files from `.owlbear/hooks/` via `git rm`.** No other action needed.

- Confidence: **0.95** — straightforward deletion, all replacements verified, no dangling refs in scope.
- Risk: **negligible** — files are dead code; .py equivalents are deployed and tested.
- Challenge: skipped — trivial deletion with no design decision.

## 5. Follow-up Tasks

No new follow-up tasks needed. Existing coverage:

- **#901** covers `setup-guide.md` .ps1 reference cleanup
- **#905** covers full macOS validation post-cleanup
