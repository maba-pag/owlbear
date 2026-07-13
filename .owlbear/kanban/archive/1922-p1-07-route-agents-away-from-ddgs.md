---
id: 1922
title: 'P1-07: Route agents away from DDGS'
status: archived
priority: low
created: 2026-07-13T03:41:48.587457+02:00
updated: 2026-07-13T06:04:57.820381+02:00
tags:
  - phase-1
  - scope:agent-config
  - agent
  - type:build
  - rigor:standard
parent: 1924
depends_on:
  - 1921
ac:
  - 'AC-1: Given the knowledge-ingestor receives a known public page, a rendered or
    authenticated page, or a supported document, its loaded grants and instructions
    route those inputs to built-in web access, browser acquisition, or MarkItDown
    respectively, and expose no DDGS search or extraction tool.'
  - 'AC-2: Given the shaper and research workflow load their active tool grants and
    guidance, they expose no DDGS server bootstrap, search, or extraction path; open-ended
    DDGS search is described as unavailable rather than silently replaced.'
  - 'AC-3: Given an agent needs arbitrary browser navigation, click, type, select,
    read, or snapshot behavior, active guidance keeps those interactive operations
    separate from acquisition and does not add action, credential, MFA, or caller-JavaScript
    fields to the acquisition workflow.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Planning source: `openspec/changes/complete-browser-content-acquisition/`

Objective: remove the selection pressure that currently sends agents to DDGS and replace it with one unambiguous known-content routing rule.

Contract authorities: OpenSpec Known-page acquisition routing, Complete DDGS retirement, Open-ended DDGS search is not preserved, and Existing browser interaction remains separate requirements; `share/README.md`; `share/skills/h-agent-structure/SKILL.md`; current knowledge-ingestor and shaper agent grants; `share/skills/w-research/SKILL.md`; `share/instructions/owlbear-system.instructions.md`.

In scope: distributed agent grants, acquisition/research guidance, system deferred-tool bootstrap guidance, and related wiring references required by those edits.

Out of scope: executable MCP configuration, browser implementation, a replacement search provider, MarkItDown behavior, and knowledge-source lifecycle.

Proof guidance: run the established agent/customization structural validators and perform a targeted distributed-artifact search for active DDGS grants or recommendations; no executable browser test is expected in this domain.

[[2026-07-13T06:01:00+02:00]]
## Builder Notes

Change envelope: remove active DDGS grants and recommendation paths from distributed agent configuration and acquisition/research guidance; preserve interactive browser operations as a separate concern.

Files changed:
- `share/agents/knowledge-ingestor.agent.md`
- `share/agents/shaper.agent.md`
- `share/skills/w-research/SKILL.md`
- `share/instructions/owlbear-system.instructions.md`

Change Module Map deviations: none. The mapped agent grants, research guidance, and system deferred-tool guidance were the owning surfaces identified by the task.

Proof selected: structural agent/skill validators plus targeted distributed-artifact search and editor diagnostics. No durable tests added; this is configuration/documentation routing with established structural validation and no executable browser behavior in scope.

Commands run:
- `uv run python .owlbear/scripts/validate_agents.py` -> `PASS — all 23 agent files conform to conventions`
- `uv run python .owlbear/scripts/validate_skills.py` -> completed successfully with no output
- `rg -n -i '(^|[[:space:],/])ddgs([*/[:space:],]|$)|extract_content|search_text' share/agents share/skills/w-research/SKILL.md share/instructions/owlbear-system.instructions.md` -> only the required explicit guidance that open-ended DDGS search is unavailable remained
- editor diagnostics via `get_errors` -> no errors in all four changed files

Acceptance evidence: knowledge-ingestor now routes known public pages to `web`, rendered/authenticated pages to browser acquisition, and supported documents to MarkItDown, with no DDGS grant. Shaper has no DDGS grant. Research guidance states open-ended DDGS search is unavailable and does not silently replace it. System bootstrap guidance no longer advertises DDGS. Interactive browser behavior remains separate from acquisition guidance.

