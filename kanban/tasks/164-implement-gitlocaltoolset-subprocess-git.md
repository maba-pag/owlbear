---
id: 164
title: 'Implement GitLocalToolset — subprocess git operationsts talk about the knowldge database. i see a problem with basic embedding. i work with very detail oriented texts (e.g. ISO norms, internal policies, laws, etc (ca. 35%)) but also general information (like powerpoint slides and intranet articles, ca 15%) but also the inbetween: technical documentation ()this might actually be the biggest part, lets say 50%. picking the right embedding model is hard. please add one or three or maybe even more research tasks for possible solutions. i am thinking of:ciprocal rank fusion, e.g. with pplx-embed-context-v1-0.6B and bge-m3, putting data into two tables: vec_semantic and vec_lexical, then using rrf (reciprocal rank fusion) to augment the results.trieve and rerank. pplx-embed-context-v1-0.6B to embed, and bge-reranker-v2-m3 to rerank search results.'
status: archived
priority: important
created: 2026-02-27T20:46:46.2518403+01:00
updated: 2026-02-28T23:53:17.7115988+01:00
started: 2026-02-27T21:26:52.5675643+01:00
completed: 2026-02-28T23:53:17.7115988+01:00
tags:
    - phase-8
    - tools
    - github
depends_on:
    - 163
class: standard
---

FunctionToolset wrapping 7 local git operations via asyncio.create_subprocess_exec.

## AC
- [ ] File: src/owlbear/tools/git_local.py
- [ ] GitLocalToolset(FunctionToolset) following FileToolset/TerminalToolset pattern
- [ ] Constructor: workspace_root: Path, hooks: HookRegistry | None = None
- [ ] 7 tools registered via add_function() (all async, use asyncio.create_subprocess_exec):
      - git_status: git status --porcelain, returns parsed output
      - git_diff: git diff [--staged] [path], returns diff text
      - git_add: git add <paths>, returns confirmation
      - git_commit: emits PRE_TOOL_USE hook, then git commit -m <message>
      - git_branch: git branch <name> or git checkout -b <name>
      - git_log: git log --oneline -n <count>, returns log
      - git_push: emits PRE_TOOL_USE hook, then git push [--set-upstream origin <branch>]
- [ ] git_commit and git_push emit HookEvent.PRE_TOOL_USE before execution (same pattern as TerminalToolset)
- [ ] Use --porcelain / --format flags for machine-readable output
- [ ] Non-zero exit codes return error string (do not raise)
- [ ] All tests from #163 pass
- [ ] ruff clean

## Architecture
- Follow TerminalToolset pattern: workspace_root as cwd, optional hooks
- Use asyncio.create_subprocess_exec (NOT subprocess.run, NOT GitPython)
- GitPython explicitly warns against daemon use (resource leaks via __del__)
- Separate from GitHubToolset — different auth, different failure modes
- Approval gates via PRE_TOOL_USE hook (CommandGuard or custom hook intercepts)
