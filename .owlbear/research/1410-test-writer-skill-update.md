# Test-Writer Skill Update — Exact-Value Assertions, Structural Test Separation

> **Owning task:** #1410 — C2: Test-writer skill update — exact-value assertions, structural test separation, convention updates
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

Brief C2 (parent #1403) calls for three changes across 4 skill files (`w-tdd-red`, `h-python-conventions`, `w-tdd-green`, `w-test-curation`):

1. Default to exact-value assertions over pattern-matching assertions
2. Document structural test separation: task-scoped in root `tests/`, durable in `serve/*/tests/`
3. Expand test-writer mandate for consolidation-test tasks

**Question:** What specific edits are needed in each file, and are there conflicts with the current codebase state?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `w-tdd-red` SKILL.md (current) | Codebase | 1.0 — primary edit target |
| `h-python-conventions` SKILL.md (current) | Codebase | 1.0 — primary edit target |
| `w-tdd-green` SKILL.md (current) | Codebase | 1.0 — primary edit target |
| `w-test-curation` SKILL.md (current) | Codebase | 1.0 — primary edit target |
| `.owlbear/briefs/draft-pipeline-review-rethink/brief.md` | Brief | 1.0 — authoritative spec |
| `.github/copilot-instructions.md` | Codebase | 0.8 — project conventions (already documents both test locations) |
| `pyproject.toml` testpaths | Codebase | 0.9 — confirms `["tests", "serve"]` discovers both locations |
| Codebase file counts | Codebase | 0.9 — current reality: 125 task-scoped + 36 durable in root; 43 task + 29 durable in package-local |

## 3. Analysis

### 3.1 Exact-Value Assertions

**Gap:** `w-tdd-red` Step 4 says "Test the contract described in AC" but gives no guidance on assertion style. No preference for `assert result == 42` over `assert "foo" in result`.

**Change:** Add assertion-style guidance to Step 4: prefer exact-value assertions (`==`, exact exception types, exact return values) over pattern-matching (`in`, `>`, regex). Pattern-matching acceptable only when AC explicitly describes pattern-based behavior (e.g., "output contains X").

**Risk:** None. This is strictly additive guidance. Doesn't conflict with existing test patterns.

### 3.2 Structural Test Separation

**Current state per skill files:** All 4 skills reference only root `tests/test_{module}.py` for durable tests. Reality is split — 29 durable tests already live in `serve/*/tests/`.

**Current state per project docs:** `.github/copilot-instructions.md` already documents `serve/*/tests/` for "package-scoped test suites." `pyproject.toml` already discovers both locations.

| File | Current Reference | Required Change |
|------|------------------|-----------------|
| `w-tdd-red` Step 4 | `tests/test_{module}_{task_id}.py` | No change — task-scoped stays in root `tests/` |
| `w-tdd-red` (new) | N/A | Add consolidation-test section allowing `serve/*/tests/` writes |
| `h-python-conventions` Two-Tier Model | Tier locations unspecified | Specify: task-scoped → `tests/`, durable → `serve/{package}/tests/` |
| `w-tdd-green` Step 2 | `tests/test_{module}.py` | Update to `serve/{package}/tests/test_{module}.py` |
| `w-tdd-green` Step 6 | `tests/test_{module}.py` | Update to `serve/{package}/tests/test_{module}.py` |
| `w-test-curation` Steps 0-4 | All reference root `tests/` only | Update durable file operations to `serve/*/tests/`, keep task-test cleanup in root `tests/` |

**Risk:** 36 existing durable tests in root `tests/` are "legacy" under the new convention. Migration is E2 scope (out of scope for C2). Forward-looking only — new durable tests go to `serve/*/tests/`, existing ones stay until E2.

### 3.3 Consolidation-Test Mandate

**Current state:** `w-tdd-red` restricts test-writer to creating `tests/test_{module}_{task_id}.py` only. No path for writing durable package-local tests.

**Change:** Add a new step (or substep of Step 4) for consolidation-test tasks. When the task title matches "consolidation test: *" (created per D4 by planner), the test-writer:
- Creates/modifies durable tests in `serve/{package}/tests/test_{module}.py`
- Uses descriptive class names (not `TestFromAC_` — those are task-scoped)
- File naming follows durable pattern: `test_{module}.py` (no task ID suffix)

**Risk:** Low. The file-domain distinction is clean: normal tasks → root `tests/`, consolidation → `serve/*/tests/`.

### 3.4 Cross-File Consistency

All 4 files must use consistent terminology:

| Term | Definition |
|------|-----------|
| Task-scoped test | `tests/test_{module}_{task_id}.py` — transient, deleted at archival |
| Durable module test | `serve/{package}/tests/test_{module}.py` — permanent, test-curator managed |
| Consolidation-test task | Planner-created task (title: "consolidation test: {name}"), gives test-writer durable-write permission |

## 4. Recommendation

**Proceed as specified by brief C2.** All changes are additive skill-text edits with no codebase conflicts. Confidence: 0.92.

**Challenge:** Skipped — brief-directed implementation with no alternative options to evaluate. All changes flow directly from decisions D4 and the C2 spec.

**Minor concern:** `w-test-curation` Step 0 currently scans only root `tests/` for task-scoped files. After this change, task-scoped files still only live in root `tests/`, so the curator's cleanup path doesn't change. But the curator's mine-and-write path does — it writes durable tests to `serve/*/tests/` instead of root. The curator needs to know which package a module belongs to. The implementation should add a mapping note or heuristic (import path → package).

## 5. Follow-up Tasks

No new tasks needed beyond #1410 itself. All changes are within scope of the existing AC. The task can proceed through architect → test-writer → builder pipeline.
