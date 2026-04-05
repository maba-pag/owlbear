# AST-based Package Boundary Enforcement Test

> **Owning task:** #510 — Add AST-based package boundary enforcement test
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

OwlBear has 6 packages (7 namespaces) under `packages/` with no automated import boundary enforcement. Cross-package coupling could silently accumulate. How should we enforce allowed import directions?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| deer-flow test_harness_boundary.py (MIT) | github.com/bytedance/deer-flow | AST-based enforcement pattern, ~50 LOC, zero deps (.90) |
| import-linter v2.11 (BSD-2) | github.com/seddonym/import-linter | Mature tool with forbidden/independence/layers contracts (.75) |

## 3. Analysis

### Current OwlBear dependency graph (verified)

| Package namespace | Allowed imports from | Declared in pyproject.toml? |
|-------------------|---------------------|-----------------------------|
| `owlbear_knowledge` | (none) | Foundation — no owlbear deps |
| `owlbear_mcp_kanban` | (none) | Standalone MCP server |
| `owlbear_mcp_knowledge` | `owlbear_knowledge` | Yes — workspace dep |
| `owlbear_mcp_project` | (none) | Standalone MCP server |
| `owlbear` | `owlbear_orchestrator` | Same wheel (co-shipped) |
| `owlbear_orchestrator` | `owlbear` | Same wheel (co-shipped) |
| `owlbear_voice` | (none) | Standalone addon |

All 7 namespaces are clean today — no undeclared cross-package imports exist.

### Approach comparison

| Criterion | AST-based test (deer-flow) | import-linter |
|-----------|---------------------------|---------------|
| External deps | 0 (stdlib only) | 1 (import-linter) |
| LOC | ~50-80 | ~10 (config) + tool install |
| KISS | High — single test file | Medium — external tool + config |
| Flexibility | Sufficient for forbidden imports | Layers, independence, acyclic siblings |
| CI integration | pytest (already in pipeline) | Separate lint-imports command |
| Contract types | Forbidden only (all we need) | 5 built-in types (YAGNI) |
| Maintenance | Manual update when deps change | Same — config update needed |

## 4. Recommendation (.85 confidence)

**AST-based test (deer-flow pattern).** Zero deps, ~60 LOC, runs in existing pytest suite. import-linter's extra contract types (layers, independence) are YAGNI — OwlBear only needs "forbidden imports" enforcement.

**Implementation notes for downstream agents:**

- Define `ALLOWED_IMPORTS: dict[str, set[str]]` mapping each namespace to allowed owlbear-namespace imports
- Use `ast.parse` + `ast.walk` to collect all `Import` / `ImportFrom` nodes
- Scan `packages/*/src/` directories only (not tests — tests may import cross-package for integration)
- Identify owlbear namespaces by prefix match against the 7 known namespaces
- Test file: `tests/test_package_boundary.py`
- The `owlbear ↔ owlbear_orchestrator` pair lives in one wheel — treat as intra-package (allowed)

**Risk:** Minimal. False positives only possible if a new package is added without updating `ALLOWED_IMPORTS`. Mitigated by a manifest check (test fails if a `packages/*/src/` namespace isn't in the map).

## 5. Follow-up Tasks

Task #510 already exists with correct AC. No additional tasks needed — this research validates approach and provides the dependency rules for implementation.
