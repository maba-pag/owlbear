---
id: 1a2dfb13-d645-4d76-98fb-6790bb8e2a17
title: Vitest vi.hoisted TDZ in Cockpit tests
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.9
state: curated
scope_agents:
- builder
- test-writer
- reviewer
source_agent: builder
created_at: '2026-05-12T16:04:32.061373Z'
updated_at: '2026-05-12T21:24:29.406743Z'
approved_at: null
---

In Cockpit Vitest files, a vi.hoisted mock factory that references a const declared later in the file can throw `ReferenceError: Cannot access <name> before initialization` once import errors are resolved. Avoid referencing non-hoisted defaults from hoisted factories — hoist those defaults too or inline literals directly in the factory.
