# Brief

## Problem

The existing ideation surface collapses discovery and mediation into one visible voice, which obscures the handoff and encourages drift.

## Proposal

- split the user-facing workflow into `ideation-discoverer` and `ideation-mediator`
- keep `ideator` as a thin compatibility router
- preserve the multi-file blackboard and explicit handoff artifacts

## Risks

- users may still enter through the old name and need routing help
- live runtime behavior still needs validation on the main-consuming surface

## Validation Notes

- this fixture demonstrates a fresh-context Phase 2 start from `context.md`, `decisions.md`, and `research-notes.md`
- qualitative review judged the handoff readable without replaying the whole session