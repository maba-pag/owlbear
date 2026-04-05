# Re-exports for Empty `__init__.py` Files

> **Owning task:** #549 — Add re-exports to empty `__init__.py` files
> **Date:** 2026-03-15  **Status:** Complete

## 1. Context and Question

INT-10 in `docs/integration-audit.md` identified 7 packages with empty or docstring-only `__init__.py` files:
`auth`, `planning`, `projects`, `providers`, `safety`, `tools`, `tools/browser`. No public API surface is defined, forcing consumers to use deep imports like `from owlbear.safety.policy import ApprovalPolicy`.

**Question:** Which types should each package re-export, and what pattern should we follow?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Python docs — Regular packages | <https://docs.python.org/3/reference/import.html#regular-packages> | .90 — `__init__.py` executes on import; `from .foo import Bar` binds both submodule and name |
| PydanticAI `__init__.py` | <https://github.com/pydantic/pydantic-ai> (main `__init__.py`) | .95 — Direct prior art. Imports + `__all__` tuple. Our codebase already follows this in `core/`, `memory/`, `channels/` |
| OwlBear `core/__init__.py` | Local: `src/owlbear/core/__init__.py` | 1.0 — Internal prior art. 15 re-exports with `__all__`, grouped by source module |
| OwlBear `memory/knowledge/__init__.py` | Local: `src/owlbear/memory/knowledge/__init__.py` | .85 — Counter-example: 35+ exports (INT-11 calls this too many) |

## 3. Analysis

### 3.1 Pattern comparison

| Approach | Pros | Cons | KISS/YAGNI |
|----------|------|------|------------|
| **Eager `from .mod import X` + `__all__`** | Discoverable, IDE autocomplete, type-checker friendly | Loads submodules on package import | KISS ✓ — matches existing `core/__init__.py` |
| **Lazy `__getattr__`** | Deferred loading, zero cost until accessed | Complex, breaks IDE completion, un-Pythonic | YAGNI — no hot-path perf concern here |
| **Stay empty, use deep imports** | Zero change risk | No API surface, verbose imports, no discoverability | ✗ — audit identified this as a problem |

**Recommendation (.90 confidence):** Eager re-exports with `__all__`, matching `core/__init__.py` pattern. This is what PydanticAI does and what we already do for `core`, `memory`, `channels`, `voice`, `skills`.

### 3.2 Per-package export inventory

Selection criteria: only types/functions used by ≥2 consumers OR that form the package's primary interface.

| Package | Proposed exports | Count | Rationale |
|---------|-----------------|-------|-----------|
| `auth` | `request_device_code`, `poll_for_access_token`, `exchange_for_copilot_token`, `load_or_refresh_token`, `save_token`, `load_token`, `derive_base_url` | 7 | Single module; all public functions used by CLI + providers |
| `planning` | `ProjectDefinition`, `Requirement`, `ProjectDefinitionExtractor`, `project_definition_to_markdown` | 4 | Models + extractor + formatter = full public surface |
| `projects` | `Project`, `ProjectStore`, `ProjectToolset`, `ProjectWorkspace` | 4 | One class per module; all used by bootstrap+CLI |
| `providers` | `create_copilot_client`, `create_copilot_model`, `get_premium_requests` | 3 | Public factory functions; skip internal validators |
| `safety` | `ApprovalGateToolset`, `ApprovalPolicy`, `ApprovalRule`, `ApprovalSession` | 4 | Policy model + gate toolset; skip `GrantRecord` (internal) |
| `tools` | `AskUserToolset`, `FileToolset`, `GitLocalToolset`, `GitHubToolset`, `KanbanToolset`, `TerminalToolset`, `HookedToolset`, `MCPServerRegistry`, `find_toolset`, `unwrap` | 10 | All toolset classes + key utilities; skip web/knowledge (optional extras) |
| `tools/browser` | `BrowserToolset`, `BrowserConfig`, `BrowserManager`, `URLSafetyGuard`, `BlockedURLError`, `WebCrawler`, `CrawlConfig` | 7 | Core browser types; skip internal extractors/utils |

### 3.3 Risk assessment

- **Import overhead:** Minimal. These packages are already loaded during bootstrap. No heavy deps (BGE-M3 etc.) in the selected exports.
- **Circular imports:** Low risk. The packages are leaf-ish in the dependency graph. `tools` is the riskiest — verify with test.
- **Breakage:** None. Adding re-exports is additive. Existing deep imports continue to work.

## 4. Recommendation (.90 confidence)

Apply eager re-exports with `__all__` to all 7 packages, following `core/__init__.py` as template. Keep export counts conservative (3–10 per package). Skip optional/heavy dependencies (`WebSearchToolset`, `ScreenshotService`) from `tools/__init__.py` to avoid import-time dep on `ddgs`/`playwright`.

Risk: `tools/__init__.py` importing 10 toolset classes may trigger circular imports if any toolset imports back from `tools`. Mitigate by testing imports in isolation first.

## 5. Follow-up Tasks

Split into 3 implementation tasks to keep diffs small and reviewable:

1. **Core packages** (auth, planning, projects, providers, safety) — minimal risk, 3–7 exports each
2. **tools package** — moderate risk due to circular import potential, 10 exports
3. **tools/browser subpackage** — moderate risk, 7 exports

Each task should: add `from .mod import X` lines, add `__all__`, run `ruff check` + `pytest`.
