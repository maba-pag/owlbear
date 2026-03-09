---
id: 493
title: Document shell injection risk and add mitigations
status: done
priority: important
created: 2026-03-04T07:38:08.5010961+01:00
updated: 2026-03-08T02:02:44.5045203+01:00
started: 2026-03-06T23:23:21.9589698+01:00
completed: 2026-03-08T02:02:44.5045203+01:00
tags:
    - audit
    - security
    - tools
class: standard
---

SEC-01: TerminalToolset passes LLM commands to create_subprocess_shell. CommandSafetyGuard regex is bypassable (double spaces, base64, alt tools). Inherent design tension. Document the limitation and evaluate further mitigations.
See docs/security-audit.md SEC-01 for full analysis.

## Acceptance Criteria

- [ ] SECURITY.md created at project root with a 'Shell Execution' section documenting:
  - create_subprocess_shell is used by design (LLM needs shell access)
  - CommandSafetyGuard regex blocklist is defense-in-depth, not a security boundary
  - Approval gate on run_command is the primary control (done in #461)
  - Known bypass vectors: double-spacing, base64 encoding, alt tools, chaining
- [ ] SECURITY.md 'Mitigations' section lists the current layered defense:
  1. Approval gate (run_command gated by default)
  2. CommandSafetyGuard regex blocklist (defense-in-depth)
  3. Workspace confinement (sandbox_path on working_dir)
- [ ] SECURITY.md 'Future Considerations' section evaluates allowlist mode (pros/cons/decision)
- [ ] copilot-instructions.md 'Safety' table row updated to reference SECURITY.md
- [ ] ruff clean on any changed .py files (if any)
