---
id: 1960
title: 'P1-23: Prove assembled Cockpit memory lifecycle'
status: build
priority: high
created: 2026-07-17T20:19:09.315342+02:00
updated: 2026-07-17T20:19:09.315342+02:00
tags:
  - phase-1
  - scope:cockpit
  - aggregate-proof
  - memory
parent: 1958
depends_on:
  - 1952
  - 1953
  - 1954
  - 1955
  - 1956
  - 1957
ac:
  - 'AC-1: At one recorded delivered commit SHA, running Cockpit with approved, contested,
    disputed, stale, and deleted entries demonstrates score-led ordering, seven-state
    filtering, documented detail/edit context, contested-task navigation, exceptional
    resolution, and no deleted edit action at representative desktop and mobile viewports;
    Builder and Verify Notes record interaction results and screenshot references
    without incoherent overlap.'
  - 'AC-2: At that SHA or a recorded descendant, invoking the real MCP curation operation
    rejects contested, disputed, and stale entries while the real Cockpit edit and
    resolve boundaries succeed for those states; Builder and Verify Notes record commands
    and observed responses.'
  - 'AC-3: The proof record identifies the tested SHA and ties maintained documentation
    plus verified child evidence to the requested exclusions: no score colors, pinning,
    confidence marker, raw unremarkable or non-use counters, or MCP resolve operation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Produce the missing SHA-linked aggregate evidence that the delivered Cockpit memory lifecycle works as one assembled human workflow and preserves the final MCP authority restriction.

## Scope
In scope: selecting and recording one delivered commit SHA; running Cockpit with representative approved, contested, disputed, stale, and deleted memory entries; desktop and mobile browser interactions and screenshots; real MCP exceptional-curation rejection; Cockpit exceptional edit and resolve success; and recording commands, observations, screenshot references, and resulting SHA in Builder and Verify Notes. Out of scope: planned product changes, new lifecycle behavior, compatibility work, and broad refactoring. If proof reveals a product defect, return the task with concrete evidence rather than expanding this proof task.

## Planning Authority
Aggregate task #1958 and OpenSpec change `expose-memory-lifecycle-in-cockpit`. All implementation children #1952 through #1957 are archived completed; this task restores the executable aggregate closure path requested by the latest Collect Notes.

## Proof Guidance
Use the running Cockpit at the recorded commit for the complete desktop and mobile workflow. Use the real MCP curation operation and real Cockpit adapter/HTTP boundary for the authority split; lower storage fixtures may supply representative lifecycle records but must not replace the MCP operation, Cockpit endpoint, or browser workflow being proved. Record the tested commit SHA, exact commands, viewport evidence, screenshot references, and observed results in task notes so collector can tie aggregate AC-1 and AC-2 to that SHA or a descendant. No durable test is expected unless proof exposes a meaningful uncovered regression.