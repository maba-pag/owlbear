# Context

## Problem

The old single-agent ideation surface makes discovery and mediation bleed into each other, which increases drift and hides the phase boundary from the user.

## Outcomes

- make the discovery vs mediation split explicit
- preserve the multi-file blackboard rather than replacing it
- keep the user entry path understandable even when the workflow is split

## Tier

Studio

## Constraints

- preserve the existing blackboard files
- keep `ideator` as a compatibility router during migration
- do not force brownfield research before the project type is known

## Current Tensions

- the old entrypoint is familiar, but it obscures the phase boundary
- the split must be real, not just a renamed monolith