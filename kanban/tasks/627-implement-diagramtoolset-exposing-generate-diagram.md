---
id: 627
title: Implement DiagramToolset exposing generate_diagram tool
status: archived
priority: needed
created: 2026-03-07T05:21:41.0532699+01:00
updated: 2026-03-07T18:08:26.2039948+01:00
started: 2026-03-07T13:56:06.3841727+01:00
completed: 2026-03-07T18:08:26.2039948+01:00
tags:
    - phase-research
    - scope:core
    - tooling
depends_on:
    - 626
class: standard
---

Implement Tier 1 diagram agent tool. File: src/owlbear/tools/diagram/toolset.py

AC:

- [ ] DiagramToolset(FunctionToolset) in src/owlbear/tools/diagram/toolset.py
- [ ] tool_alias: ClassVar[str] = 'diagram'
- [ ] __init__(diagram_service: DiagramService, screenshot_service: ScreenshotService, channel: ChannelPlugin, workspace: Path)  follows VisualFeedbackToolset pattern (see src/owlbear/tools/visual_feedback.py)
- [ ] Store deps as _svc (DiagramService), _screenshot (ScreenshotService), _channel, _workspace
- [ ] _register_tools() registers generate_diagram via add_function()
- [ ] async generate_diagram(diagram_type: str, source: str, output_format: str = 'svg') -> str  NOTE: param is 'source' not 'source_code' to match DiagramService.generate() signature
- [ ] Calls self._svc.generate(diagram_type=diagram_type, source=source, output_format=output_format)
- [ ] Saves returned bytes via self._screenshot.save(image_bytes, 'diagram', self._workspace)
- [ ] Delivers saved path via self._screenshot.deliver(path, self._channel, caption) where caption includes diagram_type
- [ ] Returns str(path) of the saved file
- [ ] DiagramError caught and returned as user-friendly string (NOT re-raised) e.g. f'Diagram generation failed (HTTP {e.status_code}): {e.body}'
- [ ] ValueError caught and returned as user-friendly string (NOT re-raised) e.g. f'Invalid input: {e}'
- [ ] On error, save() and deliver() are NOT called
- [ ] src/owlbear/tools/diagram/__init__.py exports DiagramToolset in __all__
- [ ] All tests from #626 pass (tests/test_diagram_toolset.py), ruff clean

Known issue: ScreenshotService.save() hardcodes .png extension. For SVG output the file content will be SVG but filename ends in .png. Accept this for now  it does not affect delivery or agent usage. A future task can refine save() to accept format hints.

Pattern: follow VisualFeedbackToolset (src/owlbear/tools/visual_feedback.py) and FileToolset (src/owlbear/tools/filesystem.py) patterns.
Ref: docs/research/visuals-diagrams-mcp.md section 4 Tier 1
