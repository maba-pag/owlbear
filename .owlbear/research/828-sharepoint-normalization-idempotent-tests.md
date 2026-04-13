# Tests — SharePoint Normalization + Idempotent Output for Cleaner

> **Owning task:** #828 — Tests — SharePoint normalization + idempotent output for cleaner
> **Date:** 2026-04-12  **Status:** Complete

## 1. Context and Question

#828 is a RED-phase test task (parent #775, depends_on #783) for tests covering
scope unique to #756 not handled by #783: (1) SharePoint-specific boilerplate
removal, (2) content normalization, (3) idempotent output for hashing. This task
was created as follow-up item #3 from the #756 research. The GREEN partner is
#829. Key question: what test patterns will genuinely FAIL at RED, and how should
tests align with #829's binding AC (which corrected the original #828 AC)?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Current `cleaner.py` implementation | serve/browser/src/owlbear_browser/cleaner.py | 1.0 |
| 2 | #756 research (unique scope analysis) | .owlbear/research/756-html-markdown-cleaner-tests.md §3.2 | .95 |
| 3 | #829 research (GREEN partner patterns) | .owlbear/research/829-sharepoint-normalization-cleaner.md | 1.0 |
| 4 | #829 task body (binding AC from arch review) | kanban board | 1.0 |
| 5 | `compute_content_hash()` | serve/knowledge/src/owlbear_knowledge/status_store.py:39 | .90 |
| 6 | Existing tests `test_cleaner_756.py` | tests/test_cleaner_756.py | .95 |
| 7 | Existing tests `test_browser_content_775.py` | tests/test_browser_content_775.py | .95 |
| 8 | Fluent UI v8 class reference | github.com/Zerg00s/sp-modern-classes (via #829 research) | .80 |

## 3. Analysis

### 3.1 Existing Coverage vs #828 Scope

| Test file | What it covers | Overlap with #828 |
|-----------|----------------|-------------------|
| `test_cleaner_756.py` | Currently-implemented SP patterns (ms-header, ms-commandBar, SuiteNavWrapper), basic normalization, idempotency | Tests that PASS — no overlap with RED scope |
| `test_browser_content_775.py` (#783) | Extractor AC, strip_noise generic, html_to_markdown, trafilatura dep, clean() structure | Generic cleaner — no SharePoint-specific patterns |

**Finding:** Neither file tests the patterns #828 targets. No duplication risk.

### 3.2 RED-Phase Failure Verification

Current `cleaner.py` state mapped against #829 binding AC:

| Pattern | Current in cleaner.py? | Test will FAIL? |
|---------|----------------------|-----------------|
| `ms-Breadcrumb` class | NO | YES |
| `ms-Persona` class | NO | YES |
| `ms-LivePersona` class | NO | YES |
| `ms-DateTimeField` class | NO | YES |
| `SuiteNavPlaceHolder` id | NO (`SuiteNavWrapper` exists, different) | YES |
| `O365_NavHeader` id | NO | YES |
| `s4-ribbonrow` id | NO | YES |
| Zero-width char removal (U+200B/200C/200D/FEFF) | NO | YES |
| `\r` stripping | NO | YES |

All 9 pattern categories will produce genuinely failing tests. ✓

### 3.3 AC Correction: Function Attribution

The #828 AC says "Tests for whitespace normalization in `html_to_markdown()` output."
The #829 architect identified this as a HIGH-severity defect: normalization lives in
`_normalize_content()` called by `clean()`, not in `html_to_markdown()`. Tests should
target `clean()` or `_normalize_content()` directly.

The test-writer must follow #829's binding AC, not the original #828 AC line:
- **Original:** "html_to_markdown() output has normalized whitespace"
- **Corrected:** `_normalize_content()` strips `\r` and zero-width Unicode; `clean()` calls it

### 3.4 Idempotency Test Design

Basic idempotency (`clean(html) == clean(html)`) already passes — functions are
deterministic. The meaningful RED test is: HTML containing zero-width chars → `clean()`
strips them from output → hash is stable. This will FAIL because `_normalize_content()`
does not currently strip zero-width chars.

Both paths need coverage:
- `clean()` path (strip_noise → html_to_markdown → _normalize_content) — primary
- `extract_content()` through cleaner fallback (when trafilatura returns None)

### 3.5 Test Structure Recommendation

| Test class | Tests | Targets |
|------------|-------|---------|
| `TestFromAC_SharePointNoiseRemoval` | 5–7 tests | `strip_noise()` with SP-specific classes/IDs |
| `TestFromAC_ContentNormalization828` | 3–4 tests | `clean()` / `_normalize_content()` for `\r`, zero-width |
| `TestFromAC_IdempotentOutput828` | 3–4 tests | `clean()` + `extract_content()` hash stability with zero-width |

Total: ~12–15 tests in `tests/test_browser_content_775.py`, appended as new classes.

### 3.6 Test Fixture Patterns

SharePoint fixtures should use realistic class/id patterns:
- Breadcrumb: `<div class="ms-Breadcrumb">Home > Sites > Team</div>`
- Persona: `<div class="ms-Persona">John Doe avatar</div>`
- Timestamps: `<div class="ms-DateTimeField">Modified: April 10, 2026</div>`
- Suite nav: `<div id="SuiteNavPlaceHolder">O365 suite bar</div>`
- Zero-width: `<p>Content\u200bwith\u200czero\u200dwidth\ufeffchars</p>`

## 4. Recommendation (.88 confidence)

**Validation pass confirms: all findings from #756 and #829 research hold. No new
research needed — proceed to backlog for test-writing.**

Test-writer guidance:
1. Follow #829's binding AC for exact patterns (not original #828 AC)
2. Place tests in `tests/test_browser_content_775.py` as new test classes
3. Target `strip_noise()` for SP patterns, `clean()` for normalization/idempotency
4. Use `_normalize_content()` directly for zero-width/`\r` tests
5. Verify all tests fail by running against current cleaner.py

Tier: **T1 Autonomous** — test scaffolding, no new capability.

Challenge: FALLBACK — validation pass of existing research, no new recommendation
requiring challenge. Self-challenge: checked whether `test_cleaner_756.py` already
covers these patterns — it does not.

## 5. Follow-up Tasks

None. #828 advances to backlog. GREEN partner #829 already exists at `todo`.
