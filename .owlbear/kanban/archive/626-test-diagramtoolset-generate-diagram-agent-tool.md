---
id: 626
title: Test DiagramToolset (generate_diagram agent tool)
status: archived
priority: needed
created: 2026-03-07T05:21:20.005502+01:00
updated: 2026-03-07T18:08:25.6807066+01:00
started: 2026-03-07T06:23:27.8942157+01:00
completed: 2026-03-07T18:08:25.6807066+01:00
tags:
    - phase-research
    - scope:core
    - tooling
    - test
depends_on:
    - 620
class: standard
---

Test-first task for DiagramToolset. File: tests/test_diagram_toolset.py

Interface under test (from #627):
  DiagramToolset(FunctionToolset) in src/owlbear/tools/diagram/toolset.py
  __init__(diagram_service: DiagramService, screenshot_service: ScreenshotService, channel: ChannelPlugin, workspace: Path)
  tool_alias: ClassVar[str] = 'diagram'
  async generate_diagram(diagram_type: str, source_code: str, output_format: str = 'svg') -> str

AC:

**TestConstruction (wiring and registration):**
- [ ] DiagramToolset is a FunctionToolset subclass
- [ ] Registers 'generate_diagram' tool via add_function() (assert 'generate_diagram' in toolset.tools)
- [ ] tool_alias class var equals 'diagram'

**TestGenerateDiagram (happy path -- mocked services):**
- [ ] Calls DiagramService.generate(diagram_type, source_code, output_format) with correct args
- [ ] Saves returned bytes via ScreenshotService.save(bytes, 'diagram', workspace)
- [ ] Delivers saved path via ScreenshotService.deliver(path, channel, caption) -- NOT channel.send_file() directly
- [ ] Returns str(path) of the saved file
- [ ] Default output_format is 'svg' when omitted

**TestErrorHandling (service errors -- mocked DiagramService.generate raising):**
- [ ] DiagramError caught and returned as user-friendly string (not re-raised)
- [ ] ValueError (bad diagram_type) caught and returned as user-friendly string

**TDD gate:**
- [ ] All tests fail with ImportError before DiagramToolset implementation exists
- [ ] File: tests/test_diagram_toolset.py

Total: ~10 test cases across 3 test classes.

Fixtures (mock wiring -- follow test_visual_feedback.py):
- diagram_svc: MagicMock with AsyncMock generate() returning b'<svg>ok</svg>'
- screenshot_svc: MagicMock with save() returning Path, deliver = AsyncMock
- channel: AsyncMock (duck-typed ChannelPlugin)
- workspace: tmp_path
- toolset: DiagramToolset(diagram_svc, screenshot_svc, channel, workspace)

Pattern: follow tests/test_visual_feedback.py structure exactly.
Ref: docs/research/visuals-diagrams-mcp.md section 4 Tier 1
