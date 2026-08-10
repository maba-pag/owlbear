# Context

## Problem

A new export surface is needed for approved ideation briefs so a user can capture the final decision set without reopening the whole working directory.

## Outcomes

- produce one minimal export entrypoint
- keep the first release narrow enough to ship without touching the main-consuming runtime
- preserve the current blackboard files as the source of truth

## Tier

Studio

## Constraints

- no consumer-repo changes in this phase
- reuse existing brief blackboard files
- avoid adding a second hidden workflow behind the same command

## Current Tensions

- a richer export wizard would overrun the real need
- the user wants a tangible output, but not a new mini-platform