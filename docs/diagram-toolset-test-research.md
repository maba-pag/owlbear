# DiagramToolset Test Strategy Research

> **Owning task:** #626 — Test DiagramToolset (generate_diagram agent tool)
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Task #626 asks: what tests should `tests/test_diagram_toolset.py` contain before building `DiagramToolset`? The toolset wraps `DiagramService` (Kroki API) as a `FunctionToolset` for agent use. This research documents the exact pattern, identifies test cases from prior art, and refines the AC.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | VisualFeedbackToolset | `src/owlbear/tools/visual_feedback.py` | .95 — closest pattern: service + channel + save |
| 2 | test_visual_feedback.py | `tests/test_visual_feedback.py` | .95 — test structure to follow exactly |
| 3 | DiagramService | `src/owlbear/tools/diagram/service.py` | .90 — the service being wrapped |
| 4 | ScreenshotService | `src/owlbear/tools/screenshot.py` | .85 — save/deliver methods reused |
| 5 | KnowledgeToolset | `src/owlbear/tools/knowledge.py` | .80 — alternative FunctionToolset pattern |
| 6 | BrowserToolset | `src/owlbear/tools/browser/toolset.py` | .75 — toolset registration pattern |
| 7 | Task #627 AC | `kanban/tasks/627-*.md` | .90 — defines the implementation contract |

## 3. Analysis

### 3.1 Toolset Pattern Comparison

All OwlBear toolsets follow a consistent `FunctionToolset` subclass pattern:

| Aspect | VisualFeedbackToolset | KnowledgeToolset | BrowserToolset |
|--------|----------------------|------------------|----------------|
| Base class | `FunctionToolset` | `FunctionToolset` | `FunctionToolset` |
| `tool_alias` ClassVar | `"visual_feedback"` | `"knowledge"` | `"browser"` |
| Registration | `_register_tools()` in `__init__` | `_register_tools()` in `__init__` | `_register_tools()` in `__init__` |
| Service injection | `ScreenshotService` via ctor | vector/graph/embed stores | `BrowserManager` internal |
| Channel injection | `ChannelPlugin` via ctor | N/A | N/A |
| Workspace | `Path` via ctor | `Path` via ctor | N/A |

**DiagramToolset should match VisualFeedbackToolset** — it wraps a service, saves output, and delivers via channel. The constructor signature per #627 AC:

```
__init__(diagram_service, screenshot_service, channel, workspace)
```

### 3.2 Test Pattern from test_visual_feedback.py

The test file uses this structure (221 LOC):

1. **Fixtures**: mock service, mock channel, mock page, `tmp_path` workspace, assembled toolset
2. **TestConstruction**: `isinstance(FunctionToolset)`, tool count, tool names
3. **TestShareScreenshot**: captures, saves, delivers, returns path, checks args
4. **TestShareTerminalOutput**: same pattern per tool

Each test verifies exactly one behavior via `assert_awaited_once` / `assert_called_once`.

### 3.3 DiagramToolset Test Cases

