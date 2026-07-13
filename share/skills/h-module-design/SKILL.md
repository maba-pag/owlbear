---
name: h-module-design
description: "Handbook: Evaluate module depth, locality, interfaces, seams, and dependency placement"
user-invocable: false
---

# Module Design

Use this vocabulary when evaluating or designing code. A module is scale-agnostic: a function,
class, package, service, or tier-spanning slice can all be modules.

## Module Quality Vocabulary

| Concept | Definition | Diagnostic |
|---------|------------|------------|
| **Module** | Something with an interface and an implementation | Name the responsibility it hides, not its file type or framework role. |
| **Interface** | Everything a caller must know to use a module correctly, including invariants, ordering, errors, configuration, and performance | If callers must understand internals, the effective interface is larger than its type signature. |
| **Implementation** | Behavior hidden inside a module | Internal composition does not need to become caller knowledge or an external seam. |
| **Depth** | Leverage delivered through the interface | Deep modules expose substantial behavior through a small interface; shallow modules make callers coordinate the behavior. |
| **Leverage** | Capability callers receive per unit of interface they must learn | One implementation pays back across multiple callers and tests. |
| **Locality** | Degree to which change, bugs, knowledge, and verification concentrate in one place | Good locality means a behavior change is understood and fixed once. |
| **Seam** | Location where behavior can vary without editing the caller | A seam is justified by real variation, usually at least two adapters. |
| **Adapter** | A concrete participant that satisfies an interface at a seam | It names the substitutable role, not a generic forwarding wrapper. |

## Deletion Test

Imagine deleting a module entirely. If deleting it removes only forwarding while callers become
simpler, it was shallow. If its hidden complexity reappears across callers, it was earning its keep.

Apply the test when evaluating abstractions, adapters, wrappers, and proposed package boundaries. A
module that fails is a candidate for removal or deepening by absorbing more responsibility behind a
simpler interface.

## Interface Is the Test Surface

Callers and durable behavioral tests should cross the same interface. Tests may replace a dependency
below that interface, but should not bypass the behavior being claimed. If tests routinely need to
reach past the interface, reconsider the module shape before adding more test-only seams.

## Seam Discipline

- One adapter usually indicates a hypothetical seam; two adapters establish actual variation.
- A deep module may contain private internal seams without exposing them to callers.
- Prefer replacing a dependency below the tested interface over layering tests across every shallow
  internal module.
- Do not introduce a seam merely to make a test easier when callers have no corresponding variation.

## Dependency Classification

| Type | Example | Seam needed? |
|------|---------|--------------|
| In-process | Direct function call | Rarely |
| Local-substitutable | File-system or process adapter | Maybe |
| Remote-but-owned | A separately deployed service owned by the same project | Yes |
| True-external | Third-party API or independently controlled service | Yes |

Classification describes operational ownership and substitution cost, not protocol alone. A local
HTTP process may be local-substitutable; a separately deployed internal service may be
remote-but-owned.

## Applying the Diagnostics

1. Name the responsibility and caller-facing interface.
2. Identify what complexity the implementation hides from callers.
3. Apply the Deletion Test and note where complexity would reappear.
4. Check whether behavior, knowledge, and verification have good locality.
5. Classify dependencies and justify each exposed seam with real variation or ownership boundaries.
6. Prefer the smallest boundary that concentrates responsibility without making callers coordinate
   implementation details.

Use `h-codebase-orientation` first when the owning modules and callers have not yet been located.
