---
id: 318
title: Create fix-attempt.agent.md with assign-mode tools
status: ideation
priority: needed
created: 2026-03-30T20:38:16.8297495+02:00
updated: 2026-03-30T22:26:23.4836942+02:00
tags:
    - scope:agents
    - phase-2
blocked: true
block_reason: Decision 228-fresh-context-retry.md pending (approved:false). Feature invalidated if Option D chosen.
class: standard
---

AC:
1. agents/fix-attempt.agent.md with persona, tools (assign: 9 tools - builder tools minus kanban), workflow
2. Frontmatter: user-invocable: false, disable-model-invocation: true, agents: [], model: [Claude Sonnet 4.6 (copilot), GPT-5.3-Codex (copilot)]
3. Assigned tools (exactly 9): vscode/memory, execute/runInTerminal, execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal, read/readFile, edit/editFiles, edit/createFile, search
4. Output contract: FIXED/FAILED + files_changed + evidence (Channel A style)
5. Input contract: task_id, test_file, source_files, retry_hint, error_summary (documented in workflow section)
6. Max 1 internal retry (fix-attempt IS the fresh perspective)
7. Never touches kanban board (enforced by tool exclusion - no owlbear-kanban/*)
8. validate_agents.py passes on the new file
See docs/research/fresh-context-retry-builder.md, docs/research/fix-attempt-agent-design.md
Depends on: decision 228-fresh-context-retry.md approval

[[2026-03-30]] Mon 22:26
## Architecture Review
**Verdict:** Block (pending decision)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Agent file with persona/tools/workflow | Clear, follows pipeline agent pattern | Kept |
| 2. Frontmatter flags + model + agents:[] | Added model spec and agents:[] per research gaps | Refined |
| 3. Explicit 9-tool assign list | Enumerated all 9 tools for precision | Refined |
| 4. Output contract FIXED/FAILED | Aligns with Channel A convention | Kept |
| 5. Input contract with retry_hint | Reflexion-style verbal feedback, well-specified | Kept |
| 6. Max 1 internal retry | Bounded, clear | Kept |
| 7. No kanban tools | Enforced by tool exclusion | Kept |
| 8. validate_agents.py passes | Added: ensures pre-commit hook compatibility | Added |

### Architecture Notes
1. AC is architecturally sound. 9-tool assign set confirmed against builder.agent.md (19 tools minus 10 excluded). Exclusions justified in docs/research/fix-attempt-agent-design.md S3b.
2. Pattern consistency: follows existing pipeline agent convention (DIM true, agents:[], model list, assign tools). Reference: builder.agent.md, reviewer.agent.md.
3. TDD: not applicable for .agent.md files (declarative config). Validated by reviewer against AC plus validate_agents.py. Consistent with #307, #263 precedent.
4. Decision 228-fresh-context-retry.md (approved:false) blocks the feature. Option D (do nothing) would invalidate #318-#320. Consistent with #266 block for same reason.

### Changes Made
- Refined AC: added model spec, agents:[], explicit tool enumeration, validate_agents.py check
- Blocked to ideation pending decision 228 approval

### Dependencies
- Blocking: decision 228-fresh-context-retry.md (approved:false)
- Downstream: #319 (workflow integration), #320 (tests) both at ideation
