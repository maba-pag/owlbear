---
id: 1027
title: 'P2-03: setup/*.md sweep'
status: archived
priority: medium
created: 2026-04-19 23:52:56.667184+00:00
updated: 2026-04-20 04:13:30.722499+00:00
tags:
- phase-2
- docs-currency
- docs-sweep
parent: 1016
depends_on:
- 1024
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] `setup/setup-guide.md` verified against actual `setup/init.py` behavior — all paths, commands, prerequisites, and steps match reality
- [ ] `setup/sharing-guide.md` verified against actual sharing workflow — no stale references
- [ ] Both docs conform to `r-doc-standards` structural requirements
- [ ] Doc-index regenerated after changes

## Files

- Modifies: `setup/setup-guide.md`, `setup/sharing-guide.md`

## Notes

These are consumer-facing setup docs — accuracy is critical for downstream adoption. Pure documentation — no TDD pairing.
[[2026-04-20]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two related setup docs in one sweep — single domain |
| Interface clarity | PASS (refined) | AC2 broadened below to cover false claims, not just stale refs |
| Dependency correctness | PASS | #1024 (doc-writer v2) archived/done |
| Module layering | N/A | Pure documentation task |
| TDD compliance | PASS | Non-impl task; requires `docs` pass-through tag (see below) |
| KISS/YAGNI | PASS | Minimal scope — two files, verify + fix |
| Premise challenge | PASS | Consumer-facing docs must match reality |
| Pattern consistency | PASS | Follows r-doc-standards STR-11/12/13 |
| Security surface | PASS | No security boundary changes |
| Single domain | PASS | Docs domain only |

### Challenge Results

- Challenger: **reconsider** (confidence 0.45)
- Architect response: **accepted in part** — challenger correctly identified 5 concrete accuracy issues and AC2 vagueness. Refinements incorporated below. Verdict upgraded to APPROVE with guidance notes.

### AC Refinements (binding for executor)

**AC2 broadened:** Interpret "verified against actual sharing workflow — no stale references" as: _"verified against actual `setup/init.py` behavior and sharing workflow — no false, stale, or outdated claims about init.py behavior, file creation, or idempotency semantics."_

### Known Discrepancies (executor guidance)

The challenger identified these concrete issues the doc-writer must address:

1. **mcp.json idempotency (critical):** `setup-guide.md` line ~57 says "Skipped if file already exists" and line ~139 says "mcp.json is not updated on subsequent init.py runs." FALSE — `init.py` `_write_mcp()` reads, merges servers, and rewrites. Correct to "Merged" (same as settings.json).
2. **MCP server count:** `setup-guide.md` says "6 MCP servers (GitHub remote + 4 owlbear stdio + ddgs web search)." `create_mcp_config()` docstring says 5 (kanban, knowledge, memory, ddgs, markitdown). Executor must open `seed/.vscode/mcp.json` to resolve actual count.
3. **False copilot-instructions claim (critical):** `sharing-guide.md` states `.github/copilot-instructions.md` "is already created by init.py" — no such template exists in seed, and init.py has no reference to it. Remove or correct.
4. **Undocumented seed files:** "What Setup Creates" table omits: `.editorconfig`, `.gitattributes`, `.markdownlint-cli2.jsonc`, `.markdownlint.json`, `.markdownlintignore`, `.yamllint.yml`, `store/knowledge/.gitkeep`, `store/memory/.gitkeep`. Either add them or document the exclusion rationale.
5. **`.owlbear/knowledge/.gitkeep` idempotency:** Labeled "Created if missing" but actually "Always written" (falls through to `shutil.copy2`).
6. **`--type` CLI flag:** Module docstring mentions `--type TYPE` but CLI only implements `--name`. Docstring or setup docs should be corrected.

### Pipeline Tag

**ACTION REQUIRED:** Add `docs` pass-through tag before pipeline dispatch. Current tags (`phase-2`, `docs-currency`, `docs-sweep`) contain no pass-through tag. Without `docs`, the test-writer will attempt TDD pairing on a non-implementation task.

### Verdict: APPROVE (with refinements)
### Action Taken: Advanced to todo. AC2 interpretation broadened. 6 known discrepancies documented as executor guidance. `docs` tag addition flagged.
[[2026-04-20]]
## Test-Writer Notes
- Non-impl pass-through: AC references only `.md` files for modification (`setup/setup-guide.md`, `setup/sharing-guide.md`).
- Body explicitly states "Pure documentation — no TDD pairing."
- Step 2a scan: zero Python implementation keywords (`implement`, `function`, `class`, `src/`, `.py`, `endpoint`) in AC lines.
- `setup/init.py` appears only as a reference source (verify against), not a modification target.
- No testable Python interfaces exist. Passing through to builder.
[[2026-04-20]]
## Builder Notes

### Files changed
- `setup/setup-guide.md` — 6 fixes applied
- `setup/sharing-guide.md` — 1 fix applied
- `setup/init.py` — 1 fix applied (module docstring)

### Fixes applied
1. **mcp.json server count** (setup-guide.md table): "6 MCP servers (GitHub remote + 4 owlbear stdio + ddgs)" → "5 MCP servers (3 owlbear stdio + ddgs web search + markitdown)" — verified against `seed/.vscode/mcp.json`
2. **mcp.json idempotency** (table): "Skipped if file already exists" → "Merged (owlbear servers as defaults; your existing servers are preserved)" — confirmed by `_write_mcp()` in init.py which merges servers
3. **"mcp.json not updated" note**: Fixed false claim in "Adding project-specific MCP servers" section — now accurately describes merge behavior
4. **Missing seed files** (table): Added 10 previously undocumented files: `.owlbear/kanban/tasks/.gitkeep`, `store/knowledge/.gitkeep`, `store/memory/.gitkeep`, `.editorconfig`, `.gitattributes`, `.gitignore`, `.markdownlint-cli2.jsonc`, `.markdownlint.json`, `.markdownlintignore`, `.yamllint.yml` with accurate idempotency per `_SKIP_IF_EXISTS_REL` and `shutil.copy2` code paths
5. **`.owlbear/knowledge/.gitkeep` idempotency**: "Created if missing" → "Always written" — confirmed not in `_SKIP_IF_EXISTS_REL`, falls to `shutil.copy2`
6. **False copilot-instructions claim** (sharing-guide.md): Removed "and is already created by `init.py`" — no such template in seed, no init.py reference
7. **`--type TYPE` in docstring** (init.py): Removed non-existent CLI flag from module docstring — argparse only implements `--name`

### Tests
Non-implementation pass-through — no test suite to run.

### Doc-index
Regenerated via `uv run doc-index` (no-op: mtime check skipped write, confirming existing index is current).

### Commit
`9d9ef5f8` — `docs: verify and fix setup-guide.md and sharing-guide.md accuracy (#1027)`
[[2026-04-20]]
## Review Evidence

### Test Results
- pytest: N/A — non-implementation pass-through (documented by test-writer; no `TestFromAC_*` classes exist)

### Lint: N/A — no Python source modules changed (init.py docstring edit is a comment, not logic)

### Coverage: N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 (setup-guide.md vs init.py) | None — non-impl pass-through | N/A | COVERED (manual evidence) |
| AC2 (sharing-guide.md no stale claims) | None — non-impl pass-through | N/A | COVERED (manual evidence) |
| AC3 (r-doc-standards) | None — non-impl pass-through | N/A | COVERED (manual evidence) |
| AC4 (doc-index regenerated) | None | N/A | COVERED (builder ran uv run doc-index; no-op confirms existing index current) |

#### Security Review
- No OWASP concerns. Documentation files and a one-line docstring removal — no executable attack surface.

#### Test Integrity
- No `TestFromAC_*` classes exist. Skip.

#### Test Quality
- N/A — non-implementation task.

#### Data Safety
- No data safety issues. Documentation only.

#### Implementation-Aware Gaps
- No implementation paths to test. init.py change is a docstring removal (non-logic).

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- **Duplicate word introduced by edit** (sharing-guide.md, Team Conventions → Project-specific instructions): "...restricted tools). This\nThis file takes priority over the owlbear shared instructions...". The builder removed ", and is already created by `init.py`" from the sentence but left a dangling "This " fragment, producing "This\nThis file...". Cosmetic defect; does not affect accuracy.

### AC Compliance

**AC1 — setup/setup-guide.md vs init.py**

Each of the 6 known discrepancies verified against source:

| Fix | Verification | Status |
|-----|-------------|--------|
| mcp.json server count → "5 MCP servers (3 owlbear stdio + ddgs web search + markitdown)" | `seed/.vscode/mcp.json` lines 12, 24, 36, 39, 48 — exactly 5 server entries (kanban, knowledge, memory, ddgs, markitdown) | PASS |
| mcp.json idempotency → "Merged (owlbear servers as defaults; your existing servers are preserved)" | `init.py` `_write_mcp()`: reads existing, does `{**owlbear_servers, **user_servers}`, rewrites | PASS |
| mcp.json note in customization section → now describes merge behavior | setup-guide.md: "Note: mcp.json is merged on subsequent init.py runs..." | PASS |
| Missing seed files added to table (10 entries) | Cross-checked all 22 active seed files (after `_SKIP_NAMES` excludes `scratch-pad.txt`) against table — all present | PASS |
| `.owlbear/knowledge/.gitkeep` idempotency → "Always written" | Not in `_SKIP_IF_EXISTS_REL`, not `.json`/`.yml` → falls to `shutil.copy2` | PASS |
| All idempotency claims for builder-added rows | `.editorconfig`, `.gitattributes`, `.markdownlint-cli2.jsonc`, `.markdownlint.json`, `.markdownlintignore` in `_SKIP_IF_EXISTS_REL` → "Skipped if file already exists" ✓; `.yamllint.yml` has `.yml` extension → template write path → "Always written" ✓; `.owlbear/kanban/tasks/.gitkeep`, `store/*.gitkeep` → `shutil.copy2` → "Always written" ✓; `.gitignore` → `_write_gitignore()` → "Appended if owlbear marker absent; idempotent once present" ✓ | PASS |

**AC1 Status: PASS**

**AC2 — sharing-guide.md no false claims (broadened AC)**

| Fix | Verification | Status |
|-----|-------------|--------|
| False "already created by init.py" claim removed | sharing-guide.md table row: `.github/copilot-instructions.md` — "No — per-project (override layer)"; prose no longer contains "already created by init.py" | PASS |
| mcp.json merge behavior documented | sharing-guide.md "Adding project-specific MCP servers" note: "mcp.json is merged on subsequent init.py runs" | PASS |

**AC2 Status: PASS**

**AC3 — r-doc-standards compliance**

| Rule | Evidence | Status |
|------|----------|--------|
| STR-11 (Prerequisites, numbered steps, expected outcome, troubleshooting) | setup-guide.md: Prerequisites table ✓; numbered Quick Start steps ✓; "Verify It Works" section ✓; Troubleshooting table ✓ | PASS |
| STR-12 (No assumed OwlBear internals knowledge) | Both docs are consumer-first; no internal jargon without explanation | PASS |
| STR-13 (In sync with init.py) | All discrepancies corrected and verified against init.py source | PASS |
| STR-11 (sharing-guide.md) | Numbered steps ✓; Troubleshooting table ✓; Platform Notes ✓ | PASS |

**AC3 Status: PASS**

**AC4 — Doc-index regenerated**

Builder ran `uv run doc-index`; tool reported no-op (mtime check found index current). Cannot independently execute without a terminal run, but builder's description of the no-op is consistent with the tool's conditional-regen logic in `owlbear_tools.doc_index.should_regenerate()`.

**AC4 Status: PASS (builder-reported; no independent execution)**

### Confidence: .95
### Verdict: PASS

Minor deduction (-.02): builder-introduced duplicate word in sharing-guide.md (Pass 2); minor deduction (-.03): AC4 doc-index not independently verified. Net: .95 → above .90 threshold.
[[2026-04-20]]
## Docs Gate

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|---------|
| 1 | Behavior/API → copilot-instructions.md | No | N/A | Task changes only setup/*.md docs and init.py module docstring; copilot-instructions.md has no section on init.py behavior or MCP server counts |
| 2 | Module docstrings | Yes | PASS | setup/init.py module docstring: removed non-existent `--type TYPE` flag (builder fix). Verified remaining docstring matches argparse — only `--name NAME` documented |
| 3 | External attribution | No | N/A | Pure documentation sweep — no external patterns cited |
| 4 | CLI changes | No | N/A | Docstring correction removed a false claim; no CLI behavior changed; README.md does not reference `--type` |
| 5 | Research doc | No | N/A | No `.owlbear/research/*.md` linked from task body |
| 6 | Cosmetic defect (reviewer Pass 2) | Yes | FIXED | Duplicate "This" in sharing-guide.md §Team Conventions → Project-specific instructions; fixed and committed `14903267` |

**Files updated:** `setup/sharing-guide.md` (duplicate-word fix)
**Scratch files:** None found at `.owlbear/scratch/1027-*`
**Doc-index:** `uv run doc-index` — no-op, index current
**Commits:** `14903267` — `docs: fix duplicate word in sharing-guide.md (#1027, doc-writer)`
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: setup-guide.md vs init.py | Spot-checked: MCP count "5 servers" matches seed/.vscode/mcp.json (5 entries at L3/15/27/39/48); mcp.json idempotency says "Merged"; .owlbear/knowledge/.gitkeep says "Always written"; 10 missing seed files added to table. Reviewer verified all 6 discrepancy fixes with source references. | PASS |
| AC2: sharing-guide.md no stale refs | False copilot-instructions claim removed (L83 table + L105 prose). Duplicate "This\nThis" fixed by doc-writer commit 14903267. No remaining false claims. | PASS |
| AC3: r-doc-standards compliance | Reviewer verified STR-11/12/13 compliance (prerequisites, numbered steps, expected outcome, troubleshooting, consumer-first language, init.py sync). Trusted — detailed evidence. | PASS |
| AC4: doc-index regenerated | Builder ran `uv run doc-index` — no-op (mtime check confirms index current). Consistent with conditional-regen logic in owlbear_tools.doc_index. | PASS |

### Test Results
- pytest: 797 passed, 10 failed, 4 skipped — all 10 failures outside task scope (diagram #1033, mcp-knowledge schema, doc-index diagram refs)
- ruff: clean

### Architect Quality: 4/5
Strong AC after challenger refinement. AC2 broadened from "no stale references" to cover false claims. 6 concrete discrepancies documented as executor guidance — excellent builder onboarding. Minor: original AC2 was vague before challenger caught it.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 have specific evidence) → no deduction
- Lint violations: none → no deduction
- AC quality ≤ 3: no (4/5) → no deduction
- Missing reviewer evidence: no (detailed, PASS) → no deduction
- In-scope test failures: 0 → no deduction

### Confidence: 1.00
### Action: archive