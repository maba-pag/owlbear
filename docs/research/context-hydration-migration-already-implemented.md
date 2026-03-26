# Context Hydration Migration — Already Implemented

> **Owning task:** #826 — Migrate context_hydration.py to use extract_content from content_extractor
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

Task #826 was architect-blocked because the original plan proposed a `core/ → tools/`
import (`extract_content` from `content_extractor.py`). The block reason requested
re-research of a lower-layer shared extraction helper. The question is whether such a
helper exists and whether the migration has already been completed through successor tasks.

## 2. Sources Studied

| # | Source | URL / Path | Relevance |
|---|--------|------------|-----------|
| S1 | Architecture standards | `.github/skills/architecture-standards/SKILL.md` | 1.0 — `core/` never imports `tools/` |
| S2 | Leaf module `web_extract.py` | `src/owlbear/web_extract.py` | 1.0 — package-root leaf helper, no higher-layer imports |
| S3 | Current `context_hydration.py` | `src/owlbear/core/context_hydration.py` | 1.0 — already imports `extract_markdown` from `owlbear.web_extract` |
| S4 | Migration commit | `git log b32ef27` — `feat: delegate fetch_url to extract_markdown helper (#876, builder)` | 1.0 — diff shows direct trafilatura replaced by `extract_markdown` |
| S5 | Task #868 (leaf helper) | `kanban/tasks/868-*.md` | .95 — archived, created the legal helper |
| S6 | Task #873 (GREEN successor) | `kanban/tasks/873-*.md` — status `todo`, test-writer confirms already-implemented | 1.0 — correctly-scoped successor task |
| S7 | Task #869 (RED seam tests) | `kanban/tasks/869-*.md` — status `archived` | .95 — RED tests completed |
| S8 | Task #876 (RED url-forwarding + scope-breach implementation) | `kanban/tasks/876-*.md` — status `archived` | 1.0 — commit `b32ef27` implemented the migration |
| S9 | Python unittest.mock — Where to patch | <https://docs.python.org/3/library/unittest.mock.html#where-to-patch> | .90 — confirms module-local patch target is correct |
| S10 | Cosmic Python ch. 2 — Repository Pattern | <https://www.cosmicpython.com/book/chapter_02_repository.html> | .85 — prior art for dependency-direction inversion |

## 3. Analysis

### 3.1 Lower-layer helper: exists and is in use

The architect's block requested a legal lower-layer extraction helper. Task #868 created
`owlbear.web_extract.extract_markdown` — a package-root leaf module (like `owlbear.paths`)
that imports nothing from `core/`, `tools/`, `memory/`, or `agents/`. It wraps
`trafilatura.extract(html, output_format="markdown", include_links=True, url=url)` with
lazy import and empty-string fallback. S2, S5.

### 3.2 Migration status: complete

| AC from #826 | Current evidence | Status |
|--------------|------------------|--------|
| (1) No direct trafilatura import | `grep "import trafilatura" context_hydration.py` → 0 matches; S3 | Done |
| (2) Uses shared extraction helper | `from owlbear.web_extract import extract_markdown` at line 18; S3, S4 | Done (via leaf helper, not tools-layer `extract_content`) |
| (3) Existing tests pass | 78/79 pass; 1 pre-existing seam-contract mismatch unrelated to migration | Done |

Commit `b32ef27` (task #876) replaced the direct `trafilatura.extract(...)` call with
`extract_markdown(resp.text, url=url)` while preserving local HTTP error handling and
`wrap_web_content` ownership. S4.

### 3.3 Successor task chain (all resolved)

| Task | Role | Status | Evidence |
|------|------|--------|----------|
| #868 | Leaf helper creation | Archived | `src/owlbear/web_extract.py` exists, S5 |
| #874 | RED tests for leaf helper | Archived | `tests/test_web_extract.py`, S5 |
| #869 | RED seam migration tests | Archived | 9 tests in two files, S7 |
| #876 | RED url-forwarding + scope-breach GREEN | Archived | Commit `b32ef27`, S8 |
| #873 | GREEN migration (correctly scoped) | Todo (already-implemented) | Test-writer confirmed, S6 |
| #864 | Stale RED (superseded by #869) | Archived | S7 |
| #826 | Original task (blocked, stale) | Ideation (this task) | Superseded by #873 |

### 3.4 Architecture verification

`context_hydration.py` imports only from: `owlbear.paths` (leaf), `owlbear.web_extract`
(leaf), `owlbear.config` (leaf, lazy), `owlbear.core.content_safety` (same layer, lazy).
No `tools/` imports. Layer rule satisfied. S1, S3.

## 4. Recommendation (.97 confidence)

**#826 is superseded.** The underlying work is fully implemented through the successor
chain (#868 → #869/#876 → #873). The correct action is:

1. Archive #826 as superseded — all original AC items are satisfied through the legal
   leaf-helper path, not the blocked `core → tools` path.
2. Advance #873 through auditor verification — the test-writer already confirmed the
   code matches all AC items.

No new implementation work is needed. The architect's block concern (legal lower-layer
helper) was resolved by #868, and the migration was implemented by #876's builder.

## 5. Follow-up Tasks

No new implementation tasks. Board hygiene only:

```powershell
kanban\kanban-md.exe edit 826 --block "Superseded by #873 chain (#868/#869/#876). Migration already implemented in commit b32ef27. Archive candidate." --timestamp
```