Builder-challenger result: pass. The challenger confirmed AC-1, AC-2, and AC-3, scope compliance, and proof sufficiency after a clean validator rerun.

Follow-up risks: none identified; verifier should independently inspect the distributed artifact search if needed.

[[2026-07-13T06:04:30+02:00]]
## Verify Notes

Evidence reviewed:
- Contract authority checked: `openspec/changes/complete-browser-content-acquisition/specs/web-content-tool-routing/spec.md`.
- Change Module Map matched the four changed distributed-guidance owners: `share/agents/knowledge-ingestor.agent.md`, `share/agents/shaper.agent.md`, `share/skills/w-research/SKILL.md`, and `share/instructions/owlbear-system.instructions.md`. No scope deviation found.
- Browser tool authority checked in `serve/mcp-browser/src/owlbear_mcp_browser/server.py`: `ob-browser/acquire` is the read-only acquisition tool; interactive methods such as `navigate` remain separate.

Normal-path boundary exercised:
- Reviewed active grants and routing guidance: known public pages use `web`; rendered/authenticated pages use `ob-browser/acquire`; supported documents use `markitdown/*`.
- Confirmed the acquisition grant exposes only the read-only `acquire` operation, preserving separate interactive browser operations and adding no action, credential, MFA, or caller-JavaScript inputs.
- Targeted active-artifact DDGS scan returned only the required explicit statement that open-ended DDGS search is unavailable; it found no DDGS search/extraction grants or system bootstrap entry in the task's routing surfaces.

Finding and patch applied:
- The knowledge-ingestor guidance named browser acquisition but originally lacked its executable grant. Applied the local correction: added `ob-browser/acquire` to `share/agents/knowledge-ingestor.agent.md`; no interactive browser grants were added.

Checks run:
- `uv run python .owlbear/scripts/validate_agents.py` -> `PASS — all 23 agent files conform to conventions`.
- `uv run python .owlbear/scripts/validate_skills.py` -> exit 0.
- Scoped `rg` DDGS scan -> only intentional unavailability language in `share/skills/w-research/SKILL.md`.
- Scoped `git diff --check` -> clean.
- Editor diagnostics -> no errors in all four changed files.
- Setup MCP merge smoke (supporting evidence) -> preserved custom configuration, contained `ob-browser`, and omitted `ddgs`.

Commit:
- `89eb9059f8139e5d1ada18d5c829a4153d69856d` (`chore: route agents away from DDGS (#1922, verifier)`).

Memory:
- Recalled verifier memories; workspace-location and live-artifact verification guidance were useful. Assessment submission could not complete because this session's MCP tool requires opaque entry IDs not supplied by recall output.

Verifier-challenger result:
- Initial response used a stale workspace snapshot and was superseded by a direct current-state recheck.
- Final recheck: `decision: pass`; it confirmed all ACs, correct routing, separate interactive capability, and sufficient validation.

Final route: PASS to `collect`.

[[2026-07-13T06:04:57+02:00]]
## Collect Notes

- Classification: leaf. Task has no child tasks and carries scoped implementation intent rather than parent or EPIC aggregate intent.
- Leaf verification evidence: `## Verify Notes` records PASS after independent contract review, active-grant and routing inspection, structural validators, targeted DDGS scan, diff check, diagnostics, setup merge smoke, and verifier-challenger final `decision: pass`.
- Invariant map coverage: AC-1 known-content routing, AC-2 complete active DDGS retirement with explicit unavailability, and AC-3 separation of interactive browser operations are all explicitly covered by verifier evidence.
- Dependency gate: `depends_on` task #1921 is satisfied; pre-claim projection reported `dep_status: ok`.
- Tested commit and tied proof: commit `89eb9059f8139e5d1ada18d5c829a4153d69856d` is recorded alongside the validator, targeted scan, diff-check, diagnostics, and setup merge-smoke evidence in Verify Notes.
- Residual decisions and follow-up: no pending request records, no unresolved Required Follow-up, and no blocker.
- Archive rationale: verified leaf closure is complete; archive as completed without implementation re-review.
