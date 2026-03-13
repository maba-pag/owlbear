# DiagramToolset Implementation Research

> **Owning task:** #627 — Implement DiagramToolset exposing generate_diagram tool
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Task #627 asks: how should `DiagramToolset` be implemented as a `FunctionToolset` wrapping `DiagramService` (Kroki API) for agent use? The toolset must follow the existing VisualFeedbackToolset pattern — service injection, save, deliver, return path. This research validates the approach, checks prior art, and confirms technical feasibility.

## 2. Sources Studied

| # | Source | URL / Location | Relevance |
|---|--------|----------------|-----------|
| 1 | VisualFeedbackToolset | `src/owlbear/tools/visual_feedback.py` | .95 — identical pattern: service + channel + save + deliver |
| 2 | BrowserToolset | `src/owlbear/tools/browser/toolset.py` | .85 — FunctionToolset subclass with `tool_alias`, `_register_tools()` |
| 3 | antoinebou12/uml-mcp | <https://github.com/antoinebou12/uml-mcp> | .80 — Python MCP diagram tool: Kroki-first, `generate_uml(diagram_type, code, output_format)`, validation → generate → save |
| 4 | nicobailon/visual-explainer | <https://github.com/nicobailon/visual-explainer> | .70 — Agent skill for HTML diagram generation, routes by diagram type |
| 5 | DiagramService (existing) | `src/owlbear/tools/diagram/service.py` | .95 — the service being wrapped |
| 6 | ScreenshotService (existing) | `src/owlbear/tools/screenshot.py` | .90 — save/deliver reused directly |
| 7 | Test suite (#626) | `tests/test_diagram_toolset.py` | .95 — 14 tests already written and passing |

## 3. Analysis

### 3.1 Implementation Pattern Comparison

| Aspect | VisualFeedbackToolset (OwlBear) | uml-mcp `generate_uml` | OwlBear DiagramToolset (proposed) |
|--------|-------------------------------|----------------------|----------------------------------|
| Base class | `FunctionToolset` | `@mcp_tool` decorator | `FunctionToolset` |
| Service injection | `ScreenshotService` via ctor | Global config + utils | `DiagramService` + `ScreenshotService` via ctor |
| Channel delivery | `ScreenshotService.deliver()` duck-typed | File write + URL return | `ScreenshotService.deliver()` duck-typed |
| Error handling | Not applicable (capture can't fail) | Pydantic `ValidationError` → error dict | `DiagramError` → friendly string, `ValueError` → friendly string |
| Return type | `str` (file path) | `Dict[str, Any]` (url, path, error) | `str` (file path or error message) |
| Output formats | PNG only | svg, png, pdf, jpeg, base64 | svg, png (Kroki-supported) |

### 3.2 Error Handling Strategy

| Error | uml-mcp approach | OwlBear approach (proposed) |
|-------|-----------------|---------------------------|
| Invalid diagram type | Pydantic validation → error dict | `ValueError` from `DiagramService` → friendly string |
| Bad syntax | Kroki HTTP 400 → error dict | `DiagramError(status_code, body)` → friendly string |
| Service down | Kroki fallback → PlantUML/Mermaid.ink | Return error string (no fallback — KISS) |

uml-mcp's multi-backend fallback is over-engineered for OwlBear's use case. A single Kroki backend with clear error messages is KISS-aligned.

### 3.3 Existing Implementation Status

The implementation already exists at `src/owlbear/tools/diagram/toolset.py` (110 LOC) and **passes all 14 tests**. Key observations:

| AC Item | Status | Notes |
|---------|--------|-------|
| `DiagramToolset(FunctionToolset)` | Done | Correct subclass |
| `tool_alias = 'diagram'` | Done | ClassVar set |
| `__init__(diagram_service, screenshot_service, channel, workspace)` | Done | Matches VisualFeedbackToolset |
| `_register_tools()` via `add_function()` | Done | Single tool registered |
| `generate_diagram(diagram_type, source, output_format='svg')` | Done | Note: param name is `source` not `source_code` |
| Calls `DiagramService.generate()` → save → deliver | Done | Correct pipeline |
| Returns file path string | Done | `str(path)` |
| `DiagramError` caught → friendly message | Done | Also catches `ValueError` |
| `__init__.py` exports `DiagramToolset` | **Missing** | Only exports `DiagramError`, `DiagramService` |
| Tests pass, ruff clean | Done | 14/14 pass, ruff clean |

### 3.4 Gap: `__init__.py` Export

The `__init__.py` currently has:

```python
__all__ = ["DiagramError", "DiagramService"]
```

AC requires adding `DiagramToolset`. One-line fix.

### 3.5 Minor AC Deviation: Parameter Name

AC says `source_code`, implementation uses `source`. The tests (already passing) use `source`. Recommendation: keep `source` — it's consistent with `DiagramService.generate(source=...)` and avoids a test rewrite. Update the AC to match.

## 4. Recommendation (.90 confidence)

**The implementation is already complete and correct.** Only one gap remains:

1. Add `DiagramToolset` to `__init__.py` exports (1-line change)

The existing code follows the VisualFeedbackToolset pattern exactly, error handling is sound (catches both `DiagramError` and `ValueError`), and all 14 tests pass. No architectural changes needed.

**Risk:** Parameter name `source` vs AC's `source_code` — trivial. Keep `source` for consistency with `DiagramService`.

## 5. Follow-up Tasks

The implementation is 99% done. One micro-task to close the gap:

```powershell
kanban\kanban-md.exe edit 627 --body "Implementation complete. Remaining: add DiagramToolset to __init__.py exports. Param name uses 'source' (consistent with DiagramService) instead of AC's 'source_code' — acceptable deviation.\n\nAC:\n- [x] DiagramToolset(FunctionToolset) in src/owlbear/tools/diagram/toolset.py\n- [x] tool_alias: ClassVar[str] = 'diagram'\n- [x] __init__(diagram_service, screenshot_service, channel, workspace) matching VisualFeedbackToolset pattern\n- [x] _register_tools() registers generate_diagram via add_function()\n- [x] async generate_diagram(diagram_type: str, source: str, output_format: str = 'svg') -> str\n- [x] Calls DiagramService.generate(), saves via ScreenshotService.save(), delivers via channel\n- [x] Returns saved file path as string\n- [x] DiagramError caught and returned as user-friendly message\n- [ ] src/owlbear/tools/diagram/__init__.py also exports DiagramToolset\n- [x] All tests from #626 pass (14/14), ruff clean\n\nRef: docs/research/diagram-toolset-implementation.md"
```

## 6. Attribution Updates

No new external sources beyond those already logged for task #582 in `docs/sources.md`.
