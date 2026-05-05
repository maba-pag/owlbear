# Memory Git Integration — RED Test Design

> **Owning task:** #1310 — P1-09: RED — Git integration tests
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1310 writes failing tests for a git integration layer in mcp-memory. The layer ensures: (a) `save_memory` never commits, (b) curation and review sessions each produce a single batch commit, (c) hard-deleted pending entries never enter git history, (d) soft-deleted entries are committed, and (e) commit messages follow project format.

The GREEN counterpart (#1311) implements the module these tests target.

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | mcp-memory engine | `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` | 1.0 |
| S2 | mcp-memory tools | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` | 1.0 |
| S3 | kanban engine git pattern | `serve/kanban/src/owlbear_kanban/engine.py` L305-328 | .90 |
| S4 | project commit format | `share/skills/r-project-standards/SKILL.md` §1 | .95 |
| S5 | recall_memory RED tests | `tests/test_recall_memory_1308.py` | .85 |
| S6 | GREEN task AC | `.owlbear/kanban/tasks/1311-*.md` | .95 |

## 3. Analysis

### 3A. Module Interface Design

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module path | `owlbear_mcp_memory.git` | New module; import fails → RED guaranteed |
| Function | `commit_batch(memory_dir, *, session_type)` | Single function covers both AC2 and AC3 |
| session_type | `Literal["curation", "review"]` | Discriminates commit message |
| Return | `str` (commit SHA, or `""` if nothing to commit) | Verifiable in tests |
| Git interface | `subprocess.run(["git", ...])` | Matches kanban pattern (S3), no deps |

### 3B. Staging Safety — Pending File Exclusion

The critical design constraint: `commit_batch` must NOT stage pending files.

| Scenario | File on disk? | Git state | commit_batch behavior |
|----------|--------------|-----------|----------------------|
| save_memory (pending) | Yes | untracked | SKIP — never staged |
| curate_memory (curated) | Yes | untracked/modified | STAGE |
| approve_memory (approved) | Yes | modified | STAGE |
| soft-delete (deleted state) | Yes | modified | STAGE |
| hard-delete (pending removed) | No | n/a | Nothing to do |

Implementation approach: `commit_batch` parses frontmatter of each `.md` file, stages only non-pending files via `git add <specific-files>`, then commits.

### 3C. Commit Message Format

Per S4: `type: description (#task-id, context)`. Memory batches have no task ID, so:

- Curation: `chore: memory curation batch (mcp-memory, curator)`
- Review: `chore: memory review batch (mcp-memory, reviewer)`

### 3D. Test Infrastructure

| Pattern | Approach |
|---------|----------|
| Git repo | `subprocess.run(["git", "init"], cwd=tmp_path)` per test |
| Seed entries | `MemoryEngine(memory_dir=tmp_path / "memory").write(entry)` |
| Assert commit count | `git rev-list --count HEAD` |
| Assert file in history | `git log --all --name-only --pretty=format:""` |
| Assert commit message | `git log -1 --pretty=format:%s` |
| Assert uncommitted | `git status --porcelain` shows `??` or `M` |
| RED guarantee | `from owlbear_mcp_memory.git import commit_batch` → ImportError |

### 3E. Test Matrix (7 tests mapping to 7 AC)

| Test | AC | Assertion |
|------|-----|-----------|
| `test_save_does_not_commit` | AC1 | After save_memory, `git log` has 0 commits beyond initial |
| `test_curation_batch_single_commit` | AC2 | After 3× curate + 1× delete + commit_batch("curation") → exactly 1 new commit |
| `test_review_batch_single_commit` | AC3 | After 2× approve + 1× curate + commit_batch("review") → exactly 1 new commit |
| `test_hard_deleted_never_in_history` | AC4 | Create pending → hard-delete → commit_batch → filename absent from all git log |
| `test_soft_deleted_in_batch_commit` | AC5 | Curated entry → soft-delete → commit_batch → file diff shows state=deleted |
| `test_commit_message_format` | AC6 | commit_batch → `git log -1 --pretty=%s` matches expected pattern |
| `test_all_fail_red` | AC7 | Module import fails (ImportError) — structural guarantee |

## 4. Recommendation (.92 confidence)

Proceed with test writing. Design is straightforward — single function, subprocess-based git, no external deps. The deferred-import pattern from S5 guarantees RED state.

Challenge: SKIPPED — info-only RED test design, no alternative approaches to evaluate. Single viable interface pattern exists.

## 5. Follow-up Tasks

No new tasks needed — #1311 (GREEN) already exists as the implementation counterpart.
