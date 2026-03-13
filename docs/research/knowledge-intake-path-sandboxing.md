# Path Sandboxing for Knowledge Intake

> **Owning task:** #497 — Add path sandboxing to knowledge intake
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

SEC-11 from the security audit: `intake.read_file()` reads any file path without
sandboxing. An LLM-directed ingestion of `/etc/passwd` or `~/.ssh/id_rsa` would
silently ingest sensitive content into the knowledge base.

**Question:** Where should the sandbox check go, and should we extract a shared
utility to eliminate the 3x copy-pasted `_safe_path` pattern?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Python pathlib docs | https://docs.python.org/3/library/pathlib.html | `.resolve()` + `.is_relative_to()` — canonical pattern (1.0) |
| 2 | OWASP Path Traversal | https://owasp.org/www-community/attacks/Path_Traversal | Threat model: `../`, null bytes, abs paths (0.9) |
| 3 | OwlBear `FileToolset._safe_path` | `src/owlbear/tools/filesystem.py` L59-76 | Existing internal pattern — null byte + resolve + is_relative_to (1.0) |
| 4 | OwlBear `KnowledgeToolset._safe_path` | `src/owlbear/tools/knowledge.py` L88-105 | Identical copy of #3 (1.0) |
| 5 | OwlBear `TerminalToolset` inline check | `src/owlbear/tools/terminal.py` L172-184 | Same logic inlined (0.9) |

## 3. Analysis

### 3.1 Threat Surface

| Entry point | Sandboxed? | Risk |
|---|---|---|
| `KnowledgeToolset._ingest_document(doc_type="file")` | Yes (calls `_safe_path` before pipeline) | None |
| `IngestPipeline.ingest(path)` called directly | **No** | Any caller bypassing toolset |
| `RefreshOrchestrator._handle_file_glob` | **No** — `base_dir` from config, glob unrestricted | Medium — config-driven but unsandboxed |
| `RefreshOrchestrator._ingest_items` | **No** — passes items straight to pipeline | Medium |
| `intake.read_file(path)` | **No** — reads any path on disk | **High** — deepest layer, last chance |

### 3.2 Where to Add the Check

| Option | Location | Pros | Cons | Confidence |
|---|---|---|---|---|
| A. `intake.read_file()` only | Deepest layer | Defense-in-depth; catches all callers | Needs workspace root param; changes function signature | .60 |
| B. `IngestPipeline.ingest()` only | Pipeline level | Single chokepoint for all ingest | Doesn't protect direct `intake.read_file()` calls | .50 |
| C. Both intake + pipeline | Two layers | Maximum coverage | Two checks on same path (marginal cost) | .75 |
| **D. intake.read_file() + RefreshOrchestrator** | Intake + glob gate | Covers the two actual unsandboxed paths; minimal API change | — | **.85** |

Option D is recommended. The `_handle_file_glob` also needs its own validation
because `base_dir` from config can point anywhere.

### 3.3 Shared Utility vs Inline Check (DRY)

The `_safe_path` pattern is copy-pasted in 3 places (FileToolset, KnowledgeToolset,
TerminalToolset). All use the identical 8-line pattern:

```
null-byte check → (root / user_path).resolve() → is_relative_to(root) → PermissionError
```

| Option | Pros | Cons | Confidence |
|---|---|---|---|
| A. Keep inline copies | No new module; zero coupling | DRY violation (3→4 copies) | .30 |
| **B. Extract `sandbox_path()` to `owlbear.core.paths`** | Single source of truth; all 4 callsites use it | One new module (~15 LOC) | **.85** |
| C. Mixin or base class | OOP purity | Over-engineering for a pure function | .20 |

**Recommendation (.85):** Extract a standalone `sandbox_path(root, user_path) -> Path`
function into `owlbear.core.paths`. Replace the 3 existing copies + use in intake.

### 3.4 Signature Change for `intake.read_file()`

Current: `async def read_file(path: str | Path) -> IntakeResult`

Proposed: `async def read_file(path: str | Path, *, workspace_root: Path) -> IntakeResult`

The `workspace_root` kwarg enables sandboxing at the deepest layer. Callers that
already have a workspace root (IngestPipeline, RefreshOrchestrator) pass it
through. The check uses the shared `sandbox_path()` utility.

### 3.5 RefreshOrchestrator Glob Fix

`_handle_file_glob` should validate that `base_dir` resolves within workspace root
before globbing, and each resolved path should be checked too. Use `sandbox_path()`
for both.

## 4. Recommendation (.85 confidence)

1. **Create `owlbear.core.paths.sandbox_path(root, user_path)`** — 15 LOC, tested.
2. **Add `workspace_root` param to `intake.read_file()`** — call `sandbox_path` inside.
3. **Add sandbox to `RefreshOrchestrator._handle_file_glob`** — validate base_dir + paths.
4. **Replace 3 existing `_safe_path` copies** with calls to `sandbox_path()`.
5. **Tests:** traversal, null-byte, absolute outside, valid inside — for shared util + intake.

Risk: `intake.read_file()` signature changes. Mitigation: `workspace_root` is
keyword-only, so existing positional calls won't break if we add a default of
`None` that skips the check (backwards compat during migration). However, per
project principles (no backwards compatibility), making it required is cleaner.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Extract shared sandbox_path utility to owlbear.core.paths" --priority needed --status backlog --tags "security,refactor,phase-5" --body "DRY: Extract the null-byte + resolve + is_relative_to pattern from FileToolset, KnowledgeToolset, TerminalToolset into a standalone sandbox_path(root, user_path) -> Path function. Replace all 3 existing copies. ~15 LOC + tests. See docs/research/knowledge-intake-path-sandboxing.md"

kanban\kanban-md.exe create "Add workspace_root sandboxing to intake.read_file()" --priority needed --status backlog --tags "security,knowledge,phase-5" --depends-on 497 --body "SEC-11 fix: Add workspace_root keyword arg to intake.read_file(). Call sandbox_path() inside to reject paths outside workspace. PermissionError for traversal. Tests: ../escape, /etc/passwd, null byte, valid path. See docs/research/knowledge-intake-path-sandboxing.md"

kanban\kanban-md.exe create "Add path sandboxing to RefreshOrchestrator._handle_file_glob" --priority needed --status backlog --tags "security,knowledge,phase-5" --body "SEC-11 related: _handle_file_glob accepts base_dir from config without validation. Validate base_dir is within workspace root. Also validate each glob result. Use shared sandbox_path(). See docs/research/knowledge-intake-path-sandboxing.md"
```