The `generate_diagram` tool contract (from #627 AC):

- `async generate_diagram(diagram_type: str, source_code: str, output_format: str = 'svg') -> str`
- Calls `DiagramService.generate(diagram_type, source_code, output_format)` → bytes
- Saves bytes via `ScreenshotService.save(bytes, "diagram", workspace)` → Path
- Delivers via `ScreenshotService.deliver(path, channel, caption)` — duck-typed
- Returns `str(path)`
- Catches `DiagramError` → user-friendly error string

| Test Case | Class | Verifies |
|-----------|-------|----------|
| is FunctionToolset subclass | TestConstruction | `isinstance` check |
| tool_alias is "diagram" | TestConstruction | `toolset.tool_alias == "diagram"` |
| registers exactly 1 tool | TestConstruction | `len(toolset.tools) == 1` |
| tool name is generate_diagram | TestConstruction | `"generate_diagram" in toolset.tools` |
| calls DiagramService.generate with correct args | TestGenerateDiagram | `svc.generate.assert_awaited_once_with(type, source, fmt)` |
| saves returned bytes via ScreenshotService.save | TestGenerateDiagram | `screenshot_svc.save` called with bytes, "diagram", workspace |
| delivers saved path to channel | TestGenerateDiagram | `screenshot_svc.deliver.assert_awaited_once` |
| returns path as string | TestGenerateDiagram | `result == str(expected_path)` |
| default output_format is svg | TestGenerateDiagram | call with 2 args, verify format passed as "svg" |
| DiagramError → user-friendly string | TestErrorHandling | mock `generate` raising `DiagramError`, assert str result |
| ValueError from service propagates | TestErrorHandling | invalid diagram_type → ValueError |

### 3.4 Fixture Design

```
diagram_svc   — AsyncMock with .generate returning b"<svg>ok</svg>"
screenshot_svc — MagicMock: .save returns Path, .deliver is AsyncMock
channel        — AsyncMock (duck-typed ChannelPlugin)
workspace      — tmp_path
toolset        — DiagramToolset(diagram_svc, screenshot_svc, channel, workspace)
```

## 4. Recommendation (.90 confidence)

Follow `test_visual_feedback.py` structure exactly. 11 test cases across 3 classes. Mock `DiagramService.generate` as `AsyncMock`, mock `ScreenshotService.save`/`deliver` per existing pattern. The `DiagramError` → friendly message test is the only novel case vs the visual feedback pattern.

**Risk:** The AC for #627 says `generate_diagram` has a `caption` parameter for delivery. Looking at `VisualFeedbackToolset.share_screenshot(caption)`, this is likely — but the #627 AC doesn't list it. **Recommendation:** Add `caption: str = ""` parameter to the implementation AC.

## 5. Follow-up Tasks

### Refined AC for #626 (replaces current AC)

```
AC:
- [ ] TestConstruction: toolset isinstance FunctionToolset
- [ ] TestConstruction: tool_alias == "diagram"
- [ ] TestConstruction: exactly 1 tool registered named "generate_diagram"
- [ ] TestGenerateDiagram: calls DiagramService.generate(type, source, format)
- [ ] TestGenerateDiagram: saves bytes via ScreenshotService.save(bytes, "diagram", workspace)
- [ ] TestGenerateDiagram: delivers path via ScreenshotService.deliver(path, channel, caption)
- [ ] TestGenerateDiagram: returns str(path)
- [ ] TestGenerateDiagram: default output_format is "svg"
- [ ] TestErrorHandling: DiagramError caught and returned as user-friendly string
- [ ] TestErrorHandling: ValueError from invalid type propagates
- [ ] All tests fail before DiagramToolset implementation exists
```

### Kanban commands (for user review — NOT executed)

```powershell
# Edit #626 with refined AC
kanban\kanban-md.exe edit 626 --body "Test-first task for DiagramToolset. File: tests/test_diagram_toolset.py\n\nAC:\n- [ ] TestConstruction: toolset isinstance FunctionToolset\n- [ ] TestConstruction: tool_alias == 'diagram'\n- [ ] TestConstruction: exactly 1 tool registered named 'generate_diagram'\n- [ ] TestGenerateDiagram: calls DiagramService.generate(type, source, format)\n- [ ] TestGenerateDiagram: saves bytes via ScreenshotService.save(bytes, 'diagram', workspace)\n- [ ] TestGenerateDiagram: delivers path via ScreenshotService.deliver(path, channel, caption)\n- [ ] TestGenerateDiagram: returns str(path)\n- [ ] TestGenerateDiagram: default output_format is 'svg'\n- [ ] TestErrorHandling: DiagramError caught and returned as user-friendly string\n- [ ] TestErrorHandling: ValueError from invalid type propagates\n- [ ] All tests fail before DiagramToolset implementation exists\n\nPattern: follow test_visual_feedback.py structure\nRef: docs/diagram-toolset-test-research.md"

# Move #626 to backlog
kanban\kanban-md.exe move 626 backlog

# Edit #627 to add caption parameter
kanban\kanban-md.exe edit 627 --body "Implement Tier 1 diagram agent tool. File: src/owlbear/tools/diagram/toolset.py\n\nAC:\n- [ ] DiagramToolset(FunctionToolset) in src/owlbear/tools/diagram/toolset.py\n- [ ] tool_alias: ClassVar[str] = 'diagram'\n- [ ] __init__(diagram_service, screenshot_service, channel, workspace) matching VisualFeedbackToolset pattern\n- [ ] _register_tools() registers generate_diagram via add_function()\n- [ ] async generate_diagram(diagram_type: str, source_code: str, output_format: str = 'svg', caption: str = '') -> str\n- [ ] Calls DiagramService.generate(), saves via ScreenshotService.save(), delivers via channel\n- [ ] Returns saved file path as string\n- [ ] DiagramError caught and re-raised as user-friendly message string\n- [ ] src/owlbear/tools/diagram/__init__.py also exports DiagramToolset\n- [ ] All tests from #626 pass, ruff clean\n\nPattern: follow VisualFeedbackToolset / BrowserToolset FunctionToolset pattern\nRef: docs/diagram-toolset-test-research.md"
```

## 6. Attribution

No new external sources — all analysis is from existing codebase patterns.
